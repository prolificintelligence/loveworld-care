"""Version-bound native source contracts and protected clinical-source qualification."""

import base64
import json
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from sqlalchemy import select

from .. import db
from ..clinical import store as clinical_store
from ..clinical import tables as clinical
from ..domain import require
from . import store as s
from . import tables as t
from .proposals import catalogue as working_catalogue

EDITION = "LWH-NATIVE-2026.1"
SELECTORS = {
    "LWH-MET-010": "EMR_SERVICE_CONTACTS_V2",
    "LWH-MET-013": "EMR_INPATIENT_DEATHS_V1",
    "LWH-MET-014": "EMR_INPATIENT_MORTALITY_V1",
    "LWH-MET-025": "EMR_REFERRAL_ACCEPTANCE_V1",
}
KINDS = ("encounter", "stay", "referral", "note", "record_error")
MAX_RECORDS = 5000
MAX_EVENTS = 20000


def catalogue():
    measures = []
    for value in working_catalogue()["forms"][0]["measures"]:
        if value["metric_id"] not in SELECTORS:
            continue
        value = dict(value)
        value.pop("source_register")
        value["source_selector"] = SELECTORS[value["metric_id"]]
        value["population_definition"] = (
            "Native LW Care records for the exact facility and half-open occurrence period. "
            "The clinical policy must cover the period. External/manual records are not added. "
            "The officer must independently establish full-source coverage before declaring a complete return."
        )
        value["inclusion_exclusion"] += (
            " Native profile " + EDITION + ": verify signed event chains and current projections. "
            "Contacts require the same-patient/encounter signed disposition summary. "
            "Inpatient final outcomes use one signed DEATH, DISCHARGE or SELF_DISCHARGE per stay; "
            "ward transfer, leave, open stays and bed release are not final outcomes. "
            "Referral cohort uses REQUEST occurrence; actual named receiving acceptance must occur "
            "on or after request and before period end. Cancellation before acceptance is excluded "
            "and counted separately; cancellation after acceptance remains an accepted request. "
            "Entered-in-error records and invalidated summaries are excluded with counts. "
            "Missing required source fields or contradictory histories make the affected measure UNKNOWN. "
            "Usable native totals start PARTIAL until source coverage is reviewed."
        )
        measures.append(value)
    return {
        "edition": EDITION,
        "status": "PROPOSED_NATIVE_MAPPING_REQUIRES_REVIEW_AND_ADOPTION",
        "name": "Proposed native EMR contacts, inpatient outcomes and referral acceptance",
        "stream": "FACILITY_ACTIVITY",
        "measures": measures,
        "limits": {"records_per_facility": MAX_RECORDS, "events_per_facility": MAX_EVENTS},
        "freshness": "Changes to period-relevant records, their summaries/error markers or facility activation invalidate current use; unrelated later-period care does not. Historical evidence is preserved.",
        "limitations": "Native source only. No population incidence, certified cause of death, referral completion or full-facility coverage inferred. Manual definitions and the original working forms remain unchanged.",
    }


def validate_definition(body):
    if body["source_selector"] not in SELECTORS.values():
        return
    expected = next(
        (
            item
            for item in catalogue()["measures"]
            if item["source_selector"] == body["source_selector"]
        ),
        None,
    )
    # A source selector cannot silently be attached to a different clinical
    # definition. Names, authority, version and validity remain institution-owned.
    keys = set(expected) - {"name"}
    require(
        body["stream"] == "FACILITY_ACTIVITY"
        and all(str(body.get(key)) == str(expected[key]) for key in keys),
        "NATIVE_MAPPING_CONTRACT_MISMATCH",
        "Use the exact published native source definition; changed semantics require manual capture or a newly qualified mapping",
        422,
    )


