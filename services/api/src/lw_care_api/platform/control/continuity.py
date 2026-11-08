"""Authenticated, streamed logical archives and destructive-action-free restore rehearsals.

Only a trusted operator tool receives the independent recovery key. The web API
cannot create/download archives or read that key. No shell or pg_dump is invoked.
"""

import asyncio
import base64
import hashlib
import json
import re
import secrets
from decimal import Decimal
from time import monotonic
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Numeric, and_, inspect, select, text

from .. import db, storage
from ..security import SecretBox
from . import assurance

FORMAT = "LWH-CONTINUITY-001"
MAX_OBJECT = 16 * 1024 * 1024
MAX_MANIFEST = 16 * 1024 * 1024
CHUNK_ROWS = 200


class ArchiveError(Exception):
    """A safe category; callers never log provider exceptions or plaintext."""


def canonical(value):
    def encode(item):
        if isinstance(item, Decimal) and item.is_finite():
            return format(item, "f")
        raise ArchiveError("Unsupported source value")

    return json.dumps(
        value,
        default=encode,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def fingerprint(key):
    if not isinstance(key, bytes) or len(key) != 32:
        raise ArchiveError("A separate 32-byte recovery key is required")
    return hashlib.sha256(key).hexdigest()[:16]


def seal(key, content, backup_id, relative):
    fingerprint(key)
    nonce = secrets.token_bytes(12)
    aad = f"{FORMAT}:{backup_id}:{relative}".encode()
    return nonce + AESGCM(key).encrypt(nonce, content, aad)


def unseal(key, content, backup_id, relative):
    fingerprint(key)
    if len(content) < 28 or len(content) > MAX_OBJECT + 1024:
        raise ArchiveError("Invalid encrypted object size")
    return AESGCM(key).decrypt(
        content[:12], content[12:], f"{FORMAT}:{backup_id}:{relative}".encode()
    )


def prefix(backup_id):
    if str(UUID(str(backup_id))) != str(backup_id):
        raise ArchiveError("Invalid backup identity")
    return f"continuity/v1/{backup_id}/"


def object_name(backup_id, relative):
    if (
        not re.fullmatch(r"[a-z0-9_/-]+\.enc", relative)
        or ".." in relative
        or relative.startswith("/")
    ):
        raise ArchiveError("Invalid archive object identity")
    return prefix(backup_id) + relative


def shape():
    from ..reporting import tables as reporting_tables  # noqa: F401 -- register metadata

    return {
        table.name: {
            "columns": list(table.c.keys()),
            "types": [str(c.type) for c in table.c],
            "primary_key": [c.name for c in table.primary_key],
        }
        for table in db.metadata.sorted_tables
    }


class PrivateObjects:
    def __init__(self, cfg):
        self.client, self.bucket = storage.client(cfg), cfg.s3_bucket

    def put(self, name, content):
        self.client.put_object(
            Bucket=self.bucket, Key=name, Body=content, ContentType="application/octet-stream"
        )

    def get(self, name):
        result = self.client.get_object(Bucket=self.bucket, Key=name)
        try:
            if result.get("ContentLength", 0) > MAX_OBJECT + 1024:
                raise ArchiveError("Object exceeds recovery limit")
            value = result["Body"].read(MAX_OBJECT + 1025)
            if len(value) > MAX_OBJECT + 1024:
                raise ArchiveError("Object exceeds recovery limit")
            return value
        finally:
            result["Body"].close()

    def delete(self, name):
        self.client.delete_object(Bucket=self.bucket, Key=name)


async def put_encrypted(objects, key, backup_id, relative, content):
    if len(content) > MAX_OBJECT:
        raise ArchiveError("Archive chunk exceeds recovery limit")
    encrypted = seal(key, content, backup_id, relative)
    name = object_name(backup_id, relative)
    await asyncio.to_thread(objects.put, name, encrypted)
    received = await asyncio.to_thread(objects.get, name)
    if received != encrypted:
        raise ArchiveError("Stored ciphertext did not verify")
    return {
        "object": relative,
        "sha256": hashlib.sha256(encrypted).hexdigest(),
        "bytes": len(encrypted),
    }


async def get_encrypted(objects, key, backup_id, entry):
    raw = await asyncio.to_thread(objects.get, object_name(backup_id, entry["object"]))
    if hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]:
        raise ArchiveError("Encrypted archive integrity mismatch")
    return unseal(key, raw, backup_id, entry["object"])


