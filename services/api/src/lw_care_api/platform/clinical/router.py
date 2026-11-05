"""Clinical HTTP boundary. Institutional roles never imply permission to read charts."""

import base64
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select, update

from .. import db
from ..domain import RuleError, require, valid_interval
from . import contracts as c
from . import store as s
from . import tables as t
from .continuity import EMRService

PREFIX = "/v1/clinical/{facility_id}"
KIND_CAPABILITIES = {
    "patient": ("REGISTER",),
    "encounter": ("CARE", "NURSING", "REGISTER"),
    "note": ("CARE", "NURSING"),
    "observation": ("CARE", "NURSING"),
    "problem": ("CARE", "NURSING"),
    "allergy": ("CARE", "NURSING", "PHARMACY"),
    "consent": ("CARE",),
    "task": ("CARE",),
    "order": ("CARE", "DIAGNOSTICS"),
    "specimen": ("DIAGNOSTICS",),
    "result": ("CARE", "DIAGNOSTICS"),
    "product": ("PHARMACY", "PRESCRIBE", "NURSING", "CARE"),
    "medication": ("PRESCRIBE", "PHARMACY", "NURSING", "CARE"),
    "dispense": ("PHARMACY", "NURSING", "CARE"),
    "administration": ("NURSING", "CARE"),
    "stay": ("CARE", "NURSING"),
    "programme": ("CARE",),
    "procedure": ("PROCEDURE",),
    "transfusion": ("PROCEDURE",),
    "referral": ("CARE",),
    "record_error": ("RECORDS", "CARE"),
    "sharing_grant": ("CARE",),
    "disclosure": ("CARE",),
    "appointment": ("REGISTER", "CARE"),
    "identity_link": ("RECORDS",),
    "tariff": ("FINANCE", "CASHIER"),
    "invoice": ("FINANCE", "CASHIER"),
    "cash_receipt": ("FINANCE", "CASHIER"),
}


def governor(actor, facility_id):
    return any(
        g["role"] == "CLINICAL_GOVERNOR"
        and (
            g["scope_type"] == "GLOBAL"
            or (g["scope_type"] == "FACILITY" and g["scope_id"] == facility_id)
        )
        for g in actor["grants"]
    )


async def any_privilege(session, actor, facility_id, capabilities, service=None):
    for capability in capabilities:
        try:
            return capability, await s.privilege_for(
                session, actor["id"], facility_id, capability, service
            )
        except RuleError as exc:
            if exc.code not in {"CLINICAL_PRIVILEGE_REQUIRED"}:
                raise
    require(False, "CLINICAL_PRIVILEGE_REQUIRED", "Current clinical privileges are required")


async def readable(session, cfg, actor, row, box):
    await s.site_for(session, cfg, row["facility_id"])
    capability, _ = await any_privilege(
        session,
        actor,
        row["facility_id"],
        KIND_CAPABILITIES[row["kind"]],
        None
        if row["kind"] in {"patient", "product", "tariff", "invoice", "cash_receipt"}
        else row["service"],
    )
    data = s.opened(box, row)["data"] if row["kind"] == "encounter" else {}
    awaiting_acceptance = row["kind"] == "encounter" and (
        data.get("owner_id") is None or actor["id"] in data.get("proposed_team_ids", [])
    )
    if capability == "REGISTER" and row["kind"] == "encounter":
        require(
            data.get("owner_id") is None and row["status"] == "ARRIVED",
            "ACCESS_DENIED",
            "Registration access is limited to unclaimed arrivals",
        )
    if (
        row["patient_id"]
        and not awaiting_acceptance
        and capability
        not in {
            "REGISTER",
            "DIAGNOSTICS",
            "PHARMACY",
            "RECORDS",
            "FINANCE",
            "CASHIER",
        }
    ):
        await s.member_for(session, actor["id"], row["facility_id"], row["patient_id"])
    if row["confidentiality"] == "RESTRICTED":
        await s.privilege_for(session, actor["id"], row["facility_id"], "SENSITIVE", row["service"])