async def prepare(service, body):
    from . import contracts as c
    from .templates import Template, TemplateService

    service.governor()
    pack = catalogue()
    require(
        body["valid_until"] > db.now(), "TEMPLATE_EXPIRED", "Use current or future validity", 422
    )
    fields = [
        {
            "code": key.lower(),
            "label": label,
            "required": True,
            "disposition": "CONTEXT",
            "context": key,
            "rationale": "Exact reporting unit/period and authenticated source attestation.",
        }
        for key, label in [
            ("FACILITY", "Facility"),
            ("PERIOD_START", "Period start"),
            ("PERIOD_END", "Period end"),
            ("OFFICER_ATTESTATION", "Officer attestation"),
        ]
    ]
    for measure in pack["measures"]:
        payload = measure | {
            "definition_version": "N26-" + db.uid(),
            "stream": "FACILITY_ACTIVITY",
            "adoption_reference": body["authority_reference"],
            "template_reconciliation": "Exact qualified native source proposal "
            + EDITION
            + "; requires independent template review and explicit adoption.",
            "valid_from": body["valid_from"],
            "valid_until": body["valid_until"],
            "intent_confirmed": True,
        }
        definition = await service.definition(
            c.Definition.model_validate(payload).model_dump(mode="json")
        )
        for part in ["NUMERATOR", "DENOMINATOR"] if measure["formula"] == "RATIO" else ["VALUE"]:
            fields.append(
                {
                    "code": measure["metric_id"].replace("-", "_") + "_" + part.lower(),
                    "label": measure["name"] + " / " + part.lower(),
                    "required": True,
                    "disposition": "MEASURE",
                    "definition_id": definition["id"],
                    "part": part,
                    "rationale": "Exact "
                    + measure["source_selector"]
                    + " component; no automatic institutional adoption.",
                }
            )
    payload = Template.model_validate(
        {
            "name": pack["name"],
            "source_version": EDITION,
            "source_reference": "Packaged native mapping proposal /v1/reporting/source-profiles; "
            + EDITION,
            "source_sha256": s.digest(pack),
            "stream": "FACILITY_ACTIVITY",
            "jurisdictions": ["GLOBAL"],
            "adoption_reference": body["authority_reference"],
            "valid_from": body["valid_from"],
            "valid_until": body["valid_until"],
            "fields": fields,
        }
    ).model_dump(mode="json")
    return await TemplateService(service).create(payload)


def contributing_inventory(service, records, obligation):
    start, end = instant(obligation["period_start"]), instant(obligation["period_end"])
    contents = {
        row["id"]: json.loads(service.box.decrypt(row["content_ciphertext"]))["content"]
        for row in records
    }
    selected = set()
    for row in records:
        data = contents[row["id"]]
        if row["kind"] == "encounter" and row["status"] == "COMPLETED":
            times = [instant(data.get("disposition", {}).get("occurred_at"))]
        elif row["kind"] == "stay":
            times = [
                instant(event.get("occurred_at"))
                for event in data.get("history", [])
                if event.get("action") in {"DEATH", "DISCHARGE", "SELF_DISCHARGE"}
            ]
            if not times and row["status"] in {"DECEASED", "DISCHARGED", "SELF_DISCHARGED"}:
                times = [None]
        elif row["kind"] == "referral":
            times = [
                instant(event.get("occurred_at"))
                for event in data.get("history", [])
                if event.get("action") == "REQUEST"
            ]
            if not times and row["status"] not in {"DRAFT", "CANCELLED"}:
                times = [None]
        else:
            continue
        if any(at is None or start <= at < end for at in times):
            selected.add(row["id"])
            if row["kind"] != "encounter" and row["encounter_id"]:
                selected.add(row["encounter_id"])
            selected.add(data.get("disposition", {}).get("signed_summary_id"))
            selected.add(data.get("summary_note_id"))
            selected.update(event.get("signed_summary_id") for event in data.get("history", []))
    selected.update(
        row["id"]
        for row in records
        if row["kind"] == "record_error" and contents[row["id"]].get("target_id") in selected
    )
    return [dict(row) for row in records if row["id"] in selected]