async def create_archive(
    database, cfg, recovery_key, *, objects=None, source_schema=db.SCHEMA, record_result=True
):
    """One repeatable, read-only DB snapshot; manifest commits only after all bytes verify."""
    from ..clinical import tables as clinical_tables  # noqa: F401
    from ..reporting import tables as reporting_tables  # noqa: F401
    from . import tables  # noqa: F401 -- ensure current metadata

    fingerprint(recovery_key)
    if recovery_key == bytes.fromhex(cfg.data_key_hex):
        raise ArchiveError("Recovery and application keys must be independent")
    if source_schema != db.SCHEMA and not re.fullmatch(
        r"lwh_backup_verify_[0-9a-f]{32}", source_schema
    ):
        raise ArchiveError("Unsupported source namespace")
    objects = objects or PrivateObjects(cfg)
    identifier, started, timer = db.uid(), db.now(), monotonic()
    manifest = {
        "format": FORMAT,
        "id": identifier,
        "snapshot_at": started,
        "key_fingerprint": fingerprint(recovery_key),
        "data_key_hex": cfg.data_key_hex,
        "authority_node_id": cfg.authority_node_id,
        "shape": shape(),
        "tables": [],
        "files": [],
    }
    try:
        async with database.engine.connect() as raw_connection:
            connection = await raw_connection.execution_options(
                schema_translate_map={db.SCHEMA: source_schema}
                if database.postgres
                else {db.SCHEMA: None},
                **({"isolation_level": "REPEATABLE READ"} if database.postgres else {}),
            )
            async with connection.begin():
                if database.postgres:
                    await connection.execute(text("SET TRANSACTION READ ONLY"))
                    actual = await connection.run_sync(
                        lambda sync: inspect(sync).get_table_names(schema=source_schema)
                    )
                    if set(actual) != set(manifest["shape"]):
                        raise ArchiveError("Database and archive schema differ")
                version = await connection.scalar(
                    select(db.schema_versions.c.version)
                    .order_by(db.schema_versions.c.version.desc())
                    .limit(1)
                )
                if version != 5:
                    raise ArchiveError("Archive requires migrated schema 5")
                manifest["schema_version"] = version
                for table in db.metadata.sorted_tables:
                    entry = {"name": table.name, "rows": 0, "chunks": []}
                    digest = hashlib.sha256()
                    pending, pending_size = [], 2

                    async def flush_rows(pending=pending, table=table, entry=entry):
                        if pending:
                            chunk = await put_encrypted(
                                objects,
                                recovery_key,
                                identifier,
                                f"tables/{table.name}/{len(entry['chunks']):08d}.enc",
                                b"[" + b",".join(pending) + b"]",
                            )
                            entry["chunks"].append(chunk)
                            pending.clear()

                    result = await connection.stream(
                        select(table)
                        .order_by(*table.primary_key.columns)
                        .execution_options(yield_per=10)
                    )
                    async for partition in result.mappings().partitions(10):
                        values = [dict(row) for row in partition]
                        for row in values:
                            encoded = canonical(row)
                            if (
                                pending_size + len(encoded) > 4 * 1024 * 1024
                                or len(pending) >= CHUNK_ROWS
                            ):
                                await flush_rows()
                                pending_size = 2
                            pending.append(encoded)
                            pending_size += len(encoded) + 1
                            digest.update(encoded + b"\n")
                        entry["rows"] += len(values)
                        if table is db.evidence:
                            for row in values:
                                content = await asyncio.to_thread(objects.get, row["object_key"])
                                if (
                                    len(content) != row["size"]
                                    or hashlib.sha256(content).hexdigest() != row["sha256"]
                                ):
                                    raise ArchiveError("Source evidence bytes did not reconcile")
                                file = await put_encrypted(
                                    objects,
                                    recovery_key,
                                    identifier,
                                    f"files/{row['id']}.enc",
                                    content,
                                )
                                manifest["files"].append(
                                    {
                                        **file,
                                        "evidence_id": row["id"],
                                        "source_sha256": row["sha256"],
                                        "source_size": row["size"],
                                    }
                                )
                    await flush_rows()
                    entry["sha256"] = digest.hexdigest()
                    manifest["tables"].append(entry)
        manifest["completed_at"] = db.now()
        await put_encrypted(objects, recovery_key, identifier, "manifest.enc", canonical(manifest))
        summary = {
            "tables": len(manifest["tables"]),
            "rows": sum(t["rows"] for t in manifest["tables"]),
            "files": len(manifest["files"]),
            "snapshot_at": started,
            "elapsed_seconds": round(monotonic() - timer, 3),
            "key_fingerprint": fingerprint(recovery_key),
            "restore_verified": False,
        }
        if record_result:
            await assurance.record(
                database,
                SecretBox(cfg.data_key_hex),
                kind="BACKUP",
                outcome="ARCHIVED_NOT_RESTORE_VERIFIED",
                actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
                started_at=started,
                summary=summary,
                evidence={"manifest": object_name(identifier, "manifest.enc")},
                identifier=identifier,
            )
        return {"id": identifier, **summary}
    except Exception:
        if record_result:
            await assurance.record(
                database,
                SecretBox(cfg.data_key_hex),
                kind="BACKUP",
                outcome="FAILED",
                actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
                started_at=started,
                summary={"archive_committed": False},
                evidence={"category": "BACKUP_DID_NOT_COMPLETE"},
                identifier=identifier,
            )
        raise


