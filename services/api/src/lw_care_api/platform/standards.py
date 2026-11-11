"""Initial affiliation evidence guards. Retained evidence is never rewritten.

These guards implement the currently adopted criterion flags; they add no
institutional criteria, approval thresholds, scanner bypass or expiry extension.
"""

from sqlalchemy import select

from . import db
from .domain import current_criteria, require

SCREENING_CONTRACT = "LWH-EXT-APPLICATION-002"


async def active_criteria(session, application, facility):
    row = (
        (
            await session.execute(
                select(db.criteria).where(db.criteria.c.id == application["criteria_id"])
            )
        )
        .mappings()
        .one()
    )
    require(
        current_criteria(row)
        and row["jurisdiction"] == facility["jurisdiction"]
        and row["site_type"] == facility["site_type"],
        "POLICY_NOT_ACTIVE",
        "Current adopted criteria must still match this facility",
        409,
    )
    return row


async def assessed_evidence(session, application, criteria, assessments):
    codes = [item["criterion"] for item in assessments]
    require(
        len(codes) == len(set(codes))
        and required_codes(criteria) <= set(codes)
        and set(codes) <= {item["code"] for item in criteria["requirements"]},
        "INCOMPLETE_EVIDENCE_REVIEW",
        "Assess each required criterion once using the retained criteria",
        409,
    )
    proofs, at = await evidence(session, application), db.now()
    for item in assessments:
        ids = item["evidence_ids"]
        require(
            ids
            and len(ids) == len(set(ids))
            and all(
                identifier in proofs
                and proofs[identifier]["criterion"] == item["criterion"]
                and current(proofs[identifier], at)
                for identifier in ids
            ),
            "EVIDENCE_NOT_CURRENT",
            "Assess actual current scanned evidence for this case and criterion",
            409,
        )


async def inspection_review(session, application, version=None):
    """Follow exact consecutive revisions, never timestamp ordering or an older cycle."""
    version = application["version"] if version is None else version
    snapshot = await revision(session, application, version)
    review = snapshot.get("evidence_review", {})
    require(
        snapshot.get("state") == "INSPECTION"
        and review.get("contract") == SCREENING_CONTRACT
        and review.get("reviewed_by") == application["reviewer_id"]
        and review.get("screening_version") == version - 1
        and snapshot.get("inspector_id") == application["inspector_id"],
        "EVIDENCE_REVIEW_REQUIRED",
        "A current-cycle pre-inspection evidence review is required; return legacy dossiers for correction",
        409,
    )
    screened = await revision(session, application, version - 1)
    screening = screened.get("screening", {})
    require(
        screened.get("state") == "EVIDENCE_REVIEW"
        and screening.get("contract") == SCREENING_CONTRACT
        and screening.get("screened_by") == application["reviewer_id"]
        and screening.get("assignment_version") == version - 2,
        "SCREENING_REQUIRED",
        "The actual screening must precede evidence review in this cycle",
        409,
    )
    assigned = await revision(session, application, version - 2)
    require(
        assigned.get("state") == "SCREENING"
        and assigned.get("reviewer_id") == application["reviewer_id"]
        and assigned.get("inspector_id") == application["inspector_id"],
        "SCREENING_REQUIRED",
        "The current independent assignment must precede screening",
        409,
    )
    return review


async def current_inspection(session, application):
    version = application["version"] - (application["state"] == "RECOMMENDED")
    attestation = await revision(session, application, version)
    require(
        attestation.get("state") == "INSPECTION"
        and attestation.get("inspection_id")
        and attestation.get("extension_contract") == SCREENING_CONTRACT
        and attestation.get("evidence_review_version") == version - 1,
        "CURRENT_INSPECTION_REQUIRED",
        "A fresh screened and version-bound inspection is required for this cycle",
        409,
    )
    review = await inspection_review(session, application, version - 1)
    row = (
        (
            await session.execute(
                select(db.inspections).where(
                    db.inspections.c.application_id == application["id"],
                    db.inspections.c.id == attestation["inspection_id"],
                )
            )
        )
        .mappings()
        .first()
    )
    require(
        row and not row["conflict_declared"] and row["inspector_id"] == application["inspector_id"],
        "INCOMPLETE_FINDINGS",
        "An attributed independent inspection is required",
        409,
    )
    return row, review


async def evidence(session, application):
    return {
        row["id"]: row
        for row in (
            await session.execute(
                select(db.evidence).where(db.evidence.c.application_id == application["id"])
            )
        ).mappings()
    }


def current(proof, at):
    return proof["scan_status"] == "CLEAN" and proof["expires_at"] > at