async def inventory(service, facility, obligation):
    records = list(
        (
            await service.session.execute(
                select(clinical.records)
                .where(
                    clinical.records.c.facility_id == facility, clinical.records.c.kind.in_(KINDS)
                )
                .order_by(clinical.records.c.id)
                .limit(MAX_RECORDS + 1)
            )
        ).mappings()
    )
    require(
        len(records) <= MAX_RECORDS,
        "SOURCE_BATCH_REQUIRED",
        "Source volume exceeds this qualified synchronous batch; no truncated aggregate is returned",
        409,
    )
    policy = (
        (
            await service.session.execute(
                select(clinical.sites).where(clinical.sites.c.facility_id == facility)
            )
        )
        .mappings()
        .first()
    )
    fingerprint = s.digest(
        {
            "records": contributing_inventory(service, records, obligation),
            "policy": dict(policy) if policy else None,
        }
    )
    return records, policy, fingerprint


async def fingerprint(service, obligation):
    if not hasattr(service, "_native_fingerprints"):
        service._native_fingerprints = {}
    if obligation["id"] not in service._native_fingerprints:
        service._native_fingerprints[obligation["id"]] = (
            await inventory(service, obligation["facility_id"], obligation)
        )[2]
    return service._native_fingerprints[obligation["id"]]


async def current(service, data, obligation):
    for identifier in {value.get("extract_id") for value in data["values"]} - {None}:
        row = await s.load(service.session, t.extracts, identifier)
        payload = service.data(row)
        if payload.get("rule_version") == EDITION and (
            row["obligation_id"] != obligation["id"]
            or row["source_hash"] != await fingerprint(service, obligation)
        ):
            return False
    return True


async def verified_sources(service, obligation):
    records, policy, state_hash = await inventory(service, obligation["facility_id"], obligation)
    indexed = {row["id"]: row for row in records}
    rows = list(
        (
            await service.session.execute(
                select(clinical.events)
                .join(clinical.records, clinical.records.c.id == clinical.events.c.record_id)
                .where(
                    clinical.records.c.facility_id == obligation["facility_id"],
                    clinical.records.c.kind.in_(KINDS),
                )
                .order_by(clinical.events.c.record_id, clinical.events.c.version)
                .limit(MAX_EVENTS + 1)
            )
        ).mappings()
    )
    require(
        len(rows) <= MAX_EVENTS,
        "SOURCE_BATCH_REQUIRED",
        "Event volume requires a separately qualified batch; no truncated aggregate is returned",
        409,
    )
    heads, contents = {}, {}
    public_key = clinical_store.signing_key(service.cfg).public_key()
    for row in rows:
        value = json.loads(service.box.decrypt(row["payload_ciphertext"]))
        prior = heads.get(row["record_id"])
        require(
            row["facility_id"] == obligation["facility_id"]
            and s.digest(value) == row["payload_hash"]
            and row["version"] == (prior["version"] + 1 if prior else 1)
            and row["previous_hash"] == (prior["payload_hash"] if prior else "0" * 64)
            and all(
                value.get(key) == item
                for key, item in row.items()
                if key not in {"payload_ciphertext", "payload_hash", "signature"}
            ),
            "SOURCE_INTEGRITY_FAILURE",
            "Clinical source history did not verify",
            503,
        )
        try:
            public_key.verify(
                base64.b64decode(row["signature"], validate=True),
                bytes.fromhex(row["payload_hash"]),
            )
        except (InvalidSignature, ValueError):
            require(
                False, "SOURCE_INTEGRITY_FAILURE", "Clinical source attestation did not verify", 503
            )
        heads[row["record_id"]] = row
        contents[row["record_id"]] = value
    for identifier, row in indexed.items():
        head = heads.get(identifier)
        content = json.loads(service.box.decrypt(row["content_ciphertext"]))
        require(
            head
            and head["version"] == row["version"]
            and content.get("id") == identifier
            and contents[identifier]["content"] == content["content"]
            and all(
                contents[identifier].get(key) == row[key]
                for key in (
                    "facility_id",
                    "patient_id",
                    "kind",
                    "status",
                    "authority_node_id",
                    "authority_epoch",
                )
            ),
            "SOURCE_INTEGRITY_FAILURE",
            "Clinical projection differs from signed source",
            503,
        )
    manifest = [
        {
            "record_id": identifier,
            "version": row["version"],
            "event_id": row["id"],
            "payload_hash": row["payload_hash"],
        }
        for identifier, row in sorted(heads.items())
    ]
    return (
        indexed,
        {key: value["content"] for key, value in contents.items()},
        policy,
        state_hash,
        manifest,
        len(rows),
    )


