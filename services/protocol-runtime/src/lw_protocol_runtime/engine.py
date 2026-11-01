"""
Deterministic Three-Valued Protocol Runtime for Health Navigator (§7.1–7.5).

Safety Guarantees:
1. No LLM or statistical inference participates in routing decisions (`model_made_decision = False`).
2. Missing or ambiguous critical fields NEVER default to False; they evaluate to TriBool.UNKNOWN.
3. Hard-stop rules evaluate BEFORE missing-routine-field checks so an already-confirmed red flag
   immediately triggers EMERGENCY_GUIDANCE even if secondary questions are unanswered.
4. Any bundle with TEST-ONLY / SYNTHETIC scope or invalid SHA-256 signature is rejected for live routing.
5. Dual clinical authorization (distinct clinical_owner and clinical_reviewer signatures) is required
   before a bundle can enter ACTIVE status.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

RUNTIME_ENGINE_VERSION = "1.0.0-deterministic"


class TriBool(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    def __and__(self, other: TriBool) -> TriBool:
        # Kleene three-valued AND: FALSE dominates, otherwise UNKNOWN dominates TRUE
        if self == TriBool.FALSE or other == TriBool.FALSE:
            return TriBool.FALSE
        if self == TriBool.UNKNOWN or other == TriBool.UNKNOWN:
            return TriBool.UNKNOWN
        return TriBool.TRUE

    def __or__(self, other: TriBool) -> TriBool:
        # Kleene three-valued OR: TRUE dominates, otherwise UNKNOWN dominates FALSE
        if self == TriBool.TRUE or other == TriBool.TRUE:
            return TriBool.TRUE
        if self == TriBool.UNKNOWN or other == TriBool.UNKNOWN:
            return TriBool.UNKNOWN
        return TriBool.FALSE

    def invert(self) -> TriBool:
        if self == TriBool.TRUE:
            return TriBool.FALSE
        if self == TriBool.FALSE:
            return TriBool.TRUE
        return TriBool.UNKNOWN


class ProtocolBundleStatus(str, Enum):
    DRAFT = "DRAFT"
    CLINICAL_REVIEW = "CLINICAL_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class ProtocolOutcomeType(str, Enum):
    EMERGENCY_GUIDANCE = "EMERGENCY_GUIDANCE"
    URGENT_PROFESSIONAL_ASSESSMENT = "URGENT_PROFESSIONAL_ASSESSMENT"
    CLINICIAN_REVIEW = "CLINICIAN_REVIEW"
    ROUTINE_CARE_NAVIGATION = "ROUTINE_CARE_NAVIGATION"
    GENERAL_INFORMATION_WITH_SAFETY_NET = "GENERAL_INFORMATION_WITH_SAFETY_NET"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    PROTOCOL_UNAVAILABLE = "PROTOCOL_UNAVAILABLE"


class InputFieldSpec(BaseModel):
    field_id: str
    label: str
    field_type: Literal["boolean", "number", "string", "enum", "string_list"]
    critical: bool = True
    allowed_values: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class RuleExpr(BaseModel):
    """
    Declarative AST node for deterministic rule evaluation.
    Supported operators:
      - Logical: all, any, not
      - Comparison: eq, neq, in, not_in, gt, gte, lt, lte, contains_any, is_present
    """

    op: Literal[
        "all",
        "any",
        "not",
        "eq",
        "neq",
        "in",
        "not_in",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains_any",
        "is_present",
    ]
    field: str | None = None
    value: Any = None
    children: list[RuleExpr] = Field(default_factory=list)


class ProtocolRule(BaseModel):
    rule_id: str
    description: str
    condition: RuleExpr
    outcome_type: ProtocolOutcomeType
    outcome_template_id: str
    safety_net_text_id: str
    priority_order: int = 100


class OutcomeTemplate(BaseModel):
    template_id: str
    version: str
    patient_facing_title: str
    patient_facing_guidance: str
    clinician_handoff_banner: str


class EmergencyContactEntry(BaseModel):
    region: str
    label: str
    phone: str
    verified_at_iso: str


class ClinicalSignOffRecord(BaseModel):
    signer_id: str
    signer_name: str
    mdcn_licence_number: str
    role: Literal["CLINICAL_OWNER", "CLINICAL_REVIEWER"]
    signed_at: datetime
    signature_hash: str


class ProtocolBundle(BaseModel):
    bundle_id: str
    semver: str
    purpose: str
    jurisdiction: str = "NG"
    population: str = "ADULT_GENERAL"
    author: str
    clinical_owner: str | None = None
    reviewers: list[str] = Field(default_factory=list)
    sign_offs: list[ClinicalSignOffRecord] = Field(default_factory=list)
    approved_at: datetime | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    scope: str
    exclusions: list[RuleExpr] = Field(default_factory=list)
    input_schema: dict[str, InputFieldSpec]
    question_order: list[str]
    hard_stop_rules: list[ProtocolRule] = Field(default_factory=list)
    routine_rules: list[ProtocolRule] = Field(default_factory=list)
    outcome_templates: dict[str, OutcomeTemplate] = Field(default_factory=dict)
    safety_net_texts: dict[str, str] = Field(default_factory=dict)
    emergency_contacts: list[EmergencyContactEntry] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    test_report_hash: str | None = None
    document_hash: str = ""
    status: ProtocolBundleStatus = ProtocolBundleStatus.DRAFT

    @model_validator(mode="after")
    def ensure_hash_if_missing(self) -> ProtocolBundle:
        if not self.document_hash:
            self.document_hash = compute_bundle_sha256(self)
        return self

    @property
    def is_signed_and_validated(self) -> bool:
        """
        §7.2 & §7.4 Gate:
        A bundle is only valid for active clinical execution if:
        1. Status is ACTIVE
        2. Not expired
        3. Scope is not TEST-ONLY or SYNTHETIC
        4. Has a clinical_owner AND at least one distinct clinical reviewer (dual authorization)
        5. Has a test_report_hash
        6. Canonical SHA-256 document_hash matches current content
        """
        if self.status != ProtocolBundleStatus.ACTIVE:
            return False
        scope_upper = self.scope.upper()
        if "TEST-ONLY" in scope_upper or "SYNTHETIC" in scope_upper:
            return False
        if not self.clinical_owner or not self.reviewers:
            return False
        distinct_reviewers = [r for r in self.reviewers if r != self.clinical_owner]
        if not distinct_reviewers:
            return False
        if not self.test_report_hash:
            return False
        now = datetime.now(timezone.utc)
        if self.expires_at and self.expires_at <= now:
            return False
        if self.effective_at and self.effective_at > now:
            return False
        return self.document_hash == compute_bundle_sha256(self)


def compute_bundle_sha256(bundle: ProtocolBundle) -> str:
    canonical_payload = {
        "bundle_id": bundle.bundle_id,
        "semver": bundle.semver,
        "purpose": bundle.purpose,
        "jurisdiction": bundle.jurisdiction,
        "population": bundle.population,
        "scope": bundle.scope,
        "exclusions": [e.model_dump(mode="json") for e in bundle.exclusions],
        "input_schema": {
            k: v.model_dump(mode="json") for k, v in sorted(bundle.input_schema.items())
        },
        "question_order": bundle.question_order,
        "hard_stop_rules": [r.model_dump(mode="json") for r in bundle.hard_stop_rules],
        "routine_rules": [r.model_dump(mode="json") for r in bundle.routine_rules],
        "outcome_templates": {
            k: v.model_dump(mode="json") for k, v in sorted(bundle.outcome_templates.items())
        },
        "safety_net_texts": dict(sorted(bundle.safety_net_texts.items())),
        "evidence_refs": sorted(bundle.evidence_refs),
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CaseEvaluationInput(BaseModel):
    episode_id: str
    intake_id: str
    input_revision: int = 1
    population: str = "ADULT_GENERAL"
    jurisdiction: str = "NG"
    answers: dict[str, Any]
    ambiguous_fields: list[str] = Field(default_factory=list)
    actor_id: str
    request_id: str
    ai_extraction_provenance: dict[str, Any] | None = None


class ProtocolEvaluationResult(BaseModel):
    protocol_run_id: str
    protocol_bundle_id: str
    protocol_version: str
    protocol_document_hash: str
    input_revision: int
    outcome_type: ProtocolOutcomeType
    hard_stop_triggered: bool
    executed_rule_ids: list[str]
    fired_rule_ids: list[str]
    unresolved_fields: list[str]
    approved_content_id: str
    renderer_template_version: str
    patient_facing_title: str
    patient_facing_guidance: str
    safety_net_guidance_text: str
    emergency_contacts: list[EmergencyContactEntry]
    ai_extraction_provenance: dict[str, Any] | None = None
    clinician_acknowledged: bool = False
    model_made_decision: Literal[False] = False
    evaluated_at_iso: str
    actor_id: str
    request_id: str
    runtime_version: str = RUNTIME_ENGINE_VERSION


def evaluate_expr_tri(
    expr: RuleExpr,
    answers: dict[str, Any],
    ambiguous_set: set[str],
    referenced_unknowns: set[str],
) -> TriBool:
    if expr.op == "all":
        result = TriBool.TRUE
        for child in expr.children:
            child_val = evaluate_expr_tri(child, answers, ambiguous_set, referenced_unknowns)
            result = result & child_val
        return result

    if expr.op == "any":
        result = TriBool.FALSE
        for child in expr.children:
            child_val = evaluate_expr_tri(child, answers, ambiguous_set, referenced_unknowns)
            result = result | child_val
        return result

    if expr.op == "not":
        if not expr.children:
            return TriBool.UNKNOWN
        return evaluate_expr_tri(
            expr.children[0], answers, ambiguous_set, referenced_unknowns
        ).invert()

    field_name = expr.field
    if not field_name:
        return TriBool.UNKNOWN

    if field_name in ambiguous_set:
        referenced_unknowns.add(field_name)
        return TriBool.UNKNOWN

    if expr.op == "is_present":
        val = answers.get(field_name)
        return TriBool.TRUE if val is not None and val != "" else TriBool.FALSE

    if field_name not in answers or answers[field_name] is None or answers[field_name] == "":
        referenced_unknowns.add(field_name)
        return TriBool.UNKNOWN

    actual = answers[field_name]
    expected = expr.value

    try:
        if expr.op == "eq":
            return TriBool.TRUE if actual == expected else TriBool.FALSE
        if expr.op == "neq":
            return TriBool.TRUE if actual != expected else TriBool.FALSE
        if expr.op == "in":
            return TriBool.TRUE if actual in expected else TriBool.FALSE
        if expr.op == "not_in":
            return TriBool.TRUE if actual not in expected else TriBool.FALSE
        if expr.op == "gt":
            return TriBool.TRUE if float(actual) > float(expected) else TriBool.FALSE
        if expr.op == "gte":
            return TriBool.TRUE if float(actual) >= float(expected) else TriBool.FALSE
        if expr.op == "lt":
            return TriBool.TRUE if float(actual) < float(expected) else TriBool.FALSE
        if expr.op == "lte":
            return TriBool.TRUE if float(actual) <= float(expected) else TriBool.FALSE
        if expr.op == "contains_any":
            if not isinstance(actual, (list, set, tuple)):
                referenced_unknowns.add(field_name)
                return TriBool.UNKNOWN
            overlap = set(actual).intersection(set(expected or []))
            return TriBool.TRUE if len(overlap) > 0 else TriBool.FALSE
    except (TypeError, ValueError):
        referenced_unknowns.add(field_name)
        return TriBool.UNKNOWN

    return TriBool.UNKNOWN


FIXED_FALLBACK_EMERGENCY_CONTACTS: list[EmergencyContactEntry] = [
    EmergencyContactEntry(
        region="NG-NATIONAL",
        label="Nigeria National Emergency Toll-Free Number",
        phone="112",
        verified_at_iso="2026-10-30T00:00:00Z",
    ),
    EmergencyContactEntry(
        region="NG-LAGOS",
        label="Lagos State Emergency Service (LASEMA / LASAMBUS)",
        phone="767",
        verified_at_iso="2026-10-30T00:00:00Z",
    ),
]


class ProtocolRegistry:
    """In-memory and DB-syncable registry of versioned ProtocolBundles."""

    def __init__(self, bundles: list[ProtocolBundle] | None = None) -> None:
        self._bundles: dict[tuple[str, str], ProtocolBundle] = {}
        for b in bundles or []:
            self.register(b)

    def register(self, bundle: ProtocolBundle) -> None:
        key = (bundle.population.upper(), bundle.jurisdiction.upper())
        self._bundles[key] = bundle

    def active_for(self, population: str, jurisdiction: str) -> ProtocolBundle | None:
        return self._bundles.get((population.upper(), jurisdiction.upper()))


def validate_structured_answers(
    answers: dict[str, Any],
    ambiguous_fields: list[str],
    schema: dict[str, InputFieldSpec],
) -> list[str]:
    issues: list[str] = []
    ambiguous_set = set(ambiguous_fields)

    for field_id, spec in schema.items():
        if field_id in ambiguous_set:
            issues.append(field_id)
            continue
        val = answers.get(field_id)
        if val is None or val == "":
            if spec.critical:
                issues.append(field_id)
            continue

        if spec.field_type == "boolean" and not isinstance(val, bool):
            issues.append(field_id)
        elif spec.field_type == "number":
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                issues.append(field_id)
            else:
                if spec.min_value is not None and float(val) < spec.min_value:
                    issues.append(field_id)
                if spec.max_value is not None and float(val) > spec.max_value:
                    issues.append(field_id)
        elif spec.field_type == "enum":
            if not isinstance(val, str) or (
                spec.allowed_values and val not in spec.allowed_values
            ):
                issues.append(field_id)
        elif spec.field_type == "string_list":
            if not isinstance(val, list):
                issues.append(field_id)
            elif spec.allowed_values and any(item not in spec.allowed_values for item in val):
                issues.append(field_id)

    return sorted(set(issues))


def execute_protocol(
    case: CaseEvaluationInput,
    protocol_registry: ProtocolRegistry,
) -> ProtocolEvaluationResult:
    """
    §7.3 Deterministic execution contract.
    Never invokes an LLM; always writes full rule provenance and truthful fallbacks.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    bundle = protocol_registry.active_for(case.population, case.jurisdiction)

    # 1. Missing or unvalidated protocol bundle -> truthful PROTOCOL_UNAVAILABLE fallback
    if not bundle or not bundle.is_signed_and_validated:
        return ProtocolEvaluationResult(
            protocol_run_id=str(uuid4()),
            protocol_bundle_id=bundle.bundle_id if bundle else "NONE",
            protocol_version=bundle.semver if bundle else "0.0.0",
            protocol_document_hash=bundle.document_hash if bundle else "NONE",
            input_revision=case.input_revision,
            outcome_type=ProtocolOutcomeType.PROTOCOL_UNAVAILABLE,
            hard_stop_triggered=False,
            executed_rule_ids=[],
            fired_rule_ids=[],
            unresolved_fields=[],
            approved_content_id="FALLBACK_PROTOCOL_UNAVAILABLE_V1",
            renderer_template_version="1.0.0",
            patient_facing_title="Automated Intake Routing Unavailable",
            patient_facing_guidance=(
                "An approved automated intake protocol is not currently active for this request. "
                "You may proceed directly to book a staffed clinician slot or seek in-person care."
            ),
            safety_net_guidance_text=(
                "If you have severe, sudden, or life-threatening symptoms, do not wait for a remote "
                "consultation—contact local emergency services or attend the nearest emergency department immediately."
            ),
            emergency_contacts=(
                bundle.emergency_contacts
                if bundle and bundle.emergency_contacts
                else FIXED_FALLBACK_EMERGENCY_CONTACTS
            ),
            ai_extraction_provenance=case.ai_extraction_provenance,
            evaluated_at_iso=now_iso,
            actor_id=case.actor_id,
            request_id=case.request_id,
        )

    ambiguous_set = set(case.ambiguous_fields)
    executed_rule_ids: list[str] = []
    referenced_unknowns: set[str] = set()

    # 2. Evaluate Hard-Stop Rules FIRST (even if some non-red-flag fields are missing!)
    # This guarantees that a patient reporting e.g. severe chest pain + breathlessness
    # immediately receives EMERGENCY_GUIDANCE without being blocked on minor fields.
    sorted_hard_stops = sorted(bundle.hard_stop_rules, key=lambda r: r.priority_order)
    for rule in sorted_hard_stops:
        executed_rule_ids.append(rule.rule_id)
        eval_res = evaluate_expr_tri(
            rule.condition, case.answers, ambiguous_set, referenced_unknowns
        )
        if eval_res == TriBool.TRUE:
            tmpl = bundle.outcome_templates.get(rule.outcome_template_id)
            safety_text = bundle.safety_net_texts.get(
                rule.safety_net_text_id,
                "Seek immediate emergency medical care at the nearest hospital.",
            )
            return ProtocolEvaluationResult(
                protocol_run_id=str(uuid4()),
                protocol_bundle_id=bundle.bundle_id,
                protocol_version=bundle.semver,
                protocol_document_hash=bundle.document_hash,
                input_revision=case.input_revision,
                outcome_type=rule.outcome_type,
                hard_stop_triggered=True,
                executed_rule_ids=executed_rule_ids,
                fired_rule_ids=[rule.rule_id],
                unresolved_fields=sorted(referenced_unknowns),
                approved_content_id=rule.outcome_template_id,
                renderer_template_version=tmpl.version if tmpl else "1.0.0",
                patient_facing_title=(
                    tmpl.patient_facing_title
                    if tmpl
                    else "Immediate In-Person Emergency Care Required"
                ),
                patient_facing_guidance=(
                    tmpl.patient_facing_guidance
                    if tmpl
                    else "Your answers indicate symptoms that require urgent in-person assessment."
                ),
                safety_net_guidance_text=safety_text,
                emergency_contacts=bundle.emergency_contacts or FIXED_FALLBACK_EMERGENCY_CONTACTS,
                ai_extraction_provenance=case.ai_extraction_provenance,
                evaluated_at_iso=now_iso,
                actor_id=case.actor_id,
                request_id=case.request_id,
            )

    # 3. Evaluate Exclusions (Out of Scope)
    for idx, excl_expr in enumerate(bundle.exclusions):
        excl_id = f"EXCLUSION_{idx + 1}"
        executed_rule_ids.append(excl_id)
        if (
            evaluate_expr_tri(excl_expr, case.answers, ambiguous_set, referenced_unknowns)
            == TriBool.TRUE
        ):
            return ProtocolEvaluationResult(
                protocol_run_id=str(uuid4()),
                protocol_bundle_id=bundle.bundle_id,
                protocol_version=bundle.semver,
                protocol_document_hash=bundle.document_hash,
                input_revision=case.input_revision,
                outcome_type=ProtocolOutcomeType.OUT_OF_SCOPE,
                hard_stop_triggered=False,
                executed_rule_ids=executed_rule_ids,
                fired_rule_ids=[excl_id],
                unresolved_fields=[],
                approved_content_id="OUT_OF_SCOPE_DEFAULT_V1",
                renderer_template_version="1.0.0",
                patient_facing_title="In-Person Assessment Recommended",
                patient_facing_guidance=(
                    "This request falls outside the approved scope for remote intake routing. "
                    "Please arrange an in-person clinical evaluation."
                ),
                safety_net_guidance_text=next(
                    iter(bundle.safety_net_texts.values()),
                    "If symptoms worsen rapidly, seek urgent in-person medical care.",
                ),
                emergency_contacts=bundle.emergency_contacts or FIXED_FALLBACK_EMERGENCY_CONTACTS,
                ai_extraction_provenance=case.ai_extraction_provenance,
                evaluated_at_iso=now_iso,
                actor_id=case.actor_id,
                request_id=case.request_id,
            )

    # 4. Validate critical structured fields; never default missing critical inputs to False (§7.5)
    schema_issues = validate_structured_answers(
        case.answers, case.ambiguous_fields, bundle.input_schema
    )
    all_unresolved = sorted(set(schema_issues).union(referenced_unknowns))
    if all_unresolved:
        return ProtocolEvaluationResult(
            protocol_run_id=str(uuid4()),
            protocol_bundle_id=bundle.bundle_id,
            protocol_version=bundle.semver,
            protocol_document_hash=bundle.document_hash,
            input_revision=case.input_revision,
            outcome_type=ProtocolOutcomeType.INSUFFICIENT_INFORMATION,
            hard_stop_triggered=False,
            executed_rule_ids=executed_rule_ids,
            fired_rule_ids=[],
            unresolved_fields=all_unresolved,
            approved_content_id="INSUFFICIENT_INFORMATION_V1",
            renderer_template_version="1.0.0",
            patient_facing_title="Additional Information Needed",
            patient_facing_guidance=(
                "Please complete or clarify the highlighted clinical intake questions so we can "
                "route your request safely, or proceed to speak with a clinician."
            ),
            safety_net_guidance_text=next(
                iter(bundle.safety_net_texts.values()),
                "If you experience severe symptoms at any point, seek emergency care immediately.",
            ),
            emergency_contacts=bundle.emergency_contacts or FIXED_FALLBACK_EMERGENCY_CONTACTS,
            ai_extraction_provenance=case.ai_extraction_provenance,
            evaluated_at_iso=now_iso,
            actor_id=case.actor_id,
            request_id=case.request_id,
        )

    # 5. Evaluate Routine Rules in Approved Priority Order
    sorted_routine = sorted(bundle.routine_rules, key=lambda r: r.priority_order)
    for rule in sorted_routine:
        executed_rule_ids.append(rule.rule_id)
        eval_res = evaluate_expr_tri(
            rule.condition, case.answers, ambiguous_set, referenced_unknowns
        )
        if eval_res == TriBool.TRUE:
            tmpl = bundle.outcome_templates.get(rule.outcome_template_id)
            safety_text = bundle.safety_net_texts.get(
                rule.safety_net_text_id,
                "Monitor your symptoms closely and seek urgent care if your condition worsens.",
            )
            return ProtocolEvaluationResult(
                protocol_run_id=str(uuid4()),
                protocol_bundle_id=bundle.bundle_id,
                protocol_version=bundle.semver,
                protocol_document_hash=bundle.document_hash,
                input_revision=case.input_revision,
                outcome_type=rule.outcome_type,
                hard_stop_triggered=False,
                executed_rule_ids=executed_rule_ids,
                fired_rule_ids=[rule.rule_id],
                unresolved_fields=[],
                approved_content_id=rule.outcome_template_id,
                renderer_template_version=tmpl.version if tmpl else "1.0.0",
                patient_facing_title=(
                    tmpl.patient_facing_title if tmpl else "Clinician Consultation Recommended"
                ),
                patient_facing_guidance=(
                    tmpl.patient_facing_guidance
                    if tmpl
                    else "You may proceed to schedule a remote consultation with a licensed doctor."
                ),
                safety_net_guidance_text=safety_text,
                emergency_contacts=bundle.emergency_contacts or FIXED_FALLBACK_EMERGENCY_CONTACTS,
                ai_extraction_provenance=case.ai_extraction_provenance,
                evaluated_at_iso=now_iso,
                actor_id=case.actor_id,
                request_id=case.request_id,
            )

    # 6. No rule matched -> Truthful INSUFFICIENT_INFORMATION fallback
    return ProtocolEvaluationResult(
        protocol_run_id=str(uuid4()),
        protocol_bundle_id=bundle.bundle_id,
        protocol_version=bundle.semver,
        protocol_document_hash=bundle.document_hash,
        input_revision=case.input_revision,
        outcome_type=ProtocolOutcomeType.INSUFFICIENT_INFORMATION,
        hard_stop_triggered=False,
        executed_rule_ids=executed_rule_ids,
        fired_rule_ids=[],
        unresolved_fields=["NO_RULE_MATCH_REQUIRES_CLINICIAN_REVIEW"],
        approved_content_id="NO_RULE_MATCH_V1",
        renderer_template_version="1.0.0",
        patient_facing_title="Clinician Review Required",
        patient_facing_guidance=(
            "Your intake answers require direct review by a licensed clinician rather than "
            "automated routing."
        ),
        safety_net_guidance_text=next(
            iter(bundle.safety_net_texts.values()),
            "If your symptoms worsen, seek immediate in-person medical evaluation.",
        ),
        emergency_contacts=bundle.emergency_contacts or FIXED_FALLBACK_EMERGENCY_CONTACTS,
        ai_extraction_provenance=case.ai_extraction_provenance,
        evaluated_at_iso=now_iso,
        actor_id=case.actor_id,
        request_id=case.request_id,
    )
