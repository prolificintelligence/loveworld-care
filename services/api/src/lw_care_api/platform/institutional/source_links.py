"""Reviewed initial-criterion lineage, without manufacturing findings or resolution."""

from uuid import UUID

from fastapi import Request
from pydantic import Field
from sqlalchemy import select

from .. import db, standards
from ..domain import application_for, expected, require
from . import tables as t
from .base import Service
from .contracts import Versioned

CONTRACT = "LWH-EXT-INITIAL-FINDING-LINK-001"
LINKED = "standards.initial_finding_linked"
RETRACTED = "standards.initial_finding_link_retracted"
LIMIT = 20


class InitialSourceLink(Versioned):
    expected_case_version: int = Field(ge=1)
    application_id: UUID
    expected_application_version: int = Field(ge=1)
    inspection_id: UUID
    attestation_version: int = Field(ge=1)


class SourceLinkRetraction(Versioned):
    expected_case_version: int = Field(ge=1)


class SourceLinks(Service):
    async def context(self, identifier, *, write=False, lock=False):
        finding = await self.row(t.findings, identifier, lock=lock)
        case, facility = await self.case(finding["case_id"], write=lock)
        if write:
            require(self.actor["id"] == case["reviewer_id"])
            await self.person(self.actor["id"], {"STANDARDS_REVIEWER"}, facility)
            require(
                self.actor["id"]
                not in {finding["owner_id"], finding["inspector_id"], case["respondent_id"]}
            )
        return finding, case, facility

    async def source(self, finding, case, application, inspection_id, version):
        require(
            version <= application["version"],
            "SOURCE_ATTESTATION_REQUIRED",
            "An attestation cannot be ahead of its application history",
            409,
        )
        snapshot = await standards.revision(self.session, application, version)
        require(
            snapshot.get("id") == application["id"] and snapshot.get("version") == version,
            "SOURCE_ATTESTATION_REQUIRED",
            "The original resource and attestation version must match",
            409,
        )
        require(
            snapshot.get("facility_id") == case["facility_id"]
            and snapshot.get("criteria_id") == case["criteria_id"],
            "SOURCE_SCOPE_MISMATCH",
            "The actual facility and retained criterion version must match",
            409,
        )
        require(
            snapshot.get("state") == "INSPECTION"
            and snapshot.get("inspection_id") == str(inspection_id),
            "SOURCE_ATTESTATION_REQUIRED",
            "Select the actual immutable inspection attestation",
            409,
        )
        inspection, _ = await standards.current_inspection(self.session, snapshot)
        observations = [
            item for item in inspection["findings"] if item["criterion"] == finding["criterion"]
        ]
        require(
            len(observations) == 1 and observations[0]["outcome"] in {"NOT_MET", "NOT_OBSERVED"},
            "SOURCE_CORRECTION_REQUIRED",
            "Select one actual unmet or unobserved source criterion",
            409,
        )
        return {
            "application_id": application["id"],
            "application_version_at_confirmation": application["version"],
            "application_state_at_confirmation": application["state"],
            "attestation_version": version,
            "inspection_id": inspection["id"],
            "inspector_id": inspection["inspector_id"],
            "initial_applicant_id": snapshot["created_by"],
            "initial_reviewer_id": snapshot["reviewer_id"],
            "criteria_id": snapshot["criteria_id"],
            "criterion": finding["criterion"],
            "observation": observations[0],
            "observed_at": inspection["observed_at"],
            "recorded_at": inspection["recorded_at"],
        }

    async def links(self, finding):
        rows = (
            (
                await self.session.execute(
                    select(t.journal)
                    .where(t.journal.c.resource_id == finding["id"], t.journal.c.action == LINKED)
                    .order_by(t.journal.c.recorded_at.desc(), t.journal.c.id.desc())
                    .limit(LIMIT + 1)
                )
            )
            .mappings()
            .all()
        )
        require(
            len(rows) <= LIMIT,
            "LINK_HISTORY_LIMIT",
            "Review the retained source history before adding links",
            409,
        )
        values = [self.open(row["payload_ciphertext"]) for row in rows]
        if values:
            events = (
                (
                    await self.session.execute(
                        select(t.journal).where(
                            t.journal.c.resource_id.in_([value["id"] for value in values]),
                            t.journal.c.action == RETRACTED,
                        )
                    )
                )
                .mappings()
                .all()
            )
            by_id = {row["resource_id"]: self.open(row["payload_ciphertext"]) for row in events}
            values = [
                {
                    **value,
                    "status": "RETRACTED" if value["id"] in by_id else "RECORDED",
                    "retraction": by_id.get(value["id"]),
                }
                for value in values
            ]
        return values

    async def emit_link(self, action, resource_id, finding, facility, value):
        await self.session.execute(
            t.journal.insert().values(
                id=value["id"],
                resource_id=resource_id,
                facility_id=facility["id"],
                action=action,
                actor_id=self.actor["id"],
                version=finding["version"],
                recorded_at=value["recorded_at"],
                correlation_id=self.correlation,
                payload_ciphertext=self.seal(value),
            )
        )
        await self.audit(action, value["id"])

    async def confirm(self, identifier, body):
        # Match initial workflow lock order (application then facility). Other
        # institutional writers already share command's transaction serialization.
        application, _ = await application_for(
            self.session, self.actor, body["application_id"], lock=True
        )
        finding, case, facility = await self.context(identifier, write=True, lock=True)
        expected(application, body["expected_application_version"])
        expected(finding, body["expected_version"])
        expected(case, body["expected_case_version"])
        require(
            application["facility_id"] == facility["id"],
            "SOURCE_SCOPE_MISMATCH",
            "Source belongs to another facility",
            409,
        )
        require(
            application["state"] != "WITHDRAWN",
            "SOURCE_WITHDRAWN",
            "A withdrawn source cannot acquire a new correction link",
            409,
        )
        require(
            case["state"] == "INSPECTED"
            and finding["outcome"] != "MET"
            and finding["state"] in {"AWAITING_RESPONSE", "RETURNED"},
            "INVALID_STATE",
            "Confirm source context before pending corrective work is submitted",
            409,
        )
        source = await self.source(
            finding, case, application, body["inspection_id"], body["attestation_version"]
        )
        require(
            self.actor["id"] not in {source["inspector_id"], source["initial_applicant_id"]},
            "INDEPENDENT_REVIEW_REQUIRED",
            "The confirming reviewer must be independent of the original inspection/applicant",
            409,
        )
        existing = await self.links(finding)
        require(
            not any(
                value["source"]["inspection_id"] == source["inspection_id"] for value in existing
            ),
            "SOURCE_ALREADY_LINKED",
            "The exact source is already retained; review its current annotation",
            409,
        )
        require(
            len(existing) < LIMIT, "LINK_HISTORY_LIMIT", "This bounded source history is full", 409
        )
        value = {
            "id": db.uid(),
            "contract": CONTRACT,
            "status": "RECORDED",
            "effect": "CONTEXT_ONLY_NO_WORKFLOW_TRANSITION",
            "finding_id": finding["id"],
            "finding_version": finding["version"],
            "case_id": case["id"],
            "case_version": case["version"],
            "source": source,
            "confirmed_by": self.actor["id"],
            "recorded_at": db.now(),
            "reason": body["evidence"],
        }
        await self.emit_link(LINKED, finding["id"], finding, facility, value)
        return value

    async def retract(self, identifier, link_id, body):
        finding, case, facility = await self.context(identifier, write=True, lock=True)
        expected(finding, body["expected_version"])
        expected(case, body["expected_case_version"])
        link = next(
            (value for value in await self.links(finding) if value["id"] == str(link_id)), None
        )
        require(link, "NOT_FOUND_OR_NOT_PERMITTED", "Source link unavailable", 404)
        await application_for(self.session, self.actor, link["source"]["application_id"])
        require(
            link["status"] == "RECORDED",
            "INVALID_STATE",
            "The original retraction is already retained",
            409,
        )
        value = {
            "id": db.uid(),
            "link_id": link["id"],
            "finding_id": finding["id"],
            "finding_version": finding["version"],
            "case_version": case["version"],
            "contract": CONTRACT,
            "status": "RETRACTED",
            "effect": "CONTEXT_ONLY_NO_WORKFLOW_TRANSITION",
            "retracted_by": self.actor["id"],
            "recorded_at": db.now(),
            "reason": body["evidence"],
        }
        await self.emit_link(RETRACTED, link["id"], finding, facility, value)
        return value