async def verify_lineage(connection, manifest, recovered_box, cfg):
    from ..clinical import store as clinical_store
    from ..clinical import tables as clinical
    from ..reporting import tables as reporting

    public_key = clinical_store.signing_key(
        cfg.model_copy(update={"data_key_hex": manifest["data_key_hex"]})
    ).public_key()
    signatures, histories = 0, 0
    record_id, version, previous_hash = None, 0, "0" * 64
    result = await connection.stream(
        select(clinical.events).order_by(clinical.events.c.record_id, clinical.events.c.version)
    )
    async for row in result.mappings():
        if record_id != row["record_id"]:
            record_id, version, previous_hash = row["record_id"], 0, "0" * 64
        payload = json.loads(recovered_box.decrypt(row["payload_ciphertext"]))
        if (
            row["version"] != version + 1
            or row["previous_hash"] != previous_hash
            or hashlib.sha256(canonical(payload)).hexdigest() != row["payload_hash"]
        ):
            raise ArchiveError("Clinical event chain did not verify")
        for column, value in row.items():
            if (
                column not in {"payload_hash", "payload_ciphertext", "signature"}
                and payload.get(column) != value
            ):
                raise ArchiveError("Clinical event envelope identity differs")
        public_key.verify(
            base64.b64decode(row["signature"], validate=True), bytes.fromhex(row["payload_hash"])
        )
        version, previous_hash = row["version"], row["payload_hash"]
        signatures += 1
    result = await connection.stream(
        select(
            clinical.records, clinical.events.c.payload_ciphertext.label("last_event")
        ).select_from(
            clinical.records.outerjoin(
                clinical.events,
                and_(
                    clinical.records.c.id == clinical.events.c.record_id,
                    clinical.records.c.version == clinical.events.c.version,
                ),
            )
        )
    )
    async for row in result.mappings():
        current = clinical_store.opened(recovered_box, row)
        if not row["last_event"]:
            raise ArchiveError("Clinical current version has no source event")
        last = json.loads(recovered_box.decrypt(row["last_event"]))
        if last["content"] != current["data"] or any(
            last[key] != row[key]
            for key in (
                "status",
                "kind",
                "facility_id",
                "patient_id",
                "authority_node_id",
                "authority_epoch",
            )
        ):
            raise ArchiveError("Clinical current state differs from its signed event")
    result = await connection.stream(select(reporting.history))
    async for row in result.mappings():
        payload = json.loads(recovered_box.decrypt(row["payload_ciphertext"]))
        if hashlib.sha256(canonical(payload)).hexdigest() != row["payload_hash"]:
            raise ArchiveError("Reporting payload hash did not verify")
        histories += 1
    return signatures, histories


def restored_values(table, row):
    if set(row) != set(table.c.keys()):
        raise ArchiveError("Archive columns differ")
    return {
        name: Decimal(value)
        if isinstance(table.c[name].type, Numeric) and value is not None
        else value
        for name, value in row.items()
    }


