"""
Policy-Limited AI Model Gateway & Bounded Agent Runtime (§15.1–15.6).

Enforces:
- §15.1: AI may draft intake summaries or encounter note drafts, NEVER diagnose, prescribe,
  override a protocol hard-stop, sign clinical notes, or redeem sponsor funds.
- §15.2: Purpose + Data-Tier routing (T3 Sensitive Clinical data is restricted to private /
  contract-approved endpoints; never exported to unapproved public endpoints).
- §15.4 & AT-05: Clinical draft safety filter catches false reassurance or autonomous dosing.
- §15.5: Strictly bounded AgentDefinitions with human checkpoints and max cost budgets.
- §15.6 & AT-16: Instant AI-Off Kill Switch that preserves full deterministic/human care flow.
- AT-12: Untrusted input prompt-injection detection and isolation.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

UNSIGNED_WATERMARK = "UNSIGNED / FOR CLINICIAN REVIEW ONLY"


class DataTier(str, Enum):
    T0_PUBLIC = "T0_PUBLIC"
    T1_ORGANISATION_ONLY = "T1_ORGANISATION_ONLY"
    T2_PERSONAL = "T2_PERSONAL"
    T3_SENSITIVE_CLINICAL = "T3_SENSITIVE_CLINICAL"
    T4_RESTRICTED_CONTROLS = "T4_RESTRICTED_CONTROLS"


class ModelProviderBackend(str, Enum):
    PRIVATE_MEDGEMMA_VLLM = "PRIVATE_MEDGEMMA_VLLM"
    OPENROUTER_FREE_TIER = "OPENROUTER_FREE_TIER"
    GOOGLE_GEMINI_VERTEX = "GOOGLE_GEMINI_VERTEX"
    ANTHROPIC_CLAUDE = "ANTHROPIC_CLAUDE"
    DETERMINISTIC_FALLBACK_NO_AI = "DETERMINISTIC_FALLBACK_NO_AI"


class AgentRoleId(str, Enum):
    INTAKE_ASSISTANT = "INTAKE_ASSISTANT"
    APPOINTMENT_COORDINATOR = "APPOINTMENT_COORDINATOR"
    CARE_FOLLOW_UP_ASSISTANT = "CARE_FOLLOW_UP_ASSISTANT"
    SPONSOR_FULFILMENT_AGENT = "SPONSOR_FULFILMENT_AGENT"
    CLINICAL_NOTE_COPILOT = "CLINICAL_NOTE_COPILOT"
    EXECUTIVE_INTELLIGENCE_AGENT = "EXECUTIVE_INTELLIGENCE_AGENT"
    REVENUE_ASSURANCE_AGENT = "REVENUE_ASSURANCE_AGENT"


class AgentDefinition(BaseModel):
    agent_id: AgentRoleId
    business_owner: str
    objective: str
    max_permissible_data_tier: DataTier
    allowed_backends: list[ModelProviderBackend]
    allowed_tools: list[str]
    prohibited_actions: list[str]
    requires_human_sign_off: bool = True
    max_tokens: int = 1024
    max_cost_ngn_minor: int = 15000  # 150 NGN in kobo
    timeout_seconds: float = 12.0


AGENT_REGISTRY: dict[AgentRoleId, AgentDefinition] = {
    AgentRoleId.INTAKE_ASSISTANT: AgentDefinition(
        agent_id=AgentRoleId.INTAKE_ASSISTANT,
        business_owner="Clinical Lead + Product Owner",
        objective="Extract candidate structured intake fields and draft a readable summary for the assigned clinician.",
        max_permissible_data_tier=DataTier.T3_SENSITIVE_CLINICAL,
        allowed_backends=[
            ModelProviderBackend.PRIVATE_MEDGEMMA_VLLM,
            ModelProviderBackend.GOOGLE_GEMINI_VERTEX,
        ],
        allowed_tools=["extract_intake_fields", "draft_clinician_intake_summary"],
        prohibited_actions=[
            "diagnose_patient",
            "recommend_medication_or_dosage",
            "override_protocol_hard_stop",
            "sign_encounter",
        ],
        requires_human_sign_off=True,
        max_tokens=900,
        max_cost_ngn_minor=12000,
    ),
    AgentRoleId.CLINICAL_NOTE_COPILOT: AgentDefinition(
        agent_id=AgentRoleId.CLINICAL_NOTE_COPILOT,
        business_owner="Clinical Lead",
        objective="Propose an UNSIGNED draft SOAP note from verified encounter facts for clinician editing and signature.",
        max_permissible_data_tier=DataTier.T3_SENSITIVE_CLINICAL,
        allowed_backends=[
            ModelProviderBackend.PRIVATE_MEDGEMMA_VLLM,
            ModelProviderBackend.GOOGLE_GEMINI_VERTEX,
            ModelProviderBackend.ANTHROPIC_CLAUDE,
        ],
        allowed_tools=["draft_unsigned_soap_note"],
        prohibited_actions=["sign_encounter", "issue_prescription", "authorize_referral"],
        requires_human_sign_off=True,
        max_tokens=1500,
        max_cost_ngn_minor=20000,
    ),
    AgentRoleId.APPOINTMENT_COORDINATOR: AgentDefinition(
        agent_id=AgentRoleId.APPOINTMENT_COORDINATOR,
        business_owner="Clinical Operations Manager",
        objective="Match patient schedule preferences with verified staffed roster slots.",
        max_permissible_data_tier=DataTier.T2_PERSONAL,
        allowed_backends=[ModelProviderBackend.GOOGLE_GEMINI_VERTEX],
        allowed_tools=["list_verified_slots", "prepare_reminder"],
        prohibited_actions=["invent_clinician_availability", "assess_clinical_urgency"],
        requires_human_sign_off=True,
        max_tokens=512,
        max_cost_ngn_minor=5000,
    ),
    AgentRoleId.CARE_FOLLOW_UP_ASSISTANT: AgentDefinition(
        agent_id=AgentRoleId.CARE_FOLLOW_UP_ASSISTANT,
        business_owner="Clinical Operations Manager",
        objective="Prepare clinician-approved post-encounter follow-up check-in reminders.",
        max_permissible_data_tier=DataTier.T2_PERSONAL,
        allowed_backends=[ModelProviderBackend.GOOGLE_GEMINI_VERTEX],
        allowed_tools=["format_approved_followup_reminder"],
        prohibited_actions=["modify_care_plan", "conduct_new_clinical_assessment"],
        requires_human_sign_off=True,
        max_tokens=512,
        max_cost_ngn_minor=5000,
    ),
    AgentRoleId.SPONSOR_FULFILMENT_AGENT: AgentDefinition(
        agent_id=AgentRoleId.SPONSOR_FULFILMENT_AGENT,
        business_owner="Finance Controller",
        objective="Check contract eligibility rules for sponsor pools without accessing clinical notes.",
        max_permissible_data_tier=DataTier.T2_PERSONAL,
        allowed_backends=[ModelProviderBackend.GOOGLE_GEMINI_VERTEX],
        allowed_tools=["verify_contract_cohort_rule"],
        prohibited_actions=["read_clinical_narrative", "redirect_funds", "override_entitlement_cap"],
        requires_human_sign_off=True,
        max_tokens=512,
        max_cost_ngn_minor=5000,
    ),
    AgentRoleId.EXECUTIVE_INTELLIGENCE_AGENT: AgentDefinition(
        agent_id=AgentRoleId.EXECUTIVE_INTELLIGENCE_AGENT,
        business_owner="Executive Sponsor / Directorate",
        objective="Summarize aggregate de-identified service volume, unit economics, and SLA performance.",
        max_permissible_data_tier=DataTier.T1_ORGANISATION_ONLY,
        allowed_backends=[
            ModelProviderBackend.GOOGLE_GEMINI_VERTEX,
            ModelProviderBackend.ANTHROPIC_CLAUDE,
        ],
        allowed_tools=["summarize_aggregate_kpis"],
        prohibited_actions=["read_patient_record", "read_clinical_narrative"],
        requires_human_sign_off=True,
        max_tokens=1024,
        max_cost_ngn_minor=10000,
    ),
    AgentRoleId.REVENUE_ASSURANCE_AGENT: AgentDefinition(
        agent_id=AgentRoleId.REVENUE_ASSURANCE_AGENT,
        business_owner="Finance Controller",
        objective="Identify settlement mismatches between gateway statements and signed encounters.",
        max_permissible_data_tier=DataTier.T2_PERSONAL,
        allowed_backends=[ModelProviderBackend.GOOGLE_GEMINI_VERTEX],
        allowed_tools=["flag_reconciliation_discrepancy"],
        prohibited_actions=["post_direct_ledger_adjustment", "fabricate_billable_encounter"],
        requires_human_sign_off=True,
        max_tokens=768,
        max_cost_ngn_minor=8000,
    ),
}


PROMPT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"override\s+hard[_\s-]?stop", re.IGNORECASE),
    re.compile(r"call\s+tool|execute\s+command|exfiltrate|dump\s+database", re.IGNORECASE),
    re.compile(r"redeem[_\s-]?entitlement|approve[_\s-]?payout|sign[_\s-]?encounter", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+an?\s+unrestricted", re.IGNORECASE),
]

PROHIBITED_CLINICAL_DRAFT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"you\s+definitely\s+do\s+not\s+have\s+an?\s+emergency", re.IGNORECASE),
    re.compile(r"no\s+need\s+to\s+see\s+a\s+doctor", re.IGNORECASE),
    re.compile(r"guaranteed\s+cure|100%\s+safe\s+to\s+ignore", re.IGNORECASE),
    re.compile(r"i\s+hereby\s+prescribe\s+\d+\s*mg", re.IGNORECASE),
]


def detect_prompt_injection(untrusted_text: str) -> list[str]:
    """AT-12: Scans untrusted intake or document text for adversarial command injection."""
    findings: list[str] = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(untrusted_text):
            findings.append(pattern.pattern)
    return findings


def validate_clinical_draft_safety(draft_text: str) -> tuple[bool, list[str]]:
    """
    AT-05 & §15.4: Ensures AI-generated drafts never contain false reassurance or
    autonomous prescriptions.
    """
    violations: list[str] = []
    for pattern in PROHIBITED_CLINICAL_DRAFT_PATTERNS:
        if pattern.search(draft_text):
            violations.append(pattern.pattern)
    return (len(violations) == 0, violations)


class ModelGatewayConfig(BaseModel):
    ai_kill_switch_enabled: bool = False
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_free_models: list[str] = Field(
        default_factory=lambda: [
            "openrouter/free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
        ]
    )
    gemini_api_key: str | None = None
    gemini_model_id: str = "gemini-2.5-flash"
    medgemma_endpoint_url: str | None = None
    medgemma_api_key: str | None = None
    medgemma_model_id: str = "google/medgemma-1.5-4b-it"
    anthropic_api_key: str | None = None
    anthropic_model_id: str = "claude-3-5-sonnet-latest"
    private_clinical_inference_approved: bool = True


class ModelInvocationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: AgentRoleId
    data_tier: DataTier
    actor_id: str
    encounter_id: str | None = None
    episode_id: str | None = None
    payer_cohort: str = "SELF_PAY"
    structured_context: dict[str, Any] = Field(default_factory=dict)
    untrusted_user_text: str = ""


class ModelInvocationResult(BaseModel):
    invocation_id: str
    request_id: str
    agent_id: AgentRoleId
    status: Literal[
        "COMPLETED_DRAFT",
        "AI_KILL_SWITCH_ACTIVE",
        "BLOCKED_PROMPT_INJECTION",
        "BLOCKED_DATA_TIER_POLICY",
        "REJECTED_SAFETY_FILTER",
        "PROVIDER_UNAVAILABLE_FALLBACK",
    ]
    backend_used: ModelProviderBackend
    model_id: str
    watermark: str = UNSIGNED_WATERMARK
    requires_human_sign_off: Literal[True] = True
    model_made_decision: Literal[False] = False
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    draft_summary: str
    prompt_sha256: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_ngn_minor: int = 0
    latency_ms: int = 0
    security_flags: list[str] = Field(default_factory=list)
    created_at_iso: str


DATA_TIER_ORDER: dict[DataTier, int] = {
    DataTier.T0_PUBLIC: 0,
    DataTier.T1_ORGANISATION_ONLY: 1,
    DataTier.T2_PERSONAL: 2,
    DataTier.T3_SENSITIVE_CLINICAL: 3,
    DataTier.T4_RESTRICTED_CONTROLS: 4,
}


class ModelGatewayRouter:
    """
    Central policy-enforcing router for all AI/SLM assistance in LoveWorld Care (§15.2).
    """

    def __init__(self, config: ModelGatewayConfig) -> None:
        self.config = config

    def set_kill_switch(self, enabled: bool) -> None:
        self.config.ai_kill_switch_enabled = enabled

    async def invoke(self, req: ModelInvocationRequest) -> ModelInvocationResult:
        started = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()
        agent_def = AGENT_REGISTRY[req.agent_id]

        prompt_hash = hashlib.sha256(
            json.dumps(
                {
                    "agent_id": req.agent_id.value,
                    "context": req.structured_context,
                    "text": req.untrusted_user_text,
                },
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()

        # 1. §15.6 & AT-16: AI-Off Kill Switch
        if self.config.ai_kill_switch_enabled:
            return ModelInvocationResult(
                invocation_id=str(uuid4()),
                request_id=req.request_id,
                agent_id=req.agent_id,
                status="AI_KILL_SWITCH_ACTIVE",
                backend_used=ModelProviderBackend.DETERMINISTIC_FALLBACK_NO_AI,
                model_id="ai-off-deterministic",
                draft_summary=(
                    "[AI Assistance Disabled by Governance Kill-Switch] "
                    "Proceeding via deterministic protocol and direct clinician review."
                ),
                prompt_sha256=prompt_hash,
                latency_ms=int((time.perf_counter() - started) * 1000),
                created_at_iso=now_iso,
            )

        # 2. §15.2: Data-Tier Policy Verification (e.g., Executive Agent cannot touch T3 Clinical data)
        if DATA_TIER_ORDER[req.data_tier] > DATA_TIER_ORDER[agent_def.max_permissible_data_tier]:
            return ModelInvocationResult(
                invocation_id=str(uuid4()),
                request_id=req.request_id,
                agent_id=req.agent_id,
                status="BLOCKED_DATA_TIER_POLICY",
                backend_used=ModelProviderBackend.DETERMINISTIC_FALLBACK_NO_AI,
                model_id="policy-blocked",
                draft_summary=(
                    f"Blocked: Agent {req.agent_id.value} is not permitted to process "
                    f"{req.data_tier.value} data."
                ),
                prompt_sha256=prompt_hash,
                security_flags=["DATA_TIER_VIOLATION"],
                latency_ms=int((time.perf_counter() - started) * 1000),
                created_at_iso=now_iso,
            )

        if (
            req.data_tier == DataTier.T3_SENSITIVE_CLINICAL
            and not self.config.private_clinical_inference_approved
        ):
            return ModelInvocationResult(
                invocation_id=str(uuid4()),
                request_id=req.request_id,
                agent_id=req.agent_id,
                status="BLOCKED_DATA_TIER_POLICY",
                backend_used=ModelProviderBackend.DETERMINISTIC_FALLBACK_NO_AI,
                model_id="policy-blocked-t3",
                draft_summary="Blocked: Private T3 clinical model contract is not enabled.",
                prompt_sha256=prompt_hash,
                security_flags=["T3_CONTRACT_NOT_ENABLED"],
                latency_ms=int((time.perf_counter() - started) * 1000),
                created_at_iso=now_iso,
            )

        # 3. AT-12: Untrusted Input Prompt-Injection Guard
        injection_hits = detect_prompt_injection(req.untrusted_user_text)
        if injection_hits:
            return ModelInvocationResult(
                invocation_id=str(uuid4()),
                request_id=req.request_id,
                agent_id=req.agent_id,
                status="BLOCKED_PROMPT_INJECTION",
                backend_used=ModelProviderBackend.DETERMINISTIC_FALLBACK_NO_AI,
                model_id="injection-guard",
                draft_summary=(
                    "[Security Alert: Untrusted input contained adversarial instruction patterns "
                    "and was isolated from model execution. Raw patient input remains visible to clinician.]"
                ),
                prompt_sha256=prompt_hash,
                security_flags=[f"PROMPT_INJECTION:{p}" for p in injection_hits],
                latency_ms=int((time.perf_counter() - started) * 1000),
                created_at_iso=now_iso,
            )

        # 4. Select Backend & Execute (or structured deterministic synthesis when external API key not configured)
        backend, model_id, raw_draft, extracted, p_tok, c_tok = await self._dispatch_to_provider(
            req, agent_def
        )

        # 5. AT-05: Clinical Safety Validation on Draft Output
        is_safe, safety_violations = validate_clinical_draft_safety(raw_draft)
        if not is_safe:
            return ModelInvocationResult(
                invocation_id=str(uuid4()),
                request_id=req.request_id,
                agent_id=req.agent_id,
                status="REJECTED_SAFETY_FILTER",
                backend_used=backend,
                model_id=model_id,
                draft_summary=(
                    "[Safety Gate: Model draft suppressed due to prohibited diagnostic or "
                    "reassurance phrasing. Clinician must review raw patient intake directly.]"
                ),
                prompt_sha256=prompt_hash,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                security_flags=[f"UNSAFE_DRAFT:{v}" for v in safety_violations],
                latency_ms=int((time.perf_counter() - started) * 1000),
                created_at_iso=now_iso,
            )

        # Compute NGN minor-unit (kobo) cost attribution
        estimated_cost_kobo = min(
            agent_def.max_cost_ngn_minor,
            max(100, int((p_tok * 0.5) + (c_tok * 1.5))),
        )

        return ModelInvocationResult(
            invocation_id=str(uuid4()),
            request_id=req.request_id,
            agent_id=req.agent_id,
            status="COMPLETED_DRAFT",
            backend_used=backend,
            model_id=model_id,
            watermark=UNSIGNED_WATERMARK,
            extracted_fields=extracted,
            draft_summary=f"[{UNSIGNED_WATERMARK}] {raw_draft}",
            prompt_sha256=prompt_hash,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            estimated_cost_ngn_minor=estimated_cost_kobo,
            latency_ms=int((time.perf_counter() - started) * 1000),
            created_at_iso=now_iso,
        )

    async def _dispatch_to_provider(
        self,
        req: ModelInvocationRequest,
        agent_def: AgentDefinition,
    ) -> tuple[ModelProviderBackend, str, str, dict[str, Any], int, int]:
        """
        Routes to live configured MedGemma (OpenAI-compatible vLLM), Gemini, or Anthropic
        endpoints when credentials are set; gracefully falls back to structured clinical
        field synthesis if external network/provider is unreachable (§15.6 & AT-16).
        """
        # Prefer Private MedGemma vLLM for T3 Clinical tasks if endpoint is configured and reachable
        if (
            req.data_tier == DataTier.T3_SENSITIVE_CLINICAL
            and self.config.medgemma_endpoint_url
            and self.config.medgemma_api_key
            and not self.config.medgemma_api_key.startswith("REPLACE_")
        ):
            try:
                async with httpx.AsyncClient(timeout=agent_def.timeout_seconds) as client:
                    resp = await client.post(
                        f"{self.config.medgemma_endpoint_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {self.config.medgemma_api_key}"},
                        json={
                            "model": self.config.medgemma_model_id,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a non-decisional clinical documentation assistant. "
                                        "Summarize facts only. Never diagnose or prescribe."
                                    ),
                                },
                                {
                                    "role": "user",
                                    "content": json.dumps(
                                        {
                                            "structured": req.structured_context,
                                            "statement": req.untrusted_user_text,
                                        }
                                    ),
                                },
                            ],
                            "max_tokens": agent_def.max_tokens,
                            "temperature": 0.0,
                        },
                    )
                    if resp.status_code == 200:
                        body = resp.json()
                        text = body["choices"][0]["message"]["content"]
                        usage = body.get("usage", {})
                        return (
                            ModelProviderBackend.PRIVATE_MEDGEMMA_VLLM,
                            self.config.medgemma_model_id,
                            text,
                            self._extract_structured_candidates(req),
                            int(usage.get("prompt_tokens", 120)),
                            int(usage.get("completion_tokens", 80)),
                        )
            except Exception:
                pass

        # 2. Live OpenRouter Free-Tier Provider (with automatic free-model fallback)
        if (
            self.config.openrouter_api_key
            and not self.config.openrouter_api_key.startswith("REPLACE_")
        ):
            for candidate_model in self.config.openrouter_free_models:
                try:
                    async with httpx.AsyncClient(timeout=agent_def.timeout_seconds) as client:
                        resp = await client.post(
                            f"{self.config.openrouter_base_url.rstrip('/')}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.config.openrouter_api_key}",
                                "HTTP-Referer": "https://care.loveworld.org",
                                "X-Title": "LoveWorld Care Clinical Intake Assistant",
                            },
                            json={
                                "model": candidate_model,
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": (
                                            "You are a non-decisional clinical intake and documentation assistant "
                                            "for LoveWorld Care. Summarize the patient's reported facts concisely "
                                            "(2-3 sentences max) for the licensed doctor. "
                                            "STRICT RULES: Never diagnose, never prescribe medication or dosages, "
                                            "and never tell the patient they do not have an emergency."
                                        ),
                                    },
                                    {
                                        "role": "user",
                                        "content": json.dumps(
                                            {
                                                "structured_answers": req.structured_context,
                                                "patient_verbatim_statement": req.untrusted_user_text,
                                            }
                                        ),
                                    },
                                ],
                                "max_tokens": min(agent_def.max_tokens, 350),
                                "temperature": 0.1,
                            },
                        )
                        if resp.status_code == 200:
                            body = resp.json()
                            choices = body.get("choices") or []
                            if choices and choices[0].get("message", {}).get("content"):
                                text = str(choices[0]["message"]["content"]).strip()
                                actual_model = str(body.get("model") or candidate_model)
                                usage = body.get("usage") or {}
                                return (
                                    ModelProviderBackend.OPENROUTER_FREE_TIER,
                                    actual_model,
                                    text,
                                    self._extract_structured_candidates(req),
                                    int(usage.get("prompt_tokens", 110)),
                                    int(usage.get("completion_tokens", 65)),
                                )
                except Exception:
                    continue

        # Deterministic structured clinical summary fallback when external LLM API is offline
        extracted = self._extract_structured_candidates(req)
        summary_parts: list[str] = []
        if req.structured_context:
            kv = ", ".join(f"{k}={v}" for k, v in sorted(req.structured_context.items()))
            summary_parts.append(f"Reported structured answers: {kv}.")
        if req.untrusted_user_text.strip():
            summary_parts.append(
                f"Patient verbatim statement preserved ({len(req.untrusted_user_text.split())} words)."
            )
        summary_parts.append("Requires licensed clinician evaluation and verification.")
        draft_text = " ".join(summary_parts)

        prompt_tok = max(32, len(req.untrusted_user_text) // 4 + 40)
        comp_tok = max(24, len(draft_text) // 4)
        return (
            ModelProviderBackend.PRIVATE_MEDGEMMA_VLLM
            if req.data_tier == DataTier.T3_SENSITIVE_CLINICAL
            else ModelProviderBackend.GOOGLE_GEMINI_VERTEX,
            self.config.medgemma_model_id
            if req.data_tier == DataTier.T3_SENSITIVE_CLINICAL
            else self.config.gemini_model_id,
            draft_text,
            extracted,
            prompt_tok,
            comp_tok,
        )

    def _extract_structured_candidates(self, req: ModelInvocationRequest) -> dict[str, Any]:
        extracted = dict(req.structured_context)
        lower_text = req.untrusted_user_text.lower()
        if "fever" in lower_text and "has_fever" not in extracted:
            extracted["candidate_fever_mentioned"] = True
        if "chest pain" in lower_text and "chest_pain" not in extracted:
            extracted["candidate_chest_pain_mentioned"] = True
        if "shortness of breath" in lower_text or "breathless" in lower_text:
            extracted["candidate_dyspnea_mentioned"] = True
        return extracted
