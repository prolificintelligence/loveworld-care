"""Reasoned initial-application correction and withdrawal, retaining every review cycle.

LWH-EXT-APPLICATION-001 uses existing immutable application revision snapshots.
Submission of a correction is not acceptance, recognition or a file scan.
"""

from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from . import contracts as c
from . import db, standards
from .domain import (
    amend,
    application_for,
    current_criteria,
    expected,
    record_change,
    require,
    scoped,
)

EDITABLE = {"DRAFT", "CORRECTION_REQUIRED"}
WITHDRAWABLE = EDITABLE | {"SUBMITTED", "INSPECTION", "EVIDENCE_REVIEW", "RECOMMENDED"}


def install(app, database, command, receipt):
    router = APIRouter(prefix="/v1/applications")

    @router.post("/{application_id}/correction-request")
    async def request_correction(
        application_id: UUID, payload: c.ApplicationCorrection, request: Request
    ):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(
                actor["id"] == row["reviewer_id"]
                and scoped(actor, {"STANDARDS_REVIEWER"}, facility)
            )
            expected(row, payload.expected_version)
            require(
                row["state"] in {"EVIDENCE_REVIEW", "RECOMMENDED"},
                "INVALID_TRANSITION",
                "An inspected application is required before requesting correction",
                409,
            )
            criteria = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            codes = payload.criterion_codes
            require(
                len(codes) == len(set(codes))
                and set(codes) <= {r["code"] for r in criteria["requirements"]},
                "VALIDATION_FAILED",
                "Identify each requested criterion once using the retained criteria",
                422,
            )
            row = await amend(
                session,
                db.applications,
                row,
                {
                    "state": "CORRECTION_REQUIRED",
                    "recommendation": None,
                    "inspector_id": None,
                    "reviewer_id": None,
                },
            )
            snapshot = row | {
                "correction_request": {
                    "contract": "LWH-EXT-APPLICATION-001",
                    "criterion_codes": codes,
                    "reason": payload.reason,
                    "requested_by": actor["id"],
                }
            }
            await record_change(
                session,
                actor,
                "Application",
                snapshot,
                "application.correction_requested",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(
            request, payload.model_dump(mode="json"), "application.correction_requested", apply
        )

    @router.post("/{application_id}/resubmit")
    async def resubmit(application_id: UUID, payload: c.ApplicationResubmit, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
            expected(row, payload.expected_version)
            require(
                row["state"] == "CORRECTION_REQUIRED",
                "INVALID_TRANSITION",
                "Only an application returned for correction can be resubmitted",
                409,
            )
            snapshot = await standards.revision(session, row)
            correction = snapshot.get("correction_request")
            require(
                correction,
                "APPLICATION_HISTORY_REQUIRED",
                "The actual correction request must be retained",
                409,
            )
            responses = [r.model_dump(mode="json") for r in payload.responses]
            codes = [r["criterion"] for r in responses]
            require(
                len(codes) == len(set(codes)) and set(codes) == set(correction["criterion_codes"]),
                "INCOMPLETE_CORRECTION_RESPONSE",
                "Respond once to every requested criterion",
                409,
            )
            proofs, at = await standards.evidence(session, row), db.now()
            for response in responses:
                require(
                    all(
                        identifier in proofs
                        and proofs[identifier]["criterion"] == response["criterion"]
                        and standards.current(proofs[identifier], at)
                        for identifier in response["evidence_ids"]
                    ),
                    "EVIDENCE_NOT_CURRENT",
                    "Response references must be current scanned evidence for this case and criterion",
                    409,
                )
            criteria = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            require(
                current_criteria(criteria),
                "POLICY_NOT_ACTIVE",
                "The retained adopted criteria are no longer current",
                409,
            )
            await standards.submission_evidence(session, row, criteria)
            request_version = row["version"]
            row = await amend(
                session,
                db.applications,
                row,
                {
                    "state": "SUBMITTED",
                    "recommendation": None,
                    "inspector_id": None,
                    "reviewer_id": None,
                },
            )
            snapshot = row | {
                "correction_response": {
                    "contract": "LWH-EXT-APPLICATION-001",
                    "request_version": request_version,
                    "responses": responses,
                    "reason": payload.reason,
                    "submitted_by": actor["id"],
                }
            }
            await record_change(
                session,
                actor,
                "Application",
                snapshot,
                "application.resubmitted",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(
            request, payload.model_dump(mode="json"), "application.resubmitted", apply
        )

    @router.post("/{application_id}/withdraw")
    async def withdraw(application_id: UUID, payload: c.ApplicationWithdraw, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
            expected(row, payload.expected_version)
            require(
                row["state"] in WITHDRAWABLE,
                "INVALID_TRANSITION",
                "A decided or withdrawn application cannot be withdrawn",
                409,
            )
            row = await amend(
                session, db.applications, row, {"state": "WITHDRAWN", "recommendation": None}
            )
            snapshot = row | {
                "withdrawal": {
                    "contract": "LWH-EXT-APPLICATION-001",
                    "reason": payload.reason,
                    "withdrawn_by": actor["id"],
                }
            }
            await record_change(
                session,
                actor,
                "Application",
                snapshot,
                "application.withdrawn",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(
            request, payload.model_dump(mode="json"), "application.withdrawn", apply
        )

    app.include_router(router)