def install(app, cfg, database, box, actor_for):
    router = APIRouter()

    async def presented(session, row):
        resource = s.opened(box, row)
        if row["patient_id"]:
            patient = await s.fetch(session, row["facility_id"], row["patient_id"], "patient")
            data = s.opened(box, patient)["data"]
            resource["patient_banner"] = {
                key: data.get(key)
                for key in ("display_name", "local_identifier", "birth_date", "sex", "provisional")
            }
        return resource

    async def command(request, facility_id, payload, method, identifier=None, *, governance=False):
        body = payload.model_dump(mode="json")
        actor = None
        try:
            async with database.transaction() as session:
                actor = await actor_for(session, request)
                if not governance:
                    await s.site_for(session, cfg, facility_id, write=True)
                service = EMRService(
                    session, cfg, box, actor, facility_id, request.state.correlation_id
                )

                async def replay_guard(response):
                    if governance:
                        require(governor(actor, facility_id))
                        return
                    await s.site_for(session, cfg, facility_id, write=True)
                    resource = response["resource"]
                    if resource.get("kind"):
                        current = await s.fetch(session, facility_id, resource["id"])
                        await readable(session, cfg, actor, current, box)
                        if resource["kind"] == "disclosure":
                            content = resource["data"]
                            await service.valid_share(
                                content["sharing_grant_id"],
                                current["patient_id"],
                                content["recipient"],
                                content["purpose"],
                            )
                            for source in resource.get("package", {}).get("sources", []):
                                source_row = await s.fetch(session, facility_id, source["id"])
                                await readable(session, cfg, actor, source_row, box)
                                await service.usable(source_row)
                    else:
                        await any_privilege(
                            session,
                            actor,
                            facility_id,
                            ("PHARMACY",) if "quantity" in resource else ("REGISTER",),
                        )

                async def apply():
                    if callable(method):
                        result = await method(session, actor, body, service)
                    else:
                        result = (
                            await getattr(service, method)(identifier, body)
                            if identifier
                            else await getattr(service, method)(body)
                        )
                    return s.receipt(cfg, result)

                return await s.idempotent(
                    session,
                    database,
                    cfg,
                    box,
                    actor,
                    facility_id,
                    request.url.path,
                    request.headers.get("Idempotency-Key"),
                    body,
                    apply,
                    replay_guard,
                )
        except RuleError:
            request.state.clinical_denial_recorded = True
            async with database.transaction() as session:
                await s.audit(
                    session,
                    actor,
                    facility_id,
                    body.get("patient_id"),
                    request.url.path.split("/")[-1],
                    request.state.correlation_id,
                    "DENIED",
                )
            raise

    @router.get("/v1/clinical/sites")
    async def sites(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed = [
                g["scope_id"]
                for g in actor["grants"]
                if g["role"] == "CLINICAL_GOVERNOR" and g["scope_type"] == "FACILITY"
            ]
            global_governor = governor(actor, "GLOBAL")
            privilege_rows = [
                dict(p)
                for p in (
                    await session.execute(
                        select(t.privileges).where(
                            t.privileges.c.account_id == actor["id"],
                            t.privileges.c.revoked.is_(False),
                            t.privileges.c.valid_from <= db.now(),
                            t.privileges.c.valid_until > db.now(),
                        )
                    )
                ).mappings()
            ]
            allowed.extend(p["facility_id"] for p in privilege_rows)
            query = select(
                db.facilities.c.id,
                db.facilities.c.name,
                db.facilities.c.jurisdiction,
                db.facilities.c.identity_status,
            )
            if not global_governor:
                query = query.where(db.facilities.c.id.in_(allowed))
            facilities = [
                dict(f)
                for f in (
                    await session.execute(query.order_by(db.facilities.c.name).limit(200))
                ).mappings()
            ]
            configurations = {
                r["facility_id"]: dict(r)
                for r in (
                    await session.execute(
                        select(t.sites).where(
                            t.sites.c.facility_id.in_([f["id"] for f in facilities])
                        )
                    )
                ).mappings()
            }
            return {
                "items": [
                    {
                        **f,
                        "activation": configurations.get(f["id"]),
                        "governor": governor(actor, f["id"]),
                        "privileges": [p for p in privilege_rows if p["facility_id"] == f["id"]],
                    }
                    for f in facilities
                ],
                "as_of": db.now(),
            }

    @router.post(PREFIX + "/activation")
    async def activation(facility_id: UUID, payload: c.Activation, request: Request):
        async def apply(session, actor, body, service):
            require(governor(actor, str(facility_id)))
            valid_interval(payload.valid_from, payload.valid_until)
            require(
                payload.valid_until > datetime.now(UTC),
                "VALIDATION_FAILED",
                "Activation must have a future expiry",
                422,
            )
            facility = (
                (
                    await session.execute(
                        select(db.facilities)
                        .where(db.facilities.c.id == str(facility_id))
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(
                facility
                and facility["identity_status"] == "VERIFIED"
                and facility["statutory_status"] in {"CHECKED", "NOT_APPLICABLE"},
                "FACILITY_VERIFICATION_REQUIRED",
                "Verify facility identity and statutory status before clinical activation",
                409,
            )
            current = (
                (
                    await session.execute(
                        select(t.sites)
                        .where(t.sites.c.facility_id == str(facility_id))
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(
                body["expected_version"] == (current["version"] if current else 0),
                "VERSION_CONFLICT",
                "Facility activation changed",
                412,
            )
            values = {
                k: body[k]
                for k in (
                    "services",
                    "policy_reference",
                    "manual_medicine_policy",
                    "valid_from",
                    "valid_until",
                )
            }
            values.update(
                active=True,
                approved_by=actor["id"],
                version=body["expected_version"] + 1,
                authority_node_id=cfg.authority_node_id,
                authority_epoch="1",
            )
            if current:
                require(
                    current["authority_node_id"] == cfg.authority_node_id,
                    "AUTHORITY_HANDOVER_REQUIRED",
                    "A different writer requires a fenced authority handover",
                    409,
                )
                await session.execute(
                    update(t.sites).where(t.sites.c.id == current["id"]).values(**values)
                )
                identifier = current["id"]
            else:
                identifier = db.uid()
                await session.execute(
                    t.sites.insert().values(id=identifier, facility_id=str(facility_id), **values)
                )
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "activation.scope_changed",
                request.state.correlation_id,
                purpose="CLINICAL_GOVERNANCE",
            )
            return {"id": identifier, "facility_id": str(facility_id), **values}

        return await command(request, str(facility_id), payload, apply, governance=True)

    @router.get(PREFIX + "/privileges")
    async def privileges(facility_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(governor(actor, str(facility_id)))
            rows = [
                dict(r)
                for r in (
                    await session.execute(
                        select(t.privileges)
                        .where(t.privileges.c.facility_id == str(facility_id))
                        .order_by(t.privileges.c.valid_until.desc())
                        .limit(200)
                    )
                ).mappings()
            ]
            return {"items": rows}

    @router.post(PREFIX + "/privileges")
    async def privilege(facility_id: UUID, payload: c.Privilege, request: Request):
        async def apply(session, actor, body, service):
            require(
                governor(actor, str(facility_id)) and body["account_id"] != actor["id"],
                "ACCESS_DENIED",
                "A separate clinical governor must approve another professional's privileges",
            )
            site = await s.site_for(session, cfg, str(facility_id), write=True)
            valid_interval(payload.valid_from, payload.valid_until)
            require(
                set(body["services"]).issubset(site["services"])
                and body["valid_until"] <= site["valid_until"]
                and body["valid_until"] > db.now(),
                "VALIDATION_FAILED",
                "Privileges must fit the activated services and validity",
                422,
            )
            active = await session.scalar(
                select(db.accounts.c.active).where(db.accounts.c.id == body["account_id"])
            )
            require(
                active,
                "ACCOUNT_ACTIVATION_REQUIRED",
                "The invited professional must first activate their account",
                409,
            )
            values = {
                k: body[k]
                for k in (
                    "account_id",
                    "services",
                    "capabilities",
                    "professional_reference",
                    "valid_from",
                    "valid_until",
                )
            }
            values.update(
                id=db.uid(), facility_id=str(facility_id), revoked=False, approved_by=actor["id"]
            )
            await session.execute(t.privileges.insert().values(**values))
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "clinical.privilege_granted",
                request.state.correlation_id,
                purpose="CLINICAL_GOVERNANCE",
            )
            return values

        return await command(request, str(facility_id), payload, apply, governance=True)

    @router.post(PREFIX + "/privileges/{privilege_id}/revoke")
    async def revoke_privilege(
        facility_id: UUID, privilege_id: UUID, payload: c.StrictModel, request: Request
    ):
        async def apply(session, actor, body, service):
            require(governor(actor, str(facility_id)))
            await s.site_for(session, cfg, str(facility_id), write=True)
            row = (
                (
                    await session.execute(
                        select(t.privileges)
                        .where(
                            t.privileges.c.id == str(privilege_id),
                            t.privileges.c.facility_id == str(facility_id),
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Privilege unavailable", 404)
            await session.execute(
                update(t.privileges)
                .where(t.privileges.c.id == str(privilege_id))
                .values(revoked=True)
            )
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "clinical.privilege_revoked",
                request.state.correlation_id,
                purpose="CLINICAL_GOVERNANCE",
            )
            return {"id": str(privilege_id), "revoked": True}

        return await command(request, str(facility_id), payload, apply, governance=True)

    @router.get(PREFIX + "/staff")
    async def staff(facility_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            is_governor = governor(actor, str(facility_id))
            if not is_governor:
                await s.site_for(session, cfg, str(facility_id))
                await any_privilege(
                    session,
                    actor,
                    str(facility_id),
                    (
                        "CARE",
                        "NURSING",
                        "REGISTER",
                        "PHARMACY",
                        "DIAGNOSTICS",
                        "PROCEDURE",
                        "FINANCE",
                        "CASHIER",
                    ),
                )
            rows = (
                await session.execute(
                    select(
                        db.accounts.c.id,
                        db.accounts.c.name,
                        t.privileges.c.capabilities,
                        t.privileges.c.services,
                    )
                    .join(t.privileges, t.privileges.c.account_id == db.accounts.c.id)
                    .where(
                        t.privileges.c.facility_id == str(facility_id),
                        t.privileges.c.revoked.is_(False),
                        t.privileges.c.valid_from <= db.now(),
                        t.privileges.c.valid_until > db.now(),
                        db.accounts.c.active.is_(True),
                    )
                    .limit(200)
                )
            ).mappings()
            result = [dict(r) for r in rows]
            if is_governor:
                # Eligible invitation recipients carry no chart authority until separately privileged.
                invited = (
                    await session.execute(
                        select(db.accounts.c.id, db.accounts.c.name)
                        .join(db.grants)
                        .where(
                            db.grants.c.role == "CLINICAL_STAFF",
                            db.grants.c.scope_type == "FACILITY",
                            db.grants.c.scope_id == str(facility_id),
                            db.grants.c.revoked.is_(False),
                            db.grants.c.valid_until > db.now(),
                            db.accounts.c.active.is_(True),
                        )
                        .limit(200)
                    )
                ).mappings()
                known = {r["id"] for r in result}
                result.extend(
                    {**dict(r), "capabilities": [], "services": []}
                    for r in invited
                    if r["id"] not in known
                )
            return {"items": result}

    @router.post(PREFIX + "/patient-search")
    async def search(facility_id: UUID, payload: c.Search, request: Request):
        facility = str(facility_id)
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.guard(session, cfg, actor, facility, "REGISTER", relationship=False)
            tokens = s.search_tokens(cfg, payload.query)
            require(
                tokens,
                "VALIDATION_FAILED",
                "Enter at least one searchable name or identifier token",
                422,
            )
            query = select(t.records).where(
                t.records.c.facility_id == facility,
                t.records.c.kind == "patient",
                t.records.c.id > payload.after,
            )
            if database.postgres:
                from sqlalchemy.dialects.postgresql import JSONB

                query = query.where(t.records.c.search_tokens.cast(JSONB).contains(tokens))
            candidates = (
                await session.execute(query.order_by(t.records.c.id).limit(501))
            ).mappings()
            matches = [r for r in candidates if set(tokens).issubset(r["search_tokens"] or [])][:51]
            rows = [s.opened(box, r) for r in matches[:50]]
            await s.audit(
                session,
                actor,
                facility,
                None,
                "records.patient_searched",
                request.state.correlation_id,
                purpose="REGISTRATION",
            )
            return {
                "items": rows,
                "next_cursor": rows[-1]["id"] if len(matches) > 50 else None,
                "as_of": db.now(),
            }

    @router.get(PREFIX + "/records/{record_id}")
    async def record(facility_id: UUID, record_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            row = await s.fetch(session, str(facility_id), record_id)
            await readable(session, cfg, actor, row, box)
            await s.audit(
                session,
                actor,
                str(facility_id),
                row["patient_id"],
                "records.record_read",
                request.state.correlation_id,
            )
            return await presented(session, row)

    @router.get(PREFIX + "/patients/{patient_id}/chart")
    async def chart(facility_id: UUID, patient_id: UUID, request: Request, after: str = ""):
        facility, patient = str(facility_id), str(patient_id)
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, facility)
            await any_privilege(session, actor, facility, ("CARE", "NURSING", "RECORDS"))
            # Records custodians use the explicit record/history path; ordinary chart browsing requires treatment.
            await s.member_for(session, actor["id"], facility, patient)
            patient_row = await s.fetch(session, facility, patient, "patient")
            query = (
                select(t.records)
                .where(
                    t.records.c.facility_id == facility,
                    t.records.c.patient_id == patient,
                    t.records.c.id > after,
                )
                .order_by(t.records.c.id)
                .limit(201)
            )
            candidates = list((await session.execute(query)).mappings())
            visible, withheld = [], 0
            for row in candidates[:200]:
                try:
                    await readable(session, cfg, actor, row, box)
                except RuleError as exc:
                    if exc.status not in {403, 404}:
                        raise
                    withheld += 1
                else:
                    visible.append(s.opened(box, row))
            allergy_rows = [r for r in visible if r["kind"] == "allergy"]
            await s.audit(
                session,
                actor,
                facility,
                patient,
                "records.chart_read",
                request.state.correlation_id,
            )
            return {
                "patient": s.opened(box, patient_row),
                "items": visible,
                "allergy_assessment": "UNKNOWN"
                if not allergy_rows
                else "SEE_ATTRIBUTED_ASSESSMENTS",
                "withheld_records": withheld,
                "as_of": db.now(),
                "next_cursor": candidates[199]["id"] if len(candidates) > 200 else None,
                "automated_medication_checking": "UNAVAILABLE_MANUAL_CLINICAL_REVIEW_REQUIRED",
            }

    @router.get(PREFIX + "/worklist")
    async def worklist(facility_id: UUID, request: Request, kind: str = "task", after: str = ""):
        facility = str(facility_id)
        allowed = {
            "sharing_grant",
            "disclosure",
            "appointment",
            "identity_link",
            "tariff",
            "invoice",
            "cash_receipt",
            "task",
            "encounter",
            "order",
            "specimen",
            "result",
            "medication",
            "procedure",
            "programme",
            "stay",
            "referral",
            "product",
        }
        require(kind in allowed, "VALIDATION_FAILED", "Choose a supported clinical worklist", 422)
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, facility)
            await any_privilege(session, actor, facility, KIND_CAPABILITIES[kind])
            query = (
                select(t.records)
                .where(
                    t.records.c.facility_id == facility,
                    t.records.c.kind == kind,
                    t.records.c.id > after,
                )
                .order_by(t.records.c.id)
                .limit(201)
            )
            candidates = list((await session.execute(query)).mappings())
            visible = []
            for row in candidates[:200]:
                try:
                    await readable(session, cfg, actor, row, box)
                except RuleError as exc:
                    if exc.status not in {403, 404}:
                        raise
                    continue
                opened = await presented(session, row)
                if kind == "task" and actor["id"] not in {
                    opened["data"]["owner_id"],
                    opened["data"].get("handover_to"),
                }:
                    continue
                visible.append(opened)
            await s.audit(
                session,
                actor,
                facility,
                None,
                "clinical.worklist_read",
                request.state.correlation_id,
            )
            return {
                "items": visible,
                "as_of": db.now(),
                "next_cursor": candidates[199]["id"] if len(candidates) > 200 else None,
            }

    @router.get(PREFIX + "/beds")
    async def beds(facility_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, str(facility_id))
            await any_privilege(session, actor, str(facility_id), ("REGISTER", "CARE", "NURSING"))
            return {
                "items": [
                    dict(r)
                    for r in (
                        await session.execute(
                            select(t.beds)
                            .where(t.beds.c.facility_id == str(facility_id))
                            .limit(500)
                        )
                    ).mappings()
                ]
            }

    @router.get(PREFIX + "/stock")
    async def stock(facility_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, str(facility_id))
            await any_privilege(
                session, actor, str(facility_id), ("PHARMACY", "PRESCRIBE", "NURSING")
            )
            return {
                "items": [
                    {**dict(r), "quantity": str(r["quantity"])}
                    for r in (
                        await session.execute(
                            select(t.lots)
                            .where(t.lots.c.facility_id == str(facility_id))
                            .limit(500)
                        )
                    ).mappings()
                ]
            }

    @router.get(PREFIX + "/audit")
    async def access_history(facility_id: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.guard(session, cfg, actor, str(facility_id), "RECORDS", relationship=False)
            rows = [
                dict(r)
                for r in (
                    await session.execute(
                        select(t.audit)
                        .where(t.audit.c.facility_id == str(facility_id), t.audit.c.id > after)
                        .order_by(t.audit.c.id)
                        .limit(101)
                    )
                ).mappings()
            ]
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "records.access_history_read",
                request.state.correlation_id,
                purpose="RECORDS_CUSTODY",
            )
            return {"items": rows[:100], "next_cursor": rows[99]["id"] if len(rows) > 100 else None}

    @router.get(PREFIX + "/records/{record_id}/history")
    async def history(facility_id: UUID, record_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            row = await s.fetch(session, str(facility_id), record_id)
            await readable(session, cfg, actor, row, box)
            rows = list(
                (
                    await session.execute(
                        select(t.events)
                        .where(t.events.c.record_id == str(record_id))
                        .order_by(t.events.c.version)
                        .limit(500)
                    )
                ).mappings()
            )
            items = [
                {k: v for k, v in r.items() if k != "payload_ciphertext"}
                | {"source": json.loads(box.decrypt(r["payload_ciphertext"]))}
                for r in rows
            ]
            await s.audit(
                session,
                actor,
                str(facility_id),
                row["patient_id"],
                "records.history_read",
                request.state.correlation_id,
            )
            return {
                "items": items,
                "attestation_public_key": base64.b64encode(
                    s.signing_key(cfg).public_key().public_bytes_raw()
                ).decode(),
                "signature_semantics": "SERVER_ATTESTED_AUTHENTICATED_AUTHOR_INTENT",
            }

    @router.post(PREFIX + "/medications/{record_id}/occurrence")
    async def occurrence(
        facility_id: UUID, record_id: UUID, payload: c.Occurrence, request: Request
    ):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            row = await s.fetch(session, str(facility_id), record_id, "medication")
            await readable(session, cfg, actor, row, box)
            require(
                row["patient_id"] == str(payload.patient_id),
                "PATIENT_CONTEXT_MISMATCH",
                "Check the patient",
                409,
            )
            slot = f"{record_id}:{payload.model_dump(mode='json')['scheduled_at']}"
            return {
                "occurrence_key": s.keyed_hash(cfg, "administration_slot", slot),
                "order_version": row["version"],
            }

    @router.post(PREFIX + "/encounters/{record_id}/team")
    async def team(facility_id: UUID, record_id: UUID, payload: c.TeamOffer, request: Request):
        async def apply(session, actor, body, service):
            row = await service.linked(str(record_id), "encounter", body["patient_id"])
            await service.guard(
                "CARE", patient_id=row["patient_id"], encounter_id=row["id"], write=True
            )
            data = service.content(row)
            require(
                data["owner_id"] == actor["id"] and row["status"] != "COMPLETED",
                "ACCESS_DENIED",
                "The current encounter owner must propose team assignments",
            )
            await s.privilege_for(
                session, body["account_id"], str(facility_id), body["capability"], row["service"]
            )
            data.setdefault("proposed_team_ids", []).append(body["account_id"])
            return await service.change(
                row,
                data,
                row["status"],
                body["expected_version"],
                "clinical.encounter_changed",
                "LWH-EVT-015",
            )

        return await command(request, str(facility_id), payload, apply)

    def create_route(path, model, method):
        async def endpoint(facility_id: UUID, payload: model, request: Request):
            return await command(request, str(facility_id), payload, method)

        endpoint.__name__ = "clinical_create_" + path.replace("-", "_")
        router.add_api_route(PREFIX + "/" + path, endpoint, methods=["POST"])

    def action_route(path, model, method):
        async def endpoint(facility_id: UUID, record_id: UUID, payload: model, request: Request):
            return await command(request, str(facility_id), payload, method, str(record_id))

        endpoint.__name__ = "clinical_action_" + path.replace("/", "_").replace("-", "_")
        router.add_api_route(
            PREFIX + "/" + path.replace("{id}", "{record_id}"), endpoint, methods=["POST"]
        )

    for path, model, method in [
        ("patients", c.Patient, "patient"),
        ("encounters", c.Encounter, "encounter"),
        ("notes", c.Note, "note"),
        ("consents", c.Consent, "consent"),
        ("tasks", c.Task, "create_task"),
        ("orders", c.Order, "order"),
        ("specimens", c.Specimen, "specimen"),
        ("results", c.Result, "result"),
        ("products", c.Product, "product"),
        ("medications", c.Medication, "medication"),
        ("stock", c.Lot, "lot"),
        ("dispenses", c.Dispense, "dispense"),
        ("administrations", c.Administration, "administration"),
        ("beds", c.Bed, "bed"),
        ("admissions", c.Admission, "admission"),
        ("programmes", c.Programme, "programme"),
        ("procedures", c.Procedure, "procedure"),
        ("transfusions", c.Transfusion, "transfusion"),
        ("referrals", c.Referral, "referral"),
        ("sharing-grants", c.SharingGrant, "sharing_grant"),
        ("disclosures", c.Disclosure, "disclosure"),
        ("appointments", c.Appointment, "appointment"),
        ("identity-links", c.IdentityLink, "identity_link"),
        ("tariffs", c.Tariff, "tariff"),
        ("invoices", c.Invoice, "invoice"),
        ("cash-receipts", c.CashReceipt, "cash_receipt"),
    ]:
        create_route(path, model, method)

    for path, model, kind in [
        ("observations", c.Observation, "observation"),
        ("problems", c.Problem, "problem"),
        ("allergies", c.Allergy, "allergy"),
    ]:

        def fact_handler(record_kind):
            async def apply(session, actor, body, service):
                return await service.fact(record_kind, body)

            return apply

        create_route(path, model, fact_handler(kind))

    for path, model, method in [
        ("patients/{id}/corrections", c.PatientCorrection, "correct_patient"),
        ("notes/{id}/draft", c.NoteEdit, "edit_note"),
        ("notes/{id}/sign", c.Sign, "sign_note"),
        ("tasks/{id}/actions", c.TaskAction, "task_action"),
        ("orders/{id}/actions", c.OrderAction, "order_action"),
        ("specimens/{id}/actions", c.SpecimenAction, "specimen_action"),
        ("results/{id}/actions", c.ResultAction, "result_action"),
        ("medications/{id}/actions", c.MedicationAction, "medication_action"),
        ("stock/{id}/actions", c.LotAction, "lot_action"),
        ("stays/{id}/actions", c.StayAction, "stay_action"),
        ("programmes/{id}/reviews", c.ProgrammeReview, "programme_review"),
        ("procedures/{id}/actions", c.ProcedureAction, "procedure_action"),
        ("transfusions/{id}/actions", c.TransfusionAction, "transfusion_action"),
        ("referrals/{id}/actions", c.ReferralAction, "referral_action"),
        ("sharing-grants/{id}/revoke", c.RecordError, "revoke_sharing"),
        ("appointments/{id}/actions", c.AppointmentAction, "appointment_action"),
        ("identity-links/{id}/actions", c.IdentityLinkAction, "identity_link_action"),
        ("records/{id}/entered-in-error", c.RecordError, "record_error"),
    ]:
        action_route(path, model, method)

    for suffix, model, action in [
        ("start", c.Sign, "start"),
        ("claim", c.Sign, "claim"),
        ("join", c.Sign, "join"),
        ("triage", c.Triage, "triage"),
        ("complete", c.Disposition, "complete"),
    ]:

        def encounter_handler(selected_action, selected_model):
            async def endpoint(
                facility_id: UUID, record_id: UUID, payload: selected_model, request: Request
            ):
                async def apply(session, actor, body, service):
                    return await service.encounter_action(str(record_id), body, selected_action)

                return await command(request, str(facility_id), payload, apply)

            return endpoint

        router.add_api_route(
            PREFIX + "/encounters/{record_id}/" + suffix,
            encounter_handler(action, model),
            methods=["POST"],
            name="clinical_encounter_" + action,
        )

    app.include_router(router)