async def rehearse_restore(
    database, cfg, recovery_key, backup_id, *, objects=None, record_result=True
):
    """Always creates/drops its own random schema; never binds a running service to it."""
    if not database.postgres:
        raise ArchiveError("An isolated PostgreSQL target is required")
    objects = objects or PrivateObjects(cfg)
    started, timer = db.now(), monotonic()
    namespace = "lwh_restore_" + db.uid().replace("-", "")
    created = False
    copied_files = []
    try:
        raw = await asyncio.to_thread(objects.get, object_name(backup_id, "manifest.enc"))
        manifest = json.loads(unseal(recovery_key, raw, backup_id, "manifest.enc"))
        if (
            manifest["format"] != FORMAT
            or manifest["id"] != backup_id
            or manifest["shape"] != shape()
            or manifest["schema_version"] != 5
        ):
            raise ArchiveError("Incompatible archive")
        if len(manifest["tables"]) != len(shape()) or {
            t["name"] for t in manifest["tables"]
        } != set(shape()):
            raise ArchiveError("Incomplete archive tables")
        # Recovery uses the wrapped key, not the configured application key.
        recovered_box = SecretBox(manifest["data_key_hex"])
        async with database.engine.begin() as connection:
            if not re.fullmatch(r"lwh_restore_[0-9a-f]{32}", namespace) or namespace == db.SCHEMA:
                raise ArchiveError("Invalid restore target")
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            created = True
            target = await connection.execution_options(schema_translate_map={db.SCHEMA: namespace})
            await target.run_sync(db.metadata.create_all)
            constraints = (
                await target.execute(
                    text("""select c.relname, k.conname
                from pg_constraint k join pg_class c on c.oid=k.conrelid
                join pg_namespace n on n.oid=c.relnamespace
                where n.nspname=:schema and k.contype='f'"""),
                    {"schema": namespace},
                )
            ).all()
            quote = target.dialect.identifier_preparer.quote
            for table_name, constraint in constraints:
                await target.execute(
                    text(
                        f"ALTER TABLE {quote(namespace)}.{quote(table_name)} ALTER CONSTRAINT {quote(constraint)} DEFERRABLE INITIALLY DEFERRED"
                    )
                )
        checked_ciphertexts = 0
        expected_files = {}
        by_name = {entry["name"]: entry for entry in manifest["tables"]}
        async with database.engine.begin() as connection:
            target = await connection.execution_options(schema_translate_map={db.SCHEMA: namespace})
            for table in db.metadata.sorted_tables:
                entry, digest, rows = by_name[table.name], hashlib.sha256(), 0
                for chunk in entry["chunks"]:
                    values = json.loads(
                        await get_encrypted(objects, recovery_key, backup_id, chunk)
                    )
                    if not isinstance(values, list) or not 1 <= len(values) <= CHUNK_ROWS:
                        raise ArchiveError("Invalid row chunk")
                    for row in values:
                        if table is db.evidence:
                            expected_files[row["id"]] = (row["sha256"], row["size"])
                        for column, value in row.items():
                            if column.endswith("ciphertext") and value is not None:
                                recovered_box.decrypt(value)
                                checked_ciphertexts += 1
                        digest.update(canonical(row) + b"\n")
                    await target.execute(
                        table.insert(), [restored_values(table, row) for row in values]
                    )
                    rows += len(values)
                if rows != entry["rows"] or digest.hexdigest() != entry["sha256"]:
                    raise ArchiveError("Source row reconciliation failed")
            for table in db.metadata.sorted_tables:
                digest, count = hashlib.sha256(), 0
                result = await target.stream(select(table).order_by(*table.primary_key.columns))
                async for row in result.mappings():
                    digest.update(canonical(dict(row)) + b"\n")
                    count += 1
                if (
                    digest.hexdigest() != by_name[table.name]["sha256"]
                    or count != by_name[table.name]["rows"]
                ):
                    raise ArchiveError("Restored row reconciliation failed")
            from .assurance import observe

            integrity = await observe(target)
            signatures_verified, reporting_hashes_verified = await verify_lineage(
                target, manifest, recovered_box, cfg
            )
            # Validate deferred hierarchy/foreign-key checks before trigger DDL;
            # PostgreSQL rejects DDL while deferred trigger events are pending.
            await target.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            await db.protect_history(target, namespace)
            protected = await target.scalar(
                text(
                    "select count(distinct event_object_table) from information_schema.triggers where trigger_schema=:schema and trigger_name='immutable_history'"
                ),
                {"schema": namespace},
            )
            if protected != 38:
                raise ArchiveError("Restored history protection incomplete")
            # Probe append-only protection using a savepoint; no original row is changed.
            from sqlalchemy.exc import DBAPIError

            for table, values in (
                (db.audit, {"outcome": "TAMPER"}),
                (db.evidence, {"source": "TAMPER"}),
            ):
                try:
                    async with target.begin_nested():
                        await target.execute(table.update().values(**values))
                except DBAPIError as exc:
                    if getattr(exc.orig, "sqlstate", None) != "P0001":
                        raise ArchiveError("History probe failed for an unrelated reason") from exc
                else:
                    if by_name[table.name]["rows"]:
                        raise ArchiveError("Restored history accepted mutation")
        if len(manifest["files"]) != len(expected_files) or {
            file["evidence_id"] for file in manifest["files"]
        } != set(expected_files):
            raise ArchiveError("Archive evidence inventory incomplete")
        for file in manifest["files"]:
            if (file["source_sha256"], file["source_size"]) != expected_files[file["evidence_id"]]:
                raise ArchiveError("Archive evidence metadata mismatch")
            content = await get_encrypted(objects, recovery_key, backup_id, file)
            if (
                hashlib.sha256(content).hexdigest() != file["source_sha256"]
                or len(content) != file["source_size"]
            ):
                raise ArchiveError("Recovered evidence bytes differ")
            target_key = f"continuity/rehearsals/{namespace}/{UUID(file['evidence_id'])!s}"
            copied_files.append(target_key)
            await asyncio.to_thread(objects.put, target_key, content)
            if await asyncio.to_thread(objects.get, target_key) != content:
                raise ArchiveError("Restored private file did not verify")
        summary = {
            "tables": len(manifest["tables"]),
            "rows": sum(t["rows"] for t in manifest["tables"]),
            "files": len(manifest["files"]),
            "decrypted_fields_verified": checked_ciphertexts,
            "clinical_signatures_verified": signatures_verified,
            "reporting_payload_hashes_verified": reporting_hashes_verified,
            "protected_history_tables": protected,
            "elapsed_seconds": round(monotonic() - timer, 3),
            "integrity": integrity,
            "activation_state": "ISOLATED_VERIFIED_NOT_ACTIVATED",
            "snapshot_at": manifest["snapshot_at"],
        }
    except Exception:
        if record_result:
            await assurance.record(
                database,
                SecretBox(cfg.data_key_hex),
                kind="RESTORE",
                outcome="FAILED",
                actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
                started_at=started,
                summary={"activated": False},
                source_id=backup_id,
                evidence={"category": "RESTORE_DID_NOT_VERIFY"},
            )
        raise
    finally:
        cleanup_failed = False
        for key in copied_files:
            try:
                if not key.startswith(f"continuity/rehearsals/{namespace}/"):
                    raise ArchiveError("Refusing foreign cleanup key")
                await asyncio.to_thread(objects.delete, key)
            except Exception:  # noqa: BLE001 -- attempt all cleanup, then fail explicitly
                cleanup_failed = True
        if created:
            try:
                if not re.fullmatch(r"lwh_restore_[0-9a-f]{32}", namespace):
                    raise ArchiveError("Refusing foreign cleanup schema")
                async with database.engine.begin() as connection:
                    await connection.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
            except Exception:  # noqa: BLE001 -- attempt all cleanup, then fail explicitly
                cleanup_failed = True
        if cleanup_failed:
            if record_result:
                await assurance.record(
                    database,
                    SecretBox(cfg.data_key_hex),
                    kind="RESTORE",
                    outcome="CLEANUP_REQUIRED",
                    actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
                    started_at=started,
                    summary={"activated": False},
                    source_id=backup_id,
                    evidence={
                        "rehearsal_schema": namespace,
                        "category": "REHEARSAL_CLEANUP_REQUIRED",
                    },
                )
            raise ArchiveError("Recovery rehearsal cleanup requires attention")
    summary["temporary_schema_and_files_removed"] = True
    if record_result:
        await assurance.record(
            database,
            SecretBox(cfg.data_key_hex),
            kind="RESTORE",
            outcome="RESTORED_WITH_EXCEPTIONS"
            if any(integrity["checks"].values())
            else "ISOLATED_VERIFIED",
            actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
            started_at=started,
            summary=summary,
            source_id=backup_id,
            evidence={"rehearsal_schema": namespace, "provider_delivery_attempted": False},
        )
    return summary