def install_source_link_routes(router, cfg, database, box, actor_for, available, command):
    async def guard(service, identifier, body, link_id=None):
        finding, case, _ = await service.context(identifier, write=True)
        if link_id:
            link = next(
                (value for value in await service.links(finding) if value["id"] == str(link_id)),
                None,
            )
            require(link, "NOT_FOUND_OR_NOT_PERMITTED", "Source link unavailable", 404)
            application_id = link["source"]["application_id"]
        else:
            application_id = body["application_id"]
        application, _ = await application_for(service.session, service.actor, application_id)
        require(
            application["facility_id"] == case["facility_id"],
            "SOURCE_SCOPE_MISMATCH",
            "Source belongs to another facility",
            409,
        )

    @router.post("/v1/institutional/findings/{identifier}/initial-source-links")
    async def confirm(identifier: UUID, payload: InitialSourceLink, request: Request):
        return await command(
            request,
            payload,
            SourceLinks,
            lambda service, body: guard(service, identifier, body),
            lambda service, body: service.confirm(identifier, body),
        )

    @router.post("/v1/institutional/findings/{identifier}/initial-source-links/{link_id}/retract")
    async def retract(
        identifier: UUID, link_id: UUID, payload: SourceLinkRetraction, request: Request
    ):
        return await command(
            request,
            payload,
            SourceLinks,
            lambda service, body: guard(service, identifier, body, link_id),
            lambda service, body: service.retract(identifier, link_id, body),
        )

    @router.get("/v1/institutional/findings/{identifier}/initial-source-links")
    async def listing(identifier: UUID, request: Request, before_version: int = 0):
        await available()
        require(
            before_version >= 0, "VALIDATION_FAILED", "Use an actual source version cursor", 422
        )
        async with database.transaction() as session:
            service = SourceLinks(
                session, cfg, box, await actor_for(session, request), request.state.correlation_id
            )
            finding, case, facility = await service.context(identifier)
            application_id = await session.scalar(
                select(db.applications.c.id).where(db.applications.c.facility_id == facility["id"])
            )
            require(application_id, "NOT_FOUND_OR_NOT_PERMITTED", "Initial source unavailable", 404)
            application, _ = await application_for(session, service.actor, application_id)
            query = select(db.revisions).where(
                db.revisions.c.resource_type == "Application",
                db.revisions.c.resource_id == application_id,
                db.revisions.c.payload["inspection_id"].as_string().is_not(None),
                db.revisions.c.version < before_version if before_version else True,
            )
            rows = (
                (await session.execute(query.order_by(db.revisions.c.version.desc()).limit(11)))
                .mappings()
                .all()
            )
            candidates = []
            from ..domain import RuleError

            for row in rows[:10]:
                try:
                    source = await service.source(
                        finding, case, application, row["payload"]["inspection_id"], row["version"]
                    )
                    candidates.append({"eligible": application["state"] != "WITHDRAWN", **source})
                except RuleError as exc:
                    candidates.append(
                        {
                            "eligible": False,
                            "attestation_version": row["version"],
                            "reason_code": exc.code,
                        }
                    )
            await service.audit("standards.initial_source_links_read", finding["id"])
            return {
                "items": await service.links(finding),
                "candidates": candidates,
                "next_before_version": rows[9]["version"] if len(rows) > 10 else None,
                "application_id": application_id,
                "application_state": application["state"],
                "application_version": application["version"],
                "finding_version": finding["version"],
                "case_version": case["version"],
            }
