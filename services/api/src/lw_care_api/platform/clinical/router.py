"""Clinical HTTP boundary. Institutional roles never imply permission to read charts."""

import base64
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import exists, func, or_, select, update

from .. import db
from ..domain import RuleError, require, valid_interval
from . import advanced_contracts as ac
from . import contracts as c
from . import flow_index as fi
from . import store as s
from . import tables as t
from .specialties import Phase5Service as EMRService

PREFIX = "/v1/clinical/{facility_id}"
KIND_CAPABILITIES = {
    "patient": ("REGISTER",),
    "encounter": ("CARE", "NURSING", "REGISTER"),
    "note": ("CARE", "NURSING"),
    "observation": ("CARE", "NURSING"),
    "problem": ("CARE", "NURSING"),
    "allergy": ("CARE", "NURSING", "PHARMACY"),
    "consent": ("CARE",),
    "task": ("CARE", "NURSING"),
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
    "service_capacity": ("CARE", "NURSING", "DIAGNOSTICS", "PHARMACY", "PROCEDURE"),
    "duty_shift": ("CARE", "NURSING", "DIAGNOSTICS", "PHARMACY", "PROCEDURE"),
    "team_handover": ("CARE", "NURSING"),
    "admission_order": ("CARE", "NURSING"),
    "bed_hold": ("CARE", "NURSING"),
    "nursing_assessment": ("NURSING", "CARE"),
    "fluid_entry": ("NURSING", "CARE"),
    "labour_observation": ("CARE",),
    "birth": ("CARE",),
    "birth_link": ("CARE",),
    "child_measurement": ("CARE",),
    "immunisation": ("NURSING", "CARE"),
    "medicine_reconciliation": ("CARE", "PRESCRIBE", "PHARMACY"),
    "stock_hold": ("PHARMACY",),
    "stock_adjustment": ("PHARMACY",),
    "stock_return": ("PHARMACY",),
    "substitution": ("PHARMACY", "PRESCRIBE"),
    "anaesthesia_observation": ("PROCEDURE",),
    "device_use": ("PROCEDURE",),
    "clinical_recall": ("PROCEDURE", "CARE"),
    "care_instructions": ("CARE", "NURSING"),
    "infusion_event": ("NURSING", "CARE"),
    "infusion_witness": ("NURSING", "CARE"),
}
ADVANCED_KINDS = set(KIND_CAPABILITIES) - {
    "patient",
    "encounter",
    "note",
    "observation",
    "problem",
    "allergy",
    "consent",
    "task",
    "order",
    "specimen",
    "result",
    "product",
    "medication",
    "dispense",
    "administration",
    "stay",
    "programme",
    "procedure",
    "transfusion",
    "referral",
    "record_error",
    "sharing_grant",
    "disclosure",
    "appointment",
    "identity_link",
    "tariff",
    "invoice",
    "cash_receipt",
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
    if row["kind"] in {"service_capacity", "duty_shift"} and governor(actor, row["facility_id"]):
        return
    capability, _ = await any_privilege(
        session,
        actor,
        row["facility_id"],
        KIND_CAPABILITIES[row["kind"]],
        None
        if row["kind"]
        in {"patient", "product", "tariff", "invoice", "cash_receipt", "stock_adjustment"}
        else row["service"],
    )
    data = s.opened(box, row)["data"] if row["kind"] == "encounter" else {}
    awaiting_acceptance = row["kind"] == "encounter" and (
        data.get("owner_id") is None or actor["id"] in data.get("proposed_team_ids", [])
    )
    if row["kind"] in {"team_handover", "substitution"}:
        content = s.opened(box, row)["data"]
        awaiting_acceptance = content.get("recipient_id") == actor["id"]
    if row["kind"] == "stay":
        content = s.opened(box, row)["data"]
        if (
            content.get("responsible_nurse_id") == actor["id"]
            and content.get("nursing_responsibility_state") != "ACCEPTED"
        ):
            await s.privilege_for(
                session, actor["id"], row["facility_id"], "NURSING", row["service"]
            )
            awaiting_acceptance = True
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
        if row["kind"] in {"bed_hold", "stock_hold", "duty_shift", "service_capacity"}:
            end = resource["data"].get("expires_at") or resource["data"].get("ends_at")
            if (
                end
                and end <= db.now()
                and row["status"] in {"HELD", "OFFERED", "ACCEPTED", "CONFIGURED"}
            ):
                resource["availability_state"] = "EXPIRED"
        if row["patient_id"]:
            markers = (
                await session.execute(
                    select(t.records).where(
                        t.records.c.facility_id == row["facility_id"],
                        t.records.c.patient_id == row["patient_id"],
                        t.records.c.kind == "record_error",
                    )
                )
            ).mappings()
            if any(s.opened(box, marker)["data"]["target_id"] == row["id"] for marker in markers):
                resource["use_restriction"] = "ENTERED_IN_ERROR"
        if row["patient_id"]:
            patient = await s.fetch(session, row["facility_id"], row["patient_id"], "patient")
            data = s.opened(box, patient)["data"]
            resource["patient_banner"] = {
                key: data.get(key)
                for key in ("display_name", "local_identifier", "birth_date", "sex", "provisional")
            }
        return resource

    def listed(resource):
        if len(json.dumps(resource, default=str).encode()) > 48000:
            resource["data"] = {
                key: value
                for key, value in resource["data"].items()
                if key
                in {
                    "title",
                    "owner_id",
                    "owner_capability",
                    "source_id",
                    "due_at",
                    "code",
                    "note_type",
                    "programme_type",
                    "order_type",
                    "result_owner_id",
                    "account_id",
                    "recipient_id",
                }
            }
            resource["detail_required"] = True
        return resource

    async def command(request, facility_id, payload, method, identifier=None, *, governance=False):
        body = payload.model_dump(mode="json")
        actor = None
        if request.url.path.split("/")[4:5] == ["workflows"]:
            require(
                cfg.advanced_clinical_enabled,
                "ADVANCED_CLINICAL_PAUSED",
                "Advanced clinical commands are paused; existing records remain available",
                503,
            )
            require(
                (await database.version() or 0) >= 7,
                "CLINICAL_WORKFLOW_MIGRATION_REQUIRED",
                "This workflow awaits migration 7",
                503,
            )
            if body.get("occurred_at"):
                s.event_time(body["occurred_at"])
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
            package = None
            if cfg.production or cfg.enforce_activation_dossiers:
                require(
                    (await database.version() or 0) >= 4,
                    "CONTROLS_MIGRATION_REQUIRED",
                    "Clinical activation awaits the operating-control migration",
                    503,
                )
                from ..control.service import validate_activation

                package = await validate_activation(session, cfg, box, actor, dict(facility), body)
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
            if package:
                from ..control import tables as controls

                await session.execute(
                    controls.site_packages.insert().values(
                        id=db.uid(),
                        facility_id=str(facility_id),
                        site_version=values["version"],
                        package_id=package["id"],
                        actor_id=actor["id"],
                        created_at=db.now(),
                    )
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
                .limit(26)
            )
            candidates = list((await session.execute(query)).mappings())
            visible, withheld = [], 0
            for row in candidates[:25]:
                try:
                    await readable(session, cfg, actor, row, box)
                except RuleError as exc:
                    if exc.status not in {403, 404}:
                        raise
                    withheld += 1
                else:
                    visible.append(listed(await presented(session, row)))
            allergy_rows = []
            for row in (
                await session.execute(
                    select(t.records)
                    .where(
                        t.records.c.facility_id == facility,
                        t.records.c.patient_id == patient,
                        t.records.c.kind == "allergy",
                    )
                    .order_by(t.records.c.updated_at.desc(), t.records.c.id)
                    .limit(21)
                )
            ).mappings():
                await readable(session, cfg, actor, row, box)
                allergy_rows.append(await presented(session, row))
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
                "allergy_assessments": allergy_rows[:20],
                "additional_allergy_history": len(allergy_rows) > 20,
                "withheld_records": withheld,
                "as_of": db.now(),
                "next_cursor": candidates[24]["id"] if len(candidates) > 25 else None,
                "automated_medication_checking": "UNAVAILABLE_MANUAL_CLINICAL_REVIEW_REQUIRED",
            }

    @router.get(PREFIX + "/worklist")
    async def worklist(
        facility_id: UUID, request: Request, kind: str = "task", after: str = "", trace: str = ""
    ):
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
        allowed |= ADVANCED_KINDS
        allowed |= {"dispense", "administration", "transfusion"}
        require(kind in allowed, "VALIDATION_FAILED", "Choose a supported clinical worklist", 422)
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            version = await session.scalar(select(func.max(db.schema_versions.c.version)))
            if kind in ADVANCED_KINDS:
                require(
                    version >= 7,
                    "CLINICAL_WORKFLOW_MIGRATION_REQUIRED",
                    "This workflow awaits migration 7",
                    503,
                )
            await s.site_for(session, cfg, facility)
            governing = kind in {"service_capacity", "duty_shift"} and governor(actor, facility)
            if not governing:
                await any_privilege(session, actor, facility, KIND_CAPABILITIES[kind])
            query = (
                select(t.records)
                .where(
                    t.records.c.facility_id == facility,
                    t.records.c.kind == kind,
                    t.records.c.id > ("" if kind == "task" and after.startswith("due.") else after),
                )
                .order_by(t.records.c.id)
                .limit(26)
            )
            if version >= 7:
                require(
                    await fi.ready(session),
                    "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
                    "Reconcile the clinical work index from current sources",
                    503,
                )
                query = query.join(fi.index, fi.index.c.record_id == t.records.c.id)
                if trace:
                    require(
                        kind in {"device_use", "transfusion"} and len(trace) <= 160,
                        "INVALID_TRACE_QUERY",
                        "Search the exact local component identifier or device serial/lot",
                        422,
                    )
                    query = query.where(
                        fi.index.c.trace_hash == s.keyed_hash(cfg, "trace", trace.strip())
                    )
                if kind == "task" and (not after or after.startswith("due.")):
                    query = query.order_by(None).order_by(fi.index.c.due_at, t.records.c.id)
                    if after:
                        try:
                            cursor_due, cursor_id = json.loads(
                                base64.urlsafe_b64decode(after[4:] + "=" * (-len(after[4:]) % 4))
                            )
                            require(
                                isinstance(cursor_due, str)
                                and len(cursor_due) <= 40
                                and str(UUID(cursor_id)) == cursor_id
                            )
                        except (ValueError, TypeError):
                            require(
                                False,
                                "INVALID_CURSOR",
                                "Refresh the current clinical worklist",
                                422,
                            )
                        query = query.where(
                            or_(
                                fi.index.c.due_at > cursor_due,
                                (fi.index.c.due_at == cursor_due) & (t.records.c.id > cursor_id),
                            )
                        )
                if kind == "task":
                    query = query.where(
                        or_(
                            fi.index.c.accountable_id == actor["id"],
                            fi.index.c.recipient_id == actor["id"],
                        )
                    )
                if not governing:
                    grants = (
                        (
                            await session.execute(
                                select(t.privileges).where(
                                    t.privileges.c.facility_id == facility,
                                    t.privileges.c.account_id == actor["id"],
                                    t.privileges.c.revoked.is_(False),
                                    t.privileges.c.valid_from <= db.now(),
                                    t.privileges.c.valid_until > db.now(),
                                )
                            )
                        )
                        .mappings()
                        .all()
                    )
                    services = {
                        service
                        for privilege in grants
                        if set(privilege["capabilities"]) & set(KIND_CAPABILITIES[kind])
                        for service in privilege["services"]
                    }
                    if kind not in {
                        "product",
                        "stock_adjustment",
                        "tariff",
                        "invoice",
                        "cash_receipt",
                    }:
                        query = query.where(t.records.c.service.in_(services))
                    if kind not in {
                        "product",
                        "stock_adjustment",
                        "tariff",
                        "invoice",
                        "cash_receipt",
                    }:
                        relationship = exists(
                            select(t.memberships.c.id).where(
                                t.memberships.c.facility_id == facility,
                                t.memberships.c.patient_id == t.records.c.patient_id,
                                t.memberships.c.account_id == actor["id"],
                                t.memberships.c.active.is_(True),
                                t.memberships.c.valid_until > db.now(),
                            )
                        )
                        predicates, preferred_services = [], set()
                        for capability in KIND_CAPABILITIES[kind]:
                            eligible_services = {
                                service
                                for grant in grants
                                if capability in grant["capabilities"]
                                for service in grant["services"]
                            }
                            selected_services = eligible_services - preferred_services
                            preferred_services |= eligible_services
                            if not selected_services:
                                continue
                            permitted = t.records.c.service.in_(selected_services)
                            if capability not in {
                                "DIAGNOSTICS",
                                "PHARMACY",
                                "RECORDS",
                                "REGISTER",
                                "FINANCE",
                                "CASHIER",
                            }:
                                permitted &= or_(
                                    t.records.c.patient_id.is_(None),
                                    relationship,
                                    fi.index.c.recipient_id == actor["id"],
                                    (t.records.c.kind == "encounter")
                                    & fi.index.c.accountable_id.is_(None),
                                )
                            elif capability == "REGISTER" and kind == "encounter":
                                permitted &= fi.index.c.accountable_id.is_(None) & (
                                    t.records.c.status == "ARRIVED"
                                )
                            predicates.append(permitted)
                        query = query.where(or_(*predicates) if predicates else False)
                if kind in ADVANCED_KINDS:
                    query = query.limit(26)
            candidates = list((await session.execute(query)).mappings())
            limit = 25
            visible = []
            for row in candidates[:limit]:
                try:
                    await readable(session, cfg, actor, row, box)
                except RuleError as exc:
                    if exc.status not in {403, 404}:
                        raise
                    continue
                opened = listed(await presented(session, row))
                if kind in ADVANCED_KINDS:
                    opened["data"] = {
                        key: value
                        for key, value in opened["data"].items()
                        if key
                        in {
                            "title",
                            "owner_id",
                            "account_id",
                            "recipient_id",
                            "source_id",
                            "capability",
                            "starts_at",
                            "ends_at",
                            "due_at",
                            "expires_at",
                            "service",
                        }
                    }
                    opened["detail_required"] = True
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
                "next_cursor": (
                    "due."
                    + base64.urlsafe_b64encode(
                        json.dumps(
                            [
                                s.opened(box, candidates[limit - 1])["data"]["due_at"],
                                candidates[limit - 1]["id"],
                            ]
                        ).encode()
                    )
                    .decode()
                    .rstrip("=")
                )
                if len(candidates) > limit
                and version >= 7
                and kind == "task"
                and (not after or after.startswith("due."))
                else candidates[limit - 1]["id"]
                if len(candidates) > limit
                else None,
                "ordering": "ACTUAL_DUE_TIME"
                if version >= 7 and kind == "task"
                else "STABLE_SOURCE_IDENTIFIER",
            }

    @router.get(PREFIX + "/beds")
    async def beds(facility_id: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, str(facility_id))
            await any_privilege(session, actor, str(facility_id), ("REGISTER", "CARE", "NURSING"))
            rows = list(
                (
                    await session.execute(
                        select(t.beds)
                        .where(t.beds.c.facility_id == str(facility_id), t.beds.c.id > after)
                        .order_by(t.beds.c.id)
                        .limit(501)
                    )
                ).mappings()
            )
            reservations = {}
            if (await session.scalar(select(func.max(db.schema_versions.c.version))) or 0) >= 7:
                require(
                    await fi.ready(session),
                    "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
                    "Reconcile current reservations before confirming resource availability",
                    503,
                )
                reservations = dict(
                    (
                        await session.execute(
                            select(fi.index.c.source_id, func.max(fi.index.c.ends_at))
                            .where(
                                fi.index.c.facility_id == str(facility_id),
                                fi.index.c.kind == "bed_hold",
                                fi.index.c.status == "HELD",
                                fi.index.c.ends_at > db.now(),
                                fi.index.c.source_id.in_([row["id"] for row in rows[:500]]),
                            )
                            .group_by(fi.index.c.source_id)
                        )
                    ).all()
                )
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "inpatient.bed_board_read",
                request.state.correlation_id,
            )
            return {
                "items": [
                    {
                        **dict(row),
                        "reservation_status": "HELD" if row["id"] in reservations else "NOT_HELD",
                        "reserved_until": reservations.get(row["id"]),
                    }
                    for row in rows[:500]
                ],
                "next_cursor": rows[499]["id"] if len(rows) > 500 else None,
                "as_of": db.now(),
            }

    @router.get(PREFIX + "/stock")
    async def stock(facility_id: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await s.site_for(session, cfg, str(facility_id))
            await any_privilege(
                session, actor, str(facility_id), ("PHARMACY", "PRESCRIBE", "NURSING")
            )
            rows = list(
                (
                    await session.execute(
                        select(t.lots)
                        .where(t.lots.c.facility_id == str(facility_id), t.lots.c.id > after)
                        .order_by(t.lots.c.id)
                        .limit(501)
                    )
                ).mappings()
            )
            reserved = {}
            if (await session.scalar(select(func.max(db.schema_versions.c.version))) or 0) >= 7:
                require(
                    await fi.ready(session),
                    "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
                    "Reconcile current reservations before confirming resource availability",
                    503,
                )
                reserved = dict(
                    (
                        await session.execute(
                            select(fi.index.c.source_id, func.sum(fi.index.c.quantity))
                            .where(
                                fi.index.c.facility_id == str(facility_id),
                                fi.index.c.kind == "stock_hold",
                                fi.index.c.status == "HELD",
                                fi.index.c.ends_at > db.now(),
                                fi.index.c.source_id.in_([row["id"] for row in rows[:500]]),
                            )
                            .group_by(fi.index.c.source_id)
                        )
                    ).all()
                )
            await s.audit(
                session,
                actor,
                str(facility_id),
                None,
                "medicines.stock_board_read",
                request.state.correlation_id,
            )
            return {
                "items": [
                    {
                        **dict(row),
                        "quantity": str(row["quantity"]),
                        "reserved_quantity": str(reserved.get(row["id"], 0)),
                        "unreserved_quantity": str(row["quantity"] - reserved.get(row["id"], 0)),
                        "supply_eligibility": "AVAILABLE"
                        if row["status"] == "AVAILABLE" and row["expires_at"] > db.now()
                        else "RESTRICTED",
                    }
                    for row in rows[:500]
                ],
                "next_cursor": rows[499]["id"] if len(rows) > 500 else None,
                "as_of": db.now(),
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

    for path, model, method in [
        ("capacity", ac.Capacity, "capacity"),
        ("shifts", ac.Shift, "shift"),
        ("handovers", ac.Handover, "team_handover"),
        ("admission-orders", ac.AdmissionOrder, "admission_order"),
        ("bed-holds", ac.BedHold, "bed_hold"),
        ("nursing-assessments", ac.Nursing, "nursing"),
        ("fluids", ac.Fluid, "fluid"),
        ("labour", ac.Labour, "labour"),
        ("births", ac.Birth, "birth"),
        ("growth", ac.Growth, "growth"),
        ("immunisations", ac.Immunisation, "immunisation"),
        ("reconciliations", ac.Reconciliation, "reconciliation"),
        ("stock-holds", ac.StockHold, "stock_hold"),
        ("stock-adjustments", ac.Adjustment, "stock_adjustment"),
        ("stock-returns", ac.StockReturn, "stock_return"),
        ("substitutions", ac.Substitution, "substitution"),
        ("anaesthesia", ac.Anaesthesia, "anaesthesia"),
        ("devices", ac.Device, "device"),
        ("recalls", ac.Recall, "recall"),
        ("instructions", ac.Instructions, "instructions"),
        ("infusions", ac.Infusion, "infusion"),
    ]:
        create_route("workflows/" + path, model, method)

    for path, model, method in [
        ("shifts/{id}/actions", ac.Action, "shift_action"),
        ("capacity/{id}/revisions", ac.CapacityRevision, "capacity_revision"),
        ("handovers/{id}/actions", ac.Action, "handover_action"),
        ("stays/{id}/events", ac.WardEvent, "ward_event"),
        ("commitments/{id}/cancel", ac.Action, "cancel_hold"),
        ("stock-movements/{id}/witness", ac.Action, "witness_stock"),
        ("substitutions/{id}/decision", ac.SubstituteDecision, "substitution_decision"),
        ("infusions/{id}/witness", ac.Action, "infusion_witness"),
    ]:
        action_route("workflows/" + path, model, method)

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
