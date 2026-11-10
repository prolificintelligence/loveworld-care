"""Recovery and integrity boundaries; disk-backed archive tests use no provider-success stub."""

import json
import secrets
from decimal import Decimal

import pytest
from cryptography.exceptions import InvalidTag
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as clinical
from lw_care_api.platform.control import tables as t
from lw_care_api.platform.control.continuity import (
    ArchiveError,
    canonical,
    create_archive,
    get_encrypted,
    object_name,
    rehearse_restore,
    restored_values,
    seal,
    shape,
    unseal,
)
from sqlalchemy import func, select, update
from test_platform_controls import controls as stored_controls
from test_platform_controls import run, stamp


@pytest.fixture
def controls(tmp_path):
    yield from stored_controls.__wrapped__(tmp_path)


class DiskObjects:
    """Actual disposable filesystem transport, only used by these engineering tests."""

    def __init__(self, root):
        self.root = root

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, name):
        return (self.root / name).read_bytes()

    def delete(self, name):
        (self.root / name).unlink()


def test_reliability_has_no_invented_recovery_readiness(controls):
    response = controls.get("/operations/reliability")
    assert response.status_code == 200
    status = response.json()
    assert status["latest"] == {"backup": None, "restore": None, "reconciliation": None}
    assert status["recovery_targets"] == "NOT_ADOPTED"
    assert status["independent_off_account_copy"] == "NOT_QUALIFIED"
    assert status["scanner_configured"] is False
    assert status["evidence_upload"]["state"] == "EXCLUDED_SCANNER_UNAVAILABLE"
    assert status["evidence_upload"]["scan_bypass_permitted"] is False


def test_schema9_reporting_projection_corruption_is_visible_to_reconciliation(controls):
    from lw_care_api.platform.reporting.source_index import index

    j = controls
    _patient, encounter, _task = j.task()

    async def remove():
        async with j.app.state.database.transaction() as session:
            await session.execute(index.delete().where(index.c.record_id == encounter["id"]))

    run(remove())
    result = j.create("/operations/reconciliation", {
        "evidence": "Synthetic missing source projection fault", "intent_confirmed": True,
    })
    assert result["checks"]["reporting_source_projection_mismatches"] == 1
    assert result["integrity_outcome"] == "EXCEPTIONS"
    assert encounter["id"] not in json.dumps(result)


@pytest.mark.parametrize("name", ["target", "privacy", "proposer"])
def test_no_clinical_or_oversight_seniority_bypass_for_recovery_evidence(controls, name):
    assert controls.get("/operations/reliability", name).status_code == 403
    assert controls.get("/operations/assurance-runs", name).status_code == 403
    assert (
        controls.post(
            "/operations/reconciliation",
            {"evidence": "Synthetic observation", "intent_confirmed": True},
            name,
        ).status_code
        == 403
    )


def test_reconciliation_retains_one_effect_and_does_not_complete_care(controls):
    j = controls
    patient, _encounter, task = j.task()
    key, body = (
        db.uid(),
        {"evidence": "SYNTHETIC_PRIVATE_OPERATOR_REFERENCE", "intent_confirmed": True},
    )
    first = j.post("/operations/reconciliation", body, key=key)
    second = j.post("/operations/reconciliation", body, key=key)
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    result = first.json()["resource"]
    assert result["clinical_fulfilment_inferred"] is False
    assert result["population"]["open_indexed_tasks"] == 1
    assert not any(
        identifier in first.text for identifier in (patient["id"], task["id"], "SYNTHETIC_PRIVATE")
    )

    async def inspect():
        async with j.app.state.database.transaction() as session:
            assert await session.scalar(select(func.count()).select_from(t.assurance_runs)) == 1
            assert (
                await session.scalar(
                    select(clinical.records.c.status).where(clinical.records.c.id == task["id"])
                )
                != "COMPLETED"
            )

    run(inspect())
    history = j.get("/operations/assurance-runs")
    assert "evidence_ciphertext" not in history.text and "SYNTHETIC_PRIVATE" not in history.text
    assert history.json()["items"][0]["kind"] == "RECONCILIATION"


def test_integrity_detects_unbalanced_ledger_stock_and_missing_indexes(controls):
    j = controls
    _patient, encounter, task = j.task()

    async def inject():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                clinical.ledger.insert().values(
                    id=db.uid(),
                    facility_id=j.facility,
                    source_id=encounter["id"],
                    leg=1,
                    account="SYNTHETIC",
                    amount_minor=120,
                    currency="NGN",
                    recorded_at=db.now(),
                )
            )
            await session.execute(
                clinical.lots.insert().values(
                    id=db.uid(),
                    facility_id=j.facility,
                    product_id=encounter["id"],
                    batch="SYNTHETIC",
                    expires_at=stamp(2),
                    quantity=Decimal("5.25"),
                    unit="SYNTHETIC",
                    status="AVAILABLE",
                    version=1,
                )
            )
            await session.execute(
                t.obligations.delete().where(t.obligations.c.source_id == task["id"])
            )

    run(inject())
    result = j.create(
        "/operations/reconciliation",
        {"evidence": "Synthetic controlled integrity fault injection", "intent_confirmed": True},
    )
    assert result["integrity_outcome"] == "EXCEPTIONS"
    assert result["checks"]["unbalanced_ledger_groups"] == 1
    assert result["checks"]["stock_movement_mismatches"] == 1
    assert result["checks"]["missing_task_indexes"] == 1
    assert "NGN" not in json.dumps(result) and encounter["id"] not in json.dumps(result)


