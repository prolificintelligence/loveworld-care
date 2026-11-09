"""Research-informed working forms; proposals are never institutional approvals."""

from datetime import datetime
from typing import Literal

from pydantic import model_validator

from .. import db
from ..contracts import StrictModel
from ..domain import require
from . import contracts as c
from . import store as s
from .templates import Template, TemplateService

EDITION = "LWH-WORKING-2026.1"
SOURCES = [
    {
        "title": "WHO RHIS general principles (2023)",
        "url": "https://www.who.int/publications/i/item/9789240063938",
    },
    {
        "title": "WHO community health data quality review (2023)",
        "url": "https://www.who.int/publications/m/item/module-4--data-quality-review-for-community-health-data",
    },
    {
        "title": "WHO routine data quality review (2019)",
        "url": "https://www.who.int/docs/default-source/documents/ddi/facilityanalysisguidance-integratedhealthsservices.pdf",
    },
    {
        "title": "Nigeria CHPRBN standing orders: NHMIS routine reporting forms (2024)",
        "url": "https://chprbn.gov.ng/wp-content/uploads/2024/12/CHO-Section-1-8-TEXT.pdf",
    },
    {
        "title": "WHO SARA reference manual (2015)",
        "url": "https://www.who.int/publications/i/item/WHO-HIS-HSI-2014.5-Rev.1",
    },
    {
        "title": "WHO patient safety reporting guidance (2020)",
        "url": "https://www.who.int/publications/i/item/9789240010338",
    },
]


def measure(
    number, label, numerator, denominator=None, *, aggregation=None, unit=None, source, exclusions
):
    return {
        "metric_id": f"LWH-MET-{number:03}",
        "name": label,
        "formula": "RATIO" if denominator else "COUNT",
        "aggregation": aggregation or ("RATIO_OF_SUMS" if denominator else "SUM"),
        "unit": unit or ("percent" if denominator else "events"),
        "scale": "100" if denominator else "1",
        "numerator_is_subset": bool(denominator),
        "source_selector": "MANUAL",
        "numerator_definition": numerator,
        "denominator_definition": denominator or "Not applicable: count, not a population rate.",
        "population_definition": "The selected reporting unit and half-open occurrence period [start, end), using its recorded reporting timezone. Each underlying event is included once in this stream.",
        "inclusion_exclusion": exclusions
        + " Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.",
        "dimensions": ["reporting_unit", "occurrence_period"],
        "source_register": source,
    }