def instant(value):
    try:
        result = datetime.fromisoformat(value)
        return result.astimezone(UTC) if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def calculate(records, contents, policy, obligation):
    start, end = instant(obligation["period_start"]), instant(obligation["period_end"])
    excluded = {
        value.get("target_id")
        for identifier, value in contents.items()
        if records[identifier]["kind"] == "record_error"
    }
    counts = {
        "contacts": 0,
        "deaths": 0,
        "dispositions": 0,
        "referral_requests": 0,
        "accepted_referrals": 0,
        "excluded_entered_in_error": 0,
        "cancelled_before_acceptance": 0,
    }
    uncertain = {"contact": 0, "inpatient": 0, "referral": 0}

    def signed_summary(identifier, row):
        note = records.get(identifier)
        return bool(
            note
            and identifier not in excluded
            and note["kind"] == "note"
            and note["status"] == "SIGNED"
            and note["patient_id"] == row["patient_id"]
            and note["encounter_id"]
            == (row["id"] if row["kind"] == "encounter" else row["encounter_id"])
        )

    for identifier, row in records.items():
        if row["kind"] not in {"encounter", "stay", "referral"}:
            continue
        if identifier in excluded or row["encounter_id"] in excluded:
            counts["excluded_entered_in_error"] += 1
            continue
        data = contents[identifier]
        if row["kind"] == "encounter" and row["status"] == "COMPLETED":
            disposition = data.get("disposition", {})
            at = instant(disposition.get("occurred_at"))
            if at is None:
                uncertain["contact"] += 1
            elif start <= at < end:
                if signed_summary(disposition.get("signed_summary_id"), row):
                    counts["contacts"] += 1
                else:
                    uncertain["contact"] += 1
        elif row["kind"] == "stay":
            finals = [
                event
                for event in data.get("history", [])
                if event.get("action") in {"DEATH", "DISCHARGE", "SELF_DISCHARGE"}
            ]
            if not finals:
                if row["status"] in {"DECEASED", "DISCHARGED", "SELF_DISCHARGED"}:
                    uncertain["inpatient"] += 1
                continue
            at = instant(finals[0].get("occurred_at"))
            if len(finals) != 1 or at is None:
                uncertain["inpatient"] += 1
                continue
            if start <= at < end:
                if row["status"] == {
                    "DEATH": "DECEASED",
                    "DISCHARGE": "DISCHARGED",
                    "SELF_DISCHARGE": "SELF_DISCHARGED",
                }[finals[0]["action"]] and signed_summary(finals[0].get("signed_summary_id"), row):
                    counts["dispositions"] += 1
                    counts["deaths"] += int(finals[0]["action"] == "DEATH")
                else:
                    uncertain["inpatient"] += 1
        elif row["kind"] == "referral":
            history = data.get("history", [])
            requests = [event for event in history if event.get("action") == "REQUEST"]
            if not requests:
                if row["status"] not in {"DRAFT", "CANCELLED"}:
                    uncertain["referral"] += 1
                continue
            at = instant(requests[0].get("occurred_at"))
            if len(requests) != 1 or at is None:
                uncertain["referral"] += 1
                continue
            if not start <= at < end:
                continue
            if not signed_summary(data.get("summary_note_id"), row):
                uncertain["referral"] += 1
                continue
            relevant = [
                event
                for event in history
                if event.get("action") in {"REQUEST", "RECORD_ACCEPTANCE", "CANCEL"}
            ]
            times = [instant(event.get("occurred_at")) for event in relevant]
            if any(value is None for value in times) or times != sorted(times):
                uncertain["referral"] += 1
                continue
            accepted = next(
                (
                    event
                    for event in relevant
                    if event["action"] == "RECORD_ACCEPTANCE"
                    and instant(event["occurred_at"]) < end
                ),
                None,
            )
            cancelled = next(
                (
                    event
                    for event in relevant
                    if event["action"] == "CANCEL" and instant(event["occurred_at"]) < end
                ),
                None,
            )
            if cancelled and not accepted:
                counts["cancelled_before_acceptance"] += 1
                continue
            counts["referral_requests"] += 1
            if accepted:
                if accepted.get("receiver_name") and accepted.get("acceptance_evidence"):
                    counts["accepted_referrals"] += 1
                else:
                    uncertain["referral"] += 1
    covered = bool(
        policy
        and policy["active"]
        and instant(policy["valid_from"]) <= start
        and instant(policy["valid_until"]) >= end
    )
    raw = {
        "LWH-MET-010": (str(counts["contacts"]), None, None, uncertain["contact"]),
        "LWH-MET-013": (str(counts["deaths"]), None, None, uncertain["inpatient"]),
        "LWH-MET-014": (
            None,
            str(counts["deaths"]),
            str(counts["dispositions"]),
            uncertain["inpatient"],
        ),
        "LWH-MET-025": (
            None,
            str(counts["accepted_referrals"]),
            str(counts["referral_requests"]),
            uncertain["referral"],
        ),
    }
    values = {}
    from decimal import Decimal

    for metric, (value, numerator, denominator, missing) in raw.items():
        usable = covered and not missing and (denominator is None or int(denominator) > 0)
        if usable and denominator is not None:
            value = str(
                (Decimal(numerator) / Decimal(denominator) * 100).quantize(Decimal("0.00000001"))
            )
        values[metric] = {
            "metric_id": metric,
            "value": value if usable else None,
            "numerator": numerator if usable else None,
            "denominator": denominator if usable else None,
            "completeness": "PARTIAL" if usable else "UNKNOWN",
            "explanation": "Native LW Care subset only. Review source coverage and reconciliation before declaring complete or nil."
            if usable
            else "No usable full-period clinical activation, denominator or complete source evidence; no clinical zero inferred.",
            "incomplete_source_records": missing,
        }
    return values, counts, uncertain


