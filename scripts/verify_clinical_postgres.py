"""Actual Neon concurrency proofs in a disposable, isolated EMR namespace.

No synthetic records enter health_platform. Credentials and failed response bodies
are never printed. Only the random namespace created here is removed on completion.
"""

import asyncio
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))

from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as t
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_emr_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_emr_verify_[0-9a-f]{32}", namespace)
    engine = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app = create_platform_app(cfg.model_copy(update={"environment": "test", "enforce_activation_dossiers": False}))
    await app.state.database.engine.dispose()
    app.state.database.engine = engine
    app.state.database.session = async_sessionmaker(engine, expire_on_commit=False)
    facility, region, zone, operator, actor = [db.uid() for _ in range(5)]
    evidence = {}
    try:
        async with database.transaction() as session:
            assert await session.scalar(select(func.max(db.schema_versions.c.version))) in {2, 3, 4}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            for table in t.IMMUTABLE:
                await connection.execute(
                    text(
                        f'CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON "{namespace}".{table.name} FOR EACH ROW EXECUTE FUNCTION health_platform.reject_history_mutation()'
                    )
                )
            await connection.execute(
                text(
                    f'CREATE TRIGGER protect_clinical_records BEFORE UPDATE OR DELETE ON "{namespace}".clinical_records FOR EACH ROW EXECUTE FUNCTION health_platform.protect_clinical_records()'
                )
            )
        async with app.state.database.transaction() as session:
            await session.execute(
                db.accounts.insert().values(
                    id=actor,
                    email="emr-proof@synthetic.invalid",
                    name="Isolated EMR proof",
                    active=True,
                    totp_last_step=-1,
                    created_at=db.now(),
                )
            )
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=actor,
                    role="CLINICAL_STAFF",
                    scope_type="FACILITY",
                    scope_id=facility,
                    valid_from=stamp(-1),
                    valid_until=stamp(2),
                    revoked=False,
                    grantor="ISOLATED_TEST",
                )
            )
            await session.execute(
                db.units.insert().values(
                    id=region, name="Isolated proof region", kind="REGION", code=region, version=1
                )
            )
            await session.execute(
                db.units.insert().values(
                    id=zone,
                    name="Isolated proof zone",
                    kind="ZONE",
                    parent_id=region,
                    code=zone,
                    version=1,
                )
            )
            await session.execute(
                db.operators.insert().values(
                    id=operator, name="Isolated proof operator", external_reference=operator
                )
            )
            await session.execute(
                db.facilities.insert().values(
                    id=facility,
                    operator_id=operator,
                    zone_id=zone,
                    name="Isolated EMR proof",
                    site_type="INPATIENT_HOSPITAL",
                    ownership="MEMBER_OWNED",
                    jurisdiction="TEST",
                    external_reference=facility,
                    address="Synthetic",
                    public_contact="test@synthetic.invalid",
                    private_contact="test@synthetic.invalid",
                    services=["GENERAL"],
                    identity_status="VERIFIED",
                    statutory_status="CHECKED",
                    created_by=actor,
                    created_at=db.now(),
                    updated_at=db.now(),
                    version=1,
                )
            )
            await session.execute(
                t.sites.insert().values(
                    id=db.uid(),
                    facility_id=facility,
                    authority_node_id=cfg.authority_node_id,
                    authority_epoch="1",
                    services=["GENERAL", "PHARMACY"],
                    policy_reference="Isolated test authority",
                    manual_medicine_policy="Isolated test manual review",
                    valid_from=stamp(-1),
                    valid_until=stamp(2),
                    active=True,
                    version=1,
                    approved_by="ISOLATED_TEST",
                )
            )
            await session.execute(
                t.privileges.insert().values(
                    id=db.uid(),
                    facility_id=facility,
                    account_id=actor,
                    services=["GENERAL", "PHARMACY"],
                    capabilities=[
                        "REGISTER",
                        "CARE",
                        "NURSING",
                        "PRESCRIBE",
                        "PHARMACY",
                        "DIAGNOSTICS",
                        "PROCEDURE",
                        "RECORDS",
                    ],
                    professional_reference="Isolated test only",
                    valid_from=stamp(-1),
                    valid_until=stamp(1),
                    revoked=False,
                    approved_by="ISOLATED_TEST",
                )
            )
            token = await issue_session(session, actor, 30)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=cfg.web_origin, timeout=60
        ) as client:

            async def post(path, body, key=None):
                return await client.post(
                    f"/v1/clinical/{facility}{path}",
                    json=body,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Idempotency-Key": key or db.uid(),
                    },
                )

            async def created(path, body, key=None):
                response = await post(path, body, key)
                if response.status_code != 200:
                    code = response.json().get("error", {}).get("code", "UNKNOWN")
                    raise RuntimeError(
                        f"Isolated command failed: {path}: {response.status_code}: {code}"
                    )
                return response.json()["resource"]

            contexts = []
            for number in range(2):
                patient = await created(
                    "/patients",
                    {
                        "display_name": f"Isolated proof patient {number}",
                        "provisional": True,
                        "sex": "UNKNOWN",
                    },
                )
                encounter = await created(
                    "/encounters",
                    {
                        "patient_id": patient["id"],
                        "service": "GENERAL",
                        "encounter_type": "INPATIENT",
                        "arrival": "EMERGENCY",
                        "complaint": "Synthetic only",
                        "occurred_at": stamp(-1),
                    },
                )
                context = {
                    "patient_id": patient["id"],
                    "encounter_id": encounter["id"],
                    "occurred_at": stamp(-1),
                }
                note_body = {
                    **context,
                    "note_type": "CONSULTATION",
                    "narrative": "Synthetic source evidence",
                    "source": "Isolated proof author",
                }
                key = db.uid()
                responses = await asyncio.gather(
                    post("/notes", note_body, key), post("/notes", note_body, key)
                )
                assert all(response.status_code == 200 for response in responses)
                assert responses[0].json() == responses[1].json()
                note = responses[0].json()["resource"]
                signed = await created(
                    f"/notes/{note['id']}/sign",
                    {
                        "patient_id": patient["id"],
                        "expected_version": 1,
                        "reason": "Actual synthetic intent",
                        "intent_confirmed": True,
                    },
                )
                contexts.append((context, signed))
            evidence["simultaneous_idempotent_note_requests"] = "ONE_EFFECT_AND_IDENTICAL_RECEIPTS"
            bed = await created("/beds", {"ward": "Isolated ward", "label": "Race bed"})
            requests = [
                {
                    **context,
                    "bed_id": bed["id"],
                    "expected_bed_version": 1,
                    "responsible_clinician_id": actor,
                    "responsible_nurse_id": actor,
                    "indication": "Synthetic admission",
                    "signed_admission_note_id": note["id"],
                }
                for context, note in contexts
            ]
            admissions = await asyncio.gather(*(post("/admissions", body) for body in requests))
            assert sorted(response.status_code for response in admissions) == [200, 409]
            evidence["concurrent_exclusive_bed_claims"] = "ONE_OCCUPANCY_ONE_CONFLICT"
            context = contexts[0][0]
            product = await created(
                "/products",
                {
                    "code": {
                        "system": "urn:lwh:test-only",
                        "code": "TEST",
                        "display": "NON-CLINICAL TEST PRODUCT",
                        "version": "test-1",
                    },
                    "ingredient": "Synthetic",
                    "form": "TEST",
                    "strength": "TEST",
                    "strength_unit": "TEST",
                    "permitted_routes": ["TEST"],
                    "formulary_reference": "Synthetic test-only approval",
                    "valid_until": stamp(1),
                },
            )
            medication = await created(
                "/medications",
                {
                    **context,
                    "product_id": product["id"],
                    "indication": "Synthetic only",
                    "dose": "1",
                    "dose_unit": "TEST",
                    "route": "TEST",
                    "timing": "TEST",
                    "starts_at": stamp(-2),
                    "stops_at": stamp(1),
                    "substitution": "NOT_PERMITTED",
                    "manual_safety_review": "Synthetic actual manual check",
                    "reconciliation": "Synthetic",
                },
            )
            for action, version in [("SIGN", 1), ("VERIFY", 2)]:
                await created(
                    f"/medications/{medication['id']}/actions",
                    {
                        "patient_id": context["patient_id"],
                        "expected_version": version,
                        "action": action,
                        "reason": "Synthetic actual action",
                        "safety_review": "Synthetic actual review",
                        "intent_confirmed": True,
                    },
                )
            lot = await created(
                "/stock",
                {
                    "product_id": product["id"],
                    "batch": "TEST",
                    "expires_at": stamp(1),
                    "quantity": "3",
                    "unit": "TEST",
                    "evidence": "Synthetic actual receipt",
                },
            )
            dispense = {
                **context,
                "medication_id": medication["id"],
                "expected_order_version": 3,
                "lot_id": lot["id"],
                "expected_lot_version": 1,
                "quantity": "2",
                "verification": "Synthetic actual supply",
                "patient_identity_check": "Synthetic identity evidence",
            }
            supplied = await asyncio.gather(
                post("/dispenses", dispense), post("/dispenses", dispense)
            )
            assert sorted(response.status_code for response in supplied) == [200, 412]
            async with app.state.database.transaction() as session:
                assert (
                    await session.scalar(select(t.lots.c.quantity).where(t.lots.c.id == lot["id"]))
                    == 1
                )
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(t.movements)
                        .where(t.movements.c.lot_id == lot["id"])
                    )
                    == 2
                )
            evidence["concurrent_stock_issues"] = "ONE_ISSUE_BALANCE_ONE_NO_NEGATIVE_STOCK"
            for table, criterion, values in [
                (t.events, t.events.c.record_id == contexts[0][1]["id"], {"action": "TAMPER"}),
                (t.records, t.records.c.id == contexts[0][1]["id"], {"status": "DRAFT"}),
            ]:
                rejected = False
                try:
                    async with app.state.database.transaction() as session:
                        await session.execute(update(table).where(criterion).values(**values))
                except DBAPIError:
                    rejected = True
                assert rejected
            evidence["database_history_and_signed_note_protection"] = "DIRECT_MUTATION_REJECTED"
        print(
            json.dumps(
                {
                    "postgres_emr_verification": "PASSED",
                    "production_test_records": 0,
                    "checks": evidence,
                }
            )
        )
    finally:
        # The verified literal is the sole deletion target; never remove health_platform.
        assert re.fullmatch(r"lwh_emr_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 - redact credentials at the executable boundary
        print(
            json.dumps(
                {"postgres_emr_verification": "FAILED", "exception_type": type(exc).__name__}
            )
        )
        raise SystemExit(1) from None