def required_codes(criteria):
    return {r["code"] for r in criteria["requirements"] if r["required"]}


async def submission_evidence(session, application, criteria):
    proofs, at = await evidence(session, application), db.now()
    require(
        required_codes(criteria) <= {r["criterion"] for r in proofs.values() if current(r, at)},
        "VALIDATION_FAILED",
        "Current scanned evidence is required for every required criterion",
        422,
    )


async def inspection_findings(session, application, criteria, findings):
    codes = [f["criterion"] for f in findings]
    known = {r["code"] for r in criteria["requirements"]}
    require(set(codes) <= known, "VALIDATION_FAILED", "Unknown criterion", 422)
    require(
        len(codes) == len(set(codes)) and required_codes(criteria) <= set(codes),
        "INCOMPLETE_FINDINGS",
        "Record every required criterion once, including not observed findings",
        409,
    )
    proofs, at = await evidence(session, application), db.now()
    for finding in findings:
        references = finding["evidence_ids"]
        require(
            all(
                identifier in proofs and proofs[identifier]["criterion"] == finding["criterion"]
                for identifier in references
            ),
            "VALIDATION_FAILED",
            "Each evidence reference must belong to this application and the finding's actual criterion",
            422,
        )
        if finding["outcome"] == "MET":
            require(
                references and all(current(proofs[identifier], at) for identifier in references),
                "EVIDENCE_NOT_CURRENT",
                "A met finding requires current scanned evidence for its actual criterion",
                409,
            )


async def positive_disposition(session, application, criteria, disposition):
    if disposition not in {"APPROVE", "CONDITIONAL"}:
        return
    row, review = await current_inspection(session, application)
    await assessed_evidence(session, application, criteria, review["assessments"])
    findings = row["findings"]
    await inspection_findings(session, application, criteria, findings)
    proofs, at = await evidence(session, application), db.now()
    require(
        required_codes(criteria) <= {r["criterion"] for r in proofs.values() if current(r, at)},
        "EVIDENCE_NOT_CURRENT",
        "Required evidence must remain current and scanned at this decision",
        409,
    )
    if disposition == "APPROVE":
        require(
            all(
                f["outcome"] == "MET"
                for f in findings
                if f["criterion"] in required_codes(criteria)
            ),
            "UNRESOLVED_FINDINGS",
            "Required unmet or unobserved findings prevent unrestricted recognition",
            409,
        )


async def revision(session, application, version=None):
    value = await session.scalar(
        select(db.revisions.c.payload).where(
            db.revisions.c.resource_type == "Application",
            db.revisions.c.resource_id == application["id"],
            db.revisions.c.version == (application["version"] if version is None else version),
        )
    )
    require(
        value,
        "APPLICATION_HISTORY_REQUIRED",
        "The authoritative application revision is unavailable",
        409,
    )
    return value


async def participants(session, application, facility):
    applicants = {application["created_by"], facility["created_by"]}
    inspectors, reviewers = set(), set()
    for payload in (
        await session.execute(
            select(db.revisions.c.payload).where(
                db.revisions.c.resource_type == "Application",
                db.revisions.c.resource_id == application["id"],
            )
        )
    ).scalars():
        inspectors.add(payload.get("inspector_id"))
        reviewers.add(payload.get("reviewer_id"))
        reviewers.add(payload.get("correction_request", {}).get("requested_by"))
        applicants.add(payload.get("correction_response", {}).get("submitted_by"))
    applicants.update(
        (
            await session.execute(
                select(db.evidence.c.uploaded_by).where(
                    db.evidence.c.application_id == application["id"]
                )
            )
        ).scalars()
    )
    inspectors.update(
        (
            await session.execute(
                select(db.inspections.c.inspector_id).where(
                    db.inspections.c.application_id == application["id"]
                )
            )
        ).scalars()
    )
    return applicants - {None}, inspectors - {None}, reviewers - {None}


async def independent_assignment(session, application, facility, inspector, reviewer):
    applicants, inspectors, reviewers = await participants(session, application, facility)
    require(
        inspector != reviewer
        and inspector not in applicants | reviewers
        and reviewer not in applicants | inspectors,
        "ACCESS_DENIED",
        "Applicants and historical inspectors/reviewers cannot change sides in this case",
    )


async def independent_decider(session, application, facility, actor_id):
    applicants, inspectors, reviewers = await participants(session, application, facility)
    require(
        actor_id not in applicants | inspectors | reviewers,
        "ACCESS_DENIED",
        "The final Directorate decider must be independent of every review cycle",
    )