async def extract(service, obligation, definitions):
    require(
        obligation["period_end"] <= db.now(),
        "PERIOD_NOT_ENDED",
        "End the occurrence period before extracting",
        409,
    )
    records, contents, policy, state_hash, manifest, event_count = await verified_sources(
        service, obligation
    )
    measured, counts, uncertain = calculate(records, contents, policy, obligation)
    payload = {
        "rule_version": EDITION,
        "as_of": db.now(),
        "period_start": obligation["period_start"],
        "period_end": obligation["period_end"],
        "source_count": len(manifest),
        "signed_events_verified": event_count,
        "counts": counts,
        "incomplete_sources": uncertain,
        "source_scope": "NATIVE_LW_CARE_ONLY",
        "values": {
            identifier: measured[value["metric_id"]]
            for identifier, value in definitions.items()
            if value["payload"]["source_selector"] in SELECTORS.values()
        },
        "limitations": catalogue()["limitations"],
        "freshness_rule": catalogue()["freshness"],
    }
    row = {
        "id": db.uid(),
        "obligation_id": obligation["id"],
        "source_hash": state_hash,
        "payload_ciphertext": service.box.encrypt(s.canonical(payload)),
        "actor_id": service.actor["id"],
        "created_at": db.now(),
    }
    await service.session.execute(t.extracts.insert().values(**row))
    await service.log(
        "NATIVE_EXTRACT_MANIFEST",
        {
            "id": row["id"],
            "version": 1,
            "obligation_id": obligation["id"],
            "source_hash": state_hash,
            "aggregate_hash": s.digest(payload),
            "sources": manifest,
        },
        "reporting.native_extract_prepared",
        obligation,
    )
    return s.opened(service.box, row)
