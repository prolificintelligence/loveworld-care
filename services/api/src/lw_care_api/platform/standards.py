"""Initial affiliation evidence guards. Retained evidence is never rewritten.

These guards implement the currently adopted criterion flags; they add no
institutional criteria, approval thresholds, scanner bypass or expiry extension.
"""

from sqlalchemy import select

from . import db
from .domain import require


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
    source_version = application["version"] - (application["state"] == "RECOMMENDED")
    attestation = await revision(session, application, source_version)
    require(
        attestation.get("state") == "EVIDENCE_REVIEW" and attestation.get("inspection_id"),
        "CURRENT_INSPECTION_REQUIRED",
        "A fresh version-bound inspection is required for this review cycle",
        409,
    )
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