def catalogue():
    facility = [
        measure(
            10,
            "Completed service contacts",
            "Distinct completed encounter identifiers with an actual signed service/disposition in this period.",
            source="Completed encounter register or verified equivalent",
            exclusions="Exclude drafts, cancellations, appointments and duplicate copies. Remote contacts require actual completed care. This is not unique people; reconcile manual and EMR sources rather than adding them.",
        ),
        measure(
            11,
            "Distinct patients served within this facility",
            "Distinct custodian-reviewed local patient links among the qualifying completed contacts.",
            aggregation="NONE",
            unit="people within facility only",
            source="Reviewed patient identity crosswalk and encounter register",
            exclusions="Exclude unresolved links. No addition across facilities, zones or periods without reviewed identity reconciliation. Declare unresolved-link counts in the explanation.",
        ),
        measure(
            13,
            "Inpatient deaths by occurrence",
            "Distinct verified inpatient death dispositions occurring in the period.",
            source="Signed inpatient disposition and death register",
            exclusions="Exclude community deaths, unconfirmed reports, arrival-dead and duplicate notifications. Not deaths among community residents.",
        ),
        measure(
            14,
            "Institutional inpatient mortality proportion",
            "Verified inpatient deaths among stays with final death/discharge disposition in the period.",
            "All eligible final inpatient discharge dispositions including deaths in the same period.",
            source="Inpatient final disposition register",
            exclusions="Exclude transfers out without a final local discharge/death, arrival-dead and open stays from both components. Show case mix and incomplete dispositions in explanation. Not population mortality; no facility ranking from this alone.",
        ),
        measure(
            16,
            "Care access fulfilment",
            "Eligible care requests received in this period with the suitable requested service actually delivered by the period-end cut-off.",
            "All eligible care requests received in this period, including pending or unavailable services at cut-off.",
            source="Care request and delivered-service receipts",
            exclusions="Exclude duplicates, explicitly ineligible and withdrawn requests, declaring those counts in explanation. Automated acknowledgement is not care. Late outcomes enter a corrected version of this cohort.",
        ),
        measure(
            18,
            "Unmet suitable-care requests",
            "Distinct eligible requests received in this period still unfulfilled at cut-off because suitable capacity or capability was unavailable.",
            source="Care request and capacity/decline evidence",
            exclusions="Deduplicate repeated attempts within one request episode. Exclude patient withdrawal, ineligibility and requests merely awaiting review; disclose pending separately.",
        ),
        measure(
            20,
            "Continuity tasks completed by deadline",
            "Required follow-up or result tasks due in the period with independently evidenced completion no later than their recorded deadline.",
            "All required follow-up or result tasks whose recorded deadline falls in the period, including overdue and nonresponding cases.",
            source="Clinical task due-times and completion evidence",
            exclusions="Reminder delivery, message opening and patient nonresponse do not establish completion. Exclude a task only with documented cancellation authority, disclosed in explanation.",
        ),
        measure(
            23,
            "Planned service windows actually covered",
            "Approved service windows in the period covered throughout by the required privileged team.",
            "All approved planned service windows in the period, including uncovered windows.",
            source="Approved operating windows, duty roster and privilege evidence",
            exclusions="Count each scheduled service window once; partial staffing is not full coverage. Account count, nominal employment and a directory listing do not demonstrate coverage.",
        ),
        measure(
            24,
            "Current readiness evidence for operating capabilities",
            "Expected operating capabilities whose required readiness evidence is unexpired at period end.",
            "All capabilities expected to operate at the period-end review, including those with absent or expired evidence.",
            aggregation="NONE",
            source="Capability catalogue and time-bounded readiness assertions",
            exclusions="An as-of measure: do not sum across months. Readiness is not licence, guaranteed future availability, accepted referral or quality certification.",
        ),
        measure(
            25,
            "Referral requests receiving actual acceptance",
            "Eligible referral requests created in the period with recorded receiving-team acceptance by the period-end cut-off.",
            "All eligible referral requests created in the period, including declined, unreachable and pending requests.",
            source="Referral requests and receiving acceptance receipts",
            exclusions="A sent message, directory match or transport booking is not acceptance. Exclude documented duplicates or withdrawal before review and disclose them. Late acceptance corrects the same cohort.",
        ),
        measure(
            26,
            "Referral outcomes verified by due date",
            "Referrals due for outcome in the period with verified receiving outcome recorded by their due date.",
            "All referrals whose recorded outcome deadline falls in the period, including overdue and lost-to-follow-up cases.",
            source="Accepted handover, receiving outcome and due-date register",
            exclusions="Acceptance, transport and travel are not completed care. Keep unknown, declined and pending outcomes visible; no patient-identifying narrative in returns.",
        ),
        measure(
            29,
            "Critical results with required human follow-through",
            "Critical results with required acknowledgement and action completed by their policy-derived deadline falling in the period.",
            "All critical results whose required action deadline falls in the period under the actual local critical-result policy.",
            source="Critical flags, approved local policy and acknowledgement/action receipts",
            exclusions="Delivery receipt is not clinical acknowledgement. Include overdue and missing actions; if no approved flag/deadline policy exists report UNKNOWN, not zero.",
        ),
        measure(
            32,
            "Essential product-days with confirmed stockout",
            "Distinct required essential-product and operating-day pairs during the period with verified usable stock unavailable for any required service interval.",
            source="Locally approved essential-product list, stock ledger and physical checks",
            exclusions="One product-day once regardless of repeated attempts. Quarantined or uncertain stock is not usable; disclose uncertainty separately. Not number of patients harmed or a population rate.",
        ),
        measure(
            33,
            "Staffed qualified bed occupancy",
            "Occupied minutes in eligible staffed qualified beds during the period.",
            "Available staffed qualified bed-minutes during the same period.",
            source="Timestamped occupancy and staffed-bed capacity ledger",
            exclusions="Exclude closed/unqualified beds from both components and document closures. Reservations are not occupancy. Do not use licensed bed count as staffed capacity; unknown capacity means unavailable ratio.",
        ),
    ]
    coded = measure(
        12,
        "Completed contacts with a coded clinical condition",
        "Distinct qualifying completed encounters with at least one clinician-signed condition code from the facility's recorded coding-system/version; count each encounter once.",
        source="Signed assessment/diagnosis register, coding-system version and completed encounter register",
        exclusions="This initial profile selects any valid signed condition code and does not classify a specific disease. Suspected/confirmed status remains in the protected source. Exclude uncoded, voided and draft diagnoses. If the coding system or source is unavailable, report UNKNOWN. This is not disease incidence, prevalence, unique people or diagnostic accuracy.",
    )
    coded["less_or_equal_metric"] = "LWH-MET-010"
    facility.insert(2, coded)
    zone = [
        measure(
            35,
            "Approved health education sessions delivered",
            "Distinct approved health education sessions actually delivered in the period with content-version and delivery evidence.",
            source="Approved education content and session delivery register",
            exclusions="Exclude plans, duplicate broadcasts counted as the same session and unapproved messages. Sessions are not recipients, comprehension, clinical contacts or improved health outcomes.",
        ),
        measure(
            36,
            "Community interventions completed by deadline",
            "Accepted community interventions due in the period with evidence independently accepted complete by deadline.",
            "All accepted community interventions due in the period, including blocked and overdue work.",
            source="Intervention commitments, due dates and independent completion reviews",
            exclusions="A proposed, unowned or merely funded activity is not accepted completion. Exclusions and cancelled commitments require authority and remain disclosed.",
        ),
        measure(
            27,
            "Required demand areas with evidenced serviceability",
            "Required demand areas meeting the adopted serviceability standard at period end with reviewed capability and access evidence.",
            "All demand areas in the actual approved required-area inventory at period end.",
            aggregation="NONE",
            source="Approved area inventory, access standard and serviceability assessment",
            exclusions="If the inventory or access standard is absent, report UNKNOWN. Facility counts or self-selected attendance cannot establish geographic reach. Do not sum as-of percentages over periods.",
        ),
    ]
    region = [
        measure(
            1,
            "Verified active registry coverage",
            "Expected in-scope sites with a verified active registry record at period end.",
            "All sites in the approved expected-site inventory at period end, including sites not registered.",
            aggregation="NONE",
            source="Expected-site inventory and verified registry records",
            exclusions="No approved expected-site inventory means UNKNOWN. Registered sites alone cannot form both components. Count facility sites, not owners; do not sum across months.",
        ),
        measure(
            3,
            "Corrective actions completed by deadline",
            "Corrective actions due in the period with independently accepted completion no later than deadline.",
            "All corrective actions due in the period, including overdue and nonresponding sites.",
            source="Affiliation corrective-action due dates and independent acceptance",
            exclusions="Keep severity and criteria versions in the supporting evidence. Self-attested completion and an expired obligation are not accepted corrective closure.",
        ),
        measure(
            4,
            "Affiliation renewal decisions made in time",
            "Prior affiliation decisions expiring in the period with the renewal decision recorded before the prior expiry.",
            "All prior affiliation decisions due to expire in the period, including expired and nonresponding sites.",
            source="Prior decision expiry and actual renewal-decision timestamps",
            exclusions="Do not infer renewal from registration or a pending application; do not remove expired sites to improve the proportion.",
        ),
        measure(
            36,
            "Regional interventions completed by deadline",
            "Accepted regional coordination interventions due in the period with independently accepted completion by deadline.",
            "All accepted regional coordination interventions due in the period, including blocked and overdue work.",
            source="Regional commitments, due dates and independent completion reviews",
            exclusions="Exclude zone-delivered interventions already counted in the zone stream. Completion requires evidence and independent acceptance; funding alone is not fulfilment.",
        ),
    ]
    forms = [
        {
            "code": "FACILITY-MONTHLY",
            "name": "Proposed monthly facility health-service return",
            "stream": "FACILITY_ACTIVITY",
            "measures": facility,
        },
        {
            "code": "ZONE-MONTHLY",
            "name": "Proposed monthly zone community-health return",
            "stream": "ZONE_COMMUNITY",
            "measures": zone,
        },
        {
            "code": "REGION-MONTHLY",
            "name": "Proposed monthly regional coordination return",
            "stream": "REGIONAL_COORDINATION",
            "measures": region,
        },
    ]
    return {
        "edition": EDITION,
        "status": "PROPOSED_FOR_DIRECTOR_REVIEW",
        "researched_on": "2026-11-09",
        "authority": "Implementation proposal authorised by the project owner; not represented as a Directorate-approved form, national submission, WHO endorsement or clinical protocol.",
        "sources": SOURCES,
        "calendar": {
            "status": "PROPOSED_CONFIGURE_EXACT_OBLIGATIONS_AFTER_ADOPTION",
            "frequency": "CALENDAR_MONTH",
            "period": "Local month start inclusive through next local month start exclusive; officer records UTC boundaries and an actual IANA timezone for each obligation.",
            "submission": "23:59 local time on the fifth day of the following month",
            "independent_review": "Target tenth day of the following month; unresolved returns remain unverified.",
            "leadership_review": "Target fifteenth day; release only under the adopted disclosure policy with actual coverage and missingness.",
            "exceptions": "No automatic deadlines, public-holiday extensions or emergency-response service levels are adopted. Urgent safety matters use the actual covered escalation route immediately, not the monthly return.",
        },
        "return_rules": [
            "Source counts and ratio components must be nonnegative. Subset numerators cannot exceed denominators. Zero or absent denominators produce an unavailable rate, never fabricated zero.",
            "VALUE, NIL, PARTIAL, UNKNOWN, MISSING and NOT_APPLICABLE remain distinct; non-applicability and unavailable values require explanation. A lack of service is not automatically a nil outcome.",
            "SUM applies only to disjoint reporting units and periods. RATIO_OF_SUMS recomputes from compatible components. NONE forbids arithmetic roll-up. Do not add zone/community activity to facility clinical contacts.",
            "Maintain source reference, reconciliation, officer attestation and independent examination evidence. Confidential cases stay in their protected workflow; no names, patient IDs or credential-bearing links in aggregate returns.",
            "Governors may configure provisional indicator versions and a DRAFT mapping. Independent review and explicit adoption remain required before template-bound obligations. Director changes create a new edition; existing obligations retain their old definitions and mappings.",
        ],
        "forms": forms,
    }