def test_reconciliation_replay_checks_revoked_authority(controls):
    j = controls
    key, body = db.uid(), {"evidence": "Synthetic scoped observation", "intent_confirmed": True}
    assert j.post("/operations/reconciliation", body, key=key).status_code == 200

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["admin"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.post("/operations/reconciliation", body, key=key).status_code == 403


def test_recovery_schema_four_staging_gate_preserves_existing_controls(controls):
    async def downgrade():
        async with controls.app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.delete().where(db.schema_versions.c.version > 4)
            )

    run(downgrade())
    assert controls.client.get("/v1/ready").json()["schema_version"] == 4
    assert controls.get("/operations/context").status_code == 200
    assert controls.get("/operations/reliability").status_code == 503


def test_archive_encryption_binds_key_identity_path_and_rejects_tampering():
    key, identifier, content = secrets.token_bytes(32), db.uid(), b"SYNTHETIC_PRIVATE_RECOVERY_DATA"
    encrypted = seal(key, content, identifier, "manifest.enc")
    assert (
        content not in encrypted and unseal(key, encrypted, identifier, "manifest.enc") == content
    )
    for other_key, other_id, path, data in [
        (secrets.token_bytes(32), identifier, "manifest.enc", encrypted),
        (key, db.uid(), "manifest.enc", encrypted),
        (key, identifier, "wrong.enc", encrypted),
        (key, identifier, "manifest.enc", encrypted[:-1] + bytes([encrypted[-1] ^ 1])),
    ]:
        with pytest.raises(InvalidTag):
            unseal(other_key, data, other_id, path)
    with pytest.raises(ArchiveError):
        object_name(identifier, "../manifest.enc")


def test_streamed_archive_preserves_keys_without_plaintext_provider_objects(controls, tmp_path):
    j = controls
    _patient, _encounter, _task = j.task()
    key, objects = secrets.token_bytes(32), DiskObjects(tmp_path)
    result = run(create_archive(j.app.state.database, j.app.state.settings, key, objects=objects))
    assert result["restore_verified"] is False
    assert result["tables"] == len(shape()) and result["rows"] > 20
    manifest_bytes = objects.get(object_name(result["id"], "manifest.enc"))
    assert j.app.state.settings.data_key_hex.encode() not in manifest_bytes
    manifest = json.loads(unseal(key, manifest_bytes, result["id"], "manifest.enc"))
    assert manifest["data_key_hex"] == j.app.state.settings.data_key_hex
    assert manifest["schema_version"] == 9
    assert "reporting_source_index" in manifest["shape"]
    assert "reporting_source_index" not in shape(8)
    records = next(entry for entry in manifest["tables"] if entry["name"] == clinical.records.name)
    chunk = records["chunks"][0]
    assert b"SYNTHETIC_PRIVATE" not in objects.get(object_name(result["id"], chunk["object"]))
    payload = run(get_encrypted(objects, key, result["id"], chunk))
    assert len(json.loads(payload)) == 3
    assert (
        j.get("/operations/reliability").json()["latest"]["backup"]["outcome"]
        == "ARCHIVED_NOT_RESTORE_VERIFIED"
    )
    assert j.get("/operations/reliability").json()["latest"]["restore"] is None
    objects.put(object_name(result["id"], chunk["object"]), b"corrupted persisted object")
    with pytest.raises(ArchiveError):
        run(get_encrypted(objects, key, result["id"], chunk))


def test_archive_requires_independent_key_and_restore_requires_isolated_postgres(
    controls, tmp_path
):
    j = controls
    with pytest.raises(ArchiveError):
        run(
            create_archive(
                j.app.state.database,
                j.app.state.settings,
                bytes.fromhex(j.app.state.settings.data_key_hex),
                objects=DiskObjects(tmp_path),
            )
        )
    with pytest.raises(ArchiveError):
        run(
            rehearse_restore(
                j.app.state.database,
                j.app.state.settings,
                secrets.token_bytes(32),
                db.uid(),
                objects=DiskObjects(tmp_path),
            )
        )


def test_numeric_archive_round_trip_preserves_stock_scale():
    values = {column.name: None for column in clinical.lots.c}
    values["quantity"] = Decimal("100.001200")
    recovered = restored_values(clinical.lots, json.loads(canonical(values)))
    assert recovered["quantity"] == Decimal("100.001200")
    assert canonical(recovered) == canonical(values)
