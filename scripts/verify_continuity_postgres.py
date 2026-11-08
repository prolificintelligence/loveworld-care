"""Real Neon/private-object recovery proof, using only a disposable synthetic source.

Does not seed health_platform or send email. Uploads and cleanup are restricted to
this run's verified private verification/archive prefixes. No credentials or rows
are printed. The actual key-recovery test intentionally supplies the wrong app key.
"""

import asyncio
import hashlib
import json
import re
import secrets
import sys
import traceback
from decimal import Decimal
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidTag
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as clinical
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control.continuity import (
    ArchiveError,
    PrivateObjects,
    create_archive,
    object_name,
    rehearse_restore,
    unseal,
)
from lw_care_api.platform.institutional import tables as institutional
from lw_care_api.platform.main import create_platform_app
from test_platform_controls import ORIGIN, seed_controls, stamp


class TrackedObjects(PrivateObjects):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.written = set()
        self.archive_prefixes = set()

    def put(self, name, content):
        self.written.add(name)
        match = re.match(r"continuity/v1/[0-9a-f-]{36}/", name)
        if match:
            self.archive_prefixes.add(match.group())
        return super().put(name, content)


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_backup_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_backup_verify_[0-9a-f]{32}", namespace)
    objects, backup_id = TrackedObjects(cfg), None
    source_key = f"continuity/verification/{namespace}/source.pdf"
    mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    test_cfg = cfg.model_copy(
        update={
            "environment": "test",
            "enforce_activation_dossiers": False,
            "dispatch_recovery_after_commit": False,
            "web_origin": ORIGIN,
            "resend_api_key": "synthetic-not-a-sending-key",
        }
    )
    app = create_platform_app(test_cfg)
    await app.state.database.engine.dispose()
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
    try:
        assert await database.version() in {4, 5, 6}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=6, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:

            async def created(path, body):
                response = await client.post(
                    f"/v1/clinical/{facility}" + path,
                    json=body,
                    headers={
                        "Authorization": "Bearer " + actors["target"][1],
                        "Origin": ORIGIN,
                        "Idempotency-Key": db.uid(),
                    },
                )
                assert response.status_code == 200, (path, response.status_code)
                return response.json()["resource"]

            patient = await created(
                "/patients",
                {
                    "display_name": "Synthetic restore proof only",
                    "provisional": True,
                    "sex": "UNKNOWN",
                },
            )
            encounter = await created(
                "/encounters",
                {
                    "patient_id": patient["id"],
                    "service": "GENERAL",
                    "encounter_type": "AMBULATORY",
                    "arrival": "WALK_IN",
                    "complaint": "SYNTHETIC_ONLY",
                    "occurred_at": stamp(-1),
                },
            )
            context = {
                "patient_id": patient["id"],
                "encounter_id": encounter["id"],
                "occurred_at": stamp(-1),
            }
            note = await created(
                "/notes",
                {
                    **context,
                    "note_type": "CONSULTATION",
                    "narrative": "SYNTHETIC_SIGNED_RECOVERY_PROOF",
                    "source": "Synthetic engineering source",
                },
            )
            await created(
                f"/notes/{note['id']}/sign",
                {
                    "patient_id": patient["id"],
                    "expected_version": 1,
                    "reason": "Synthetic signature proof",
                    "intent_confirmed": True,
                },
            )
            await created(
                "/tasks",
                {
                    **context,
                    "title": "SYNTHETIC_OPEN_OBLIGATION",
                    "instructions": "Synthetic restore fixture",
                    "owner_id": actors["target"][0],
                    "due_at": stamp(1),
                },
            )
            observed = await client.post(
                "/v1/operations/reconciliation",
                json={
                    "evidence": "Synthetic cloud recovery fixture observation",
                    "intent_confirmed": True,
                },
                headers={
                    "Authorization": "Bearer " + actors["admin"][1],
                    "Origin": ORIGIN,
                    "Idempotency-Key": db.uid(),
                },
            )
            assert observed.status_code == 200, observed.status_code
        file_content = b"%PDF-1.7\nSYNTHETIC_ENGINEERING_RECOVERY_FIXTURE_ONLY\n%%EOF\n"
        await asyncio.to_thread(objects.put, source_key, file_content)
        async with app.state.database.transaction() as session:
            criteria, application, lot = db.uid(), db.uid(), db.uid()
            await session.execute(
                db.criteria.insert().values(
                    id=criteria,
                    name="Synthetic recovery fixture",
                    version="test-only",
                    jurisdiction="SYNTHETIC-ONLY",
                    site_type="COMMUNITY_PRIMARY",
                    requirements=[],
                    adoption_reference="SYNTHETIC_NOT_AN_ADOPTION",
                    adopted_by=actors["admin"][0],
                    valid_from=stamp(-1),
                    valid_until=stamp(1),
                )
            )
            await session.execute(
                db.applications.insert().values(
                    id=application,
                    facility_id=facility,
                    criteria_id=criteria,
                    state="DRAFT",
                    created_by=actors["admin"][0],
                    version=1,
                )
            )
            await session.execute(
                db.evidence.insert().values(
                    id=db.uid(),
                    application_id=application,
                    criterion="SYNTHETIC",
                    object_key=source_key,
                    sha256=hashlib.sha256(file_content).hexdigest(),
                    filename="synthetic-only.pdf",
                    media_type="application/pdf",
                    size=len(file_content),
                    source="Synthetic byte recovery fixture; scanner not qualified",
                    expires_at=stamp(1),
                    scan_status="TEST_NOT_SCANNED",
                    uploaded_by=actors["admin"][0],
                    created_at=db.now(),
                )
            )
            case_id = db.uid()
            await session.execute(
                institutional.cases.insert().values(
                    id=case_id,
                    facility_id=facility,
                    kind="RENEWAL",
                    state="OPEN",
                    version=1,
                    criteria_id=criteria,
                    criteria_snapshot={"id": criteria, "synthetic_only": True},
                    created_by=actors["admin"][0],
                    respondent_id=actors["admin"][0],
                    due_at=stamp(1),
                    created_at=db.now(),
                    details_ciphertext=app.state.box.encrypt('{"synthetic_recovery_only":true}'),
                )
            )
            await session.execute(
                institutional.case_files.insert().values(
                    id=db.uid(),
                    case_id=case_id,
                    criterion="SYNTHETIC",
                    object_key=source_key,
                    sha256=hashlib.sha256(file_content).hexdigest(),
                    filename="synthetic-only.pdf",
                    media_type="application/pdf",
                    size=len(file_content),
                    source="Synthetic case-file byte recovery; scanner not qualified",
                    expires_at=stamp(1),
                    scan_status="TEST_NOT_SCANNED",
                    uploaded_by=actors["admin"][0],
                    created_at=db.now(),
                )
            )
            await session.execute(
                clinical.lots.insert().values(
                    id=lot,
                    facility_id=facility,
                    product_id=encounter["id"],
                    batch="SYNTHETIC_RESTORE_ONLY",
                    expires_at=stamp(1),
                    quantity=Decimal("5.250000"),
                    unit="SYNTHETIC",
                    status="AVAILABLE",
                    version=1,
                )
            )
            await session.execute(
                clinical.movements.insert().values(
                    id=db.uid(),
                    lot_id=lot,
                    source_id=lot,
                    quantity=Decimal("5.250000"),
                    reason="Synthetic restore fixture",
                    actor_id=actors["target"][0],
                    recorded_at=db.now(),
                )
            )
            for leg, amount in ((1, 120), (2, -120)):
                await session.execute(
                    clinical.ledger.insert().values(
                        id=db.uid(),
                        facility_id=facility,
                        source_id=encounter["id"],
                        leg=leg,
                        account="SYNTHETIC_ONLY",
                        amount_minor=amount,
                        currency="NGN",
                        recorded_at=db.now(),
                    )
                )
            await session.execute(
                db.audit.insert().values(
                    id=db.uid(),
                    actor_id=actors["admin"][0],
                    action="SYNTHETIC_RECOVERY_PROOF",
                    outcome="SUCCESS",
                    purpose="ENGINEERING_TEST_ONLY",
                    recorded_at=db.now(),
                )
            )
        key = secrets.token_bytes(32)
        archived = await create_archive(
            app.state.database,
            test_cfg,
            key,
            objects=objects,
            source_schema=namespace,
            record_result=False,
        )
        backup_id = archived["id"]
        manifest_raw = await asyncio.to_thread(objects.get, object_name(backup_id, "manifest.enc"))
        manifest = json.loads(unseal(key, manifest_raw, backup_id, "manifest.enc"))
        try:
            await rehearse_restore(
                database,
                cfg,
                secrets.token_bytes(32),
                backup_id,
                objects=objects,
                record_result=False,
            )
        except InvalidTag:
            pass
        else:
            raise AssertionError("Wrong recovery key accepted")
        # Proves recovery from escrow, rather than reading the original app key.
        no_original_key = cfg.model_copy(update={"data_key_hex": secrets.token_hex(32)})
        restored = await rehearse_restore(
            database, no_original_key, key, backup_id, objects=objects, record_result=False
        )
        assert restored["files"] == 2 and restored["clinical_signatures_verified"] >= 5
        assert {entry["file_table"] for entry in manifest["files"]} == {
            "evidence",
            "institutional_case_files",
        }
        assert restored["integrity"]["population"]["open_indexed_tasks"] == 1
        assert restored["integrity"]["population"]["stock_lots"] == 1
        assert restored["integrity"]["population"]["ledger_entries"] == 2
        assert not any(restored["integrity"]["checks"].values())
        assert restored["temporary_schema_and_files_removed"]
        chunk = next(
            table for table in manifest["tables"] if table["name"] == clinical.events.name
        )["chunks"][0]
        name = object_name(backup_id, chunk["object"])
        original = await asyncio.to_thread(objects.get, name)
        await asyncio.to_thread(objects.put, name, original[:-1] + bytes([original[-1] ^ 1]))
        try:
            await rehearse_restore(
                database, cfg, key, backup_id, objects=objects, record_result=False
            )
        except ArchiveError:
            pass
        else:
            raise AssertionError("Corrupted private object accepted")
        print(
            json.dumps(
                {
                    "continuity_postgres_private_objects": "PASSED",
                    "recovery_without_original_application_key": "VERIFIED",
                    "wrong_recovery_key": "REJECTED",
                    "tampered_cloud_chunk": "REJECTED",
                    "files": restored["files"],
                    "file_tables_verified": sorted(
                        {entry["file_table"] for entry in manifest["files"]}
                    ),
                    "tables": restored["tables"],
                    "decrypted_fields_verified": restored["decrypted_fields_verified"],
                    "clinical_signatures_verified": restored["clinical_signatures_verified"],
                    "open_care_stock_and_ledger": "RECONCILED",
                    "protected_history_tables": restored["protected_history_tables"],
                    "production_domain_records_seeded": 0,
                }
            )
        )
    finally:
        for name in objects.written:
            allowed = (
                name == source_key
                or any(name.startswith(prefix) for prefix in objects.archive_prefixes)
                or bool(
                    re.fullmatch(
                        r"continuity/rehearsals/lwh_restore_[0-9a-f]{32}/(?:evidence|institutional_case_files)/[0-9a-f-]{36}",
                        name,
                    )
                )
            )
            assert allowed, "Refusing foreign private object cleanup"
            await asyncio.to_thread(objects.delete, name)
        assert re.fullmatch(r"lwh_backup_verify_[0-9a-f]{32}", namespace)
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- redact data, credentials and provider response bodies
        last = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "continuity_verification": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(last.filename).name,
                    "line": last.lineno,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                    "statement": (getattr(exc, "statement", "") or "")[:400],
                    "archive_diagnostic": str(exc) if isinstance(exc, ArchiveError) else None,
                    "frames": [
                        {"source": Path(frame.filename).name, "line": frame.lineno}
                        for frame in traceback.extract_tb(exc.__traceback__)
                        if "site-packages" not in frame.filename
                    ],
                }
            )
        )
        raise SystemExit(1) from None