class Prepare(StrictModel):
    form_code: Literal["FACILITY-MONTHLY", "ZONE-MONTHLY", "REGION-MONTHLY"]
    edition: Literal["LWH-WORKING-2026.1"]
    valid_from: datetime
    valid_until: datetime
    authority_reference: c.Text
    intent_confirmed: Literal[True]

    @model_validator(mode="after")
    def ordered(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Proposed validity must be ordered")
        return self


async def prepare(service, body):
    service.governor()
    pack = catalogue()
    form = next(item for item in pack["forms"] if item["code"] == body["form_code"])
    require(
        body["valid_until"] > db.now(),
        "TEMPLATE_EXPIRED",
        "Prepare a current or future edition",
        422,
    )
    fields = [
        {
            "code": key.lower(),
            "label": label,
            "required": True,
            "disposition": "CONTEXT",
            "context": key,
            "rationale": "Frozen reporting-unit/period context or authenticated officer attestation; not a patient-level value.",
        }
        for key, label in [
            (
                "FACILITY"
                if form["stream"] == "FACILITY_ACTIVITY"
                else "ZONE"
                if form["stream"] == "ZONE_COMMUNITY"
                else "REGION",
                "Reporting unit",
            ),
            ("PERIOD_START", "Occurrence period start"),
            ("PERIOD_END", "Occurrence period end"),
            ("OFFICER_ATTESTATION", "Officer source attestation"),
        ]
    ]
    for measure in form["measures"]:
        payload = {key: value for key, value in measure.items() if key != "source_register"}
        # Unique, immutable configuration per draft. The journal retains actual
        # governor authority; no implicit approval of the proposed template.
        payload.update(
            definition_version="W26-" + db.uid(),
            stream=form["stream"],
            valid_from=body["valid_from"],
            valid_until=body["valid_until"],
            adoption_reference=body["authority_reference"],
            intent_confirmed=True,
            template_reconciliation=f"{EDITION}/{form['code']}; proposed for Director review. Source: {measure['source_register']}. Full form requires independent review and adoption.",
        )
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
                    "rationale": measure["source_register"]
                    + ". "
                    + (
                        measure["denominator_definition"]
                        if part == "DENOMINATOR"
                        else measure["numerator_definition"]
                    ),
                }
            )
    payload = Template.model_validate(
        {
            "name": form["name"],
            "source_version": EDITION,
            "source_reference": f"Packaged research proposal {EDITION}/{form['code']}; /v1/reporting/template-proposals. Proposed for Director review, not an official Directorate source form.",
            "source_sha256": s.digest(pack),
            "stream": form["stream"],
            "jurisdictions": ["GLOBAL"],
            "adoption_reference": body["authority_reference"],
            "valid_from": body["valid_from"],
            "valid_until": body["valid_until"],
            "fields": fields,
        }
    ).model_dump(mode="json")
    return await TemplateService(service).create(payload)
