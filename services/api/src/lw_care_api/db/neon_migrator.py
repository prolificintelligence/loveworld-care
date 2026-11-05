"""
Neon PostgreSQL Schema Migration, Immutability Trigger Installer & Write-Through Repository.

Handles:
1. Safe `asyncpg` URL normalization for Neon DB (`?sslmode=require&channel_binding=require`).
2. Creation of the 5 isolated schemas (`identity`, `care_clinical`, `finance_ledger`,
   `governance_audit`, `analytics`) and all SQLAlchemy 2.0 tables.
3. Installation of PostgreSQL append-only immutability triggers (`BEFORE UPDATE OR DELETE`)
   on `care_clinical.care_clinical_documents`, `care_clinical.care_clinical_addenda`,
   `finance_ledger.finance_ledger_entries`, and `governance_audit.audit_events`.
4. Idempotent baseline seeding of verified MDCN clinicians, active Nigeria protocol bundle
   (`LW-NG-GP-ADULT-V1`), staffed consultation slots, and SponsorCare pools (`NGN` & `ESP`).
"""

from __future__ import annotations

import ssl
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..domain.clinical_service import build_default_verified_ng_protocol_bundle
from .models import (
    POSTGRES_IMMUTABILITY_TRIGGER_STATEMENTS,
    POSTGRES_SCHEMA_AND_IMMUTABILITY_DDL_STATEMENTS,
    Base,
    CareEpisodeModel,
    ClinicalDocumentModel,
    ClinicianCredentialModel,
    EncounterEconomicsFactModel,
    EncounterModel,
    IntakeAnswerSetModel,
    ProtocolBundleModel,
    ProtocolRunModel,
    SponsorPoolModel,
    StaffedRosterSlotModel,
    UserIdentityModel,
)


def normalize_async_database_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    """
    Converts a standard `postgresql://...` Neon connection string into a SQLAlchemy
    `postgresql+asyncpg://...` URL with TLS enabled, stripping query params (`sslmode`,
    `channel_binding`) that `asyncpg.connect()` does not accept as keyword arguments.
    """
    url = raw_url.strip()
    if url.startswith("sqlite"):
        return url, {}

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parsed = urlparse(url)
    query_pairs = dict(parse_qsl(parsed.query))
    needs_ssl = query_pairs.pop("sslmode", None) in ("require", "verify-full", "verify-ca") or (
        "neon.tech" in (parsed.hostname or "")
    )
    query_pairs.pop("channel_binding", None)
    query_pairs.pop("ssl", None)

    clean_url = urlunparse(parsed._replace(query=urlencode(query_pairs)))
    connect_args: dict[str, Any] = {}
    if needs_ssl:
        ssl_ctx = ssl.create_default_context()
        connect_args["ssl"] = ssl_ctx
    return clean_url, connect_args


class NeonDatabaseManager:
    def __init__(self, database_url: str) -> None:
        self._raw_url = database_url
        self._is_postgres = database_url.strip().startswith(("postgres://", "postgresql"))
        clean_url, connect_args = normalize_async_database_url(database_url)
        self._engine: AsyncEngine | None = (
            create_async_engine(
                clean_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
            )
            if self._is_postgres
            else None
        )
        self._session_factory: async_sessionmaker[AsyncSession] | None = (
            async_sessionmaker(self._engine, expire_on_commit=False)
            if self._engine is not None
            else None
        )

    @property
    def is_postgres_configured(self) -> bool:
        return self._engine is not None and "REPLACE_" not in self._raw_url

    async def migrate_and_seed(self) -> dict[str, Any]:
        """
        Creates all 5 isolated schemas, tables, append-only immutability triggers,
        and idempotent baseline clinical/financial records in Neon PostgreSQL.
        """
        if not self.is_postgres_configured or self._engine is None or self._session_factory is None:
            return {"status": "SKIPPED_NON_POSTGRES"}

        async with self._engine.begin() as conn:
            for stmt in POSTGRES_SCHEMA_AND_IMMUTABILITY_DDL_STATEMENTS:
                await conn.execute(text(stmt))
            await conn.run_sync(Base.metadata.create_all)
            for trig_stmt in POSTGRES_IMMUTABILITY_TRIGGER_STATEMENTS:
                await conn.execute(text(trig_stmt))

        now = datetime.now(UTC)
        bundle = build_default_verified_ng_protocol_bundle()

        async with self._session_factory() as session, session.begin():
            # 1. Seed Verified MDCN Clinicians
            await session.execute(
                pg_insert(UserIdentityModel)
                .values(
                    [
                        {
                            "id": "dr-adebayo-okonkwo",
                            "email": "adebayo.okonkwo@care.loveworld.org",
                            "phone_e164": "+2348030004421",
                            "full_name": "Dr. Adebayo Okonkwo",
                            "password_hash": "argon2id$verified$clinical_lead",
                            "roles_json": ["CLINICIAN_GP", "CLINICAL_GOVERNANCE_LEAD"],
                            "mfa_enabled": True,
                            "jurisdiction": "NG",
                            "is_active": True,
                        },
                        {
                            "id": "dr-chidinma-eze",
                            "email": "chidinma.eze@care.loveworld.org",
                            "phone_e164": "+2348030003890",
                            "full_name": "Dr. Chidinma Eze",
                            "password_hash": "argon2id$verified$clinical_reviewer",
                            "roles_json": ["CLINICIAN_SPECIALIST", "CLINICAL_GOVERNANCE_LEAD"],
                            "mfa_enabled": True,
                            "jurisdiction": "NG",
                            "is_active": True,
                        },
                    ]
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )

            await session.execute(
                pg_insert(ClinicianCredentialModel)
                .values(
                    [
                        {
                            "clinician_id": "dr-adebayo-okonkwo",
                            "mdcn_licence_number": "MDCN/R/44210",
                            "specialty": "General Practice",
                            "jurisdiction": "NG",
                            "lifecycle_status": "APPROVED_ACTIVE",
                            "licence_expires_at": now + timedelta(days=365),
                            "indemnity_verified": True,
                            "verified_by_actor_id": "clinical-governance-directorate",
                        },
                        {
                            "clinician_id": "dr-chidinma-eze",
                            "mdcn_licence_number": "MDCN/R/38901",
                            "specialty": "Internal Medicine / SpecialistBridge",
                            "jurisdiction": "NG",
                            "lifecycle_status": "APPROVED_ACTIVE",
                            "licence_expires_at": now + timedelta(days=365),
                            "indemnity_verified": True,
                            "verified_by_actor_id": "clinical-governance-directorate",
                        },
                    ]
                )
                .on_conflict_do_nothing(index_elements=["clinician_id"])
            )

            # 2. Seed Active Dual-Signed Protocol Bundle (LW-NG-GP-ADULT-V1)
            await session.execute(
                pg_insert(ProtocolBundleModel)
                .values(
                    {
                        "bundle_id": bundle.bundle_id,
                        "semver": bundle.semver,
                        "jurisdiction": bundle.jurisdiction,
                        "population": bundle.population,
                        "status": bundle.status.value,
                        "clinical_owner": bundle.clinical_owner or "dr-adebayo-okonkwo",
                        "reviewers_json": bundle.reviewers,
                        "document_hash": bundle.document_hash,
                        "bundle_payload_json": bundle.model_dump(mode="json"),
                    }
                )
                .on_conflict_do_nothing(index_elements=["bundle_id"])
            )

            # 3. Seed Verified Staffed Slots
            await session.execute(
                pg_insert(StaffedRosterSlotModel)
                .values(
                    [
                        {
                            "slot_id": "slot-ng-gp-001",
                            "clinician_id": "dr-adebayo-okonkwo",
                            "clinician_display_name": "Dr. Adebayo Okonkwo (GP · MDCN/R/44210)",
                            "clinician_mdcn_licence": "MDCN/R/44210",
                            "specialty": "GP",
                            "jurisdiction": "NG",
                            "starts_at": now + timedelta(minutes=15),
                            "ends_at": now + timedelta(days=30),
                            "supported_modalities_json": [
                                "VIDEO",
                                "AUDIO_FALLBACK",
                                "ASYNC_CLINICAL_MESSAGING",
                            ],
                            "fee_minor": 600_000,
                            "currency": "NGN",
                            "is_booked": False,
                            "staffing_verified": True,
                        },
                        {
                            "slot_id": "slot-ng-spec-002",
                            "clinician_id": "dr-chidinma-eze",
                            "clinician_display_name": "Dr. Chidinma Eze (SpecialistBridge · MDCN/R/38901)",
                            "clinician_mdcn_licence": "MDCN/R/38901",
                            "specialty": "SPECIALIST_INTERNAL_MEDICINE",
                            "jurisdiction": "NG",
                            "starts_at": now + timedelta(minutes=30),
                            "ends_at": now + timedelta(days=30),
                            "supported_modalities_json": ["VIDEO", "AUDIO_FALLBACK"],
                            "fee_minor": 1_200_000,
                            "currency": "NGN",
                            "is_booked": False,
                            "staffing_verified": True,
                        },
                    ]
                )
                .on_conflict_do_nothing(index_elements=["slot_id"])
            )

            # 4. Seed SponsorCare Pools (NGN Medicaid Pool & ESP Espees Global Pool)
            await session.execute(
                pg_insert(SponsorPoolModel)
                .values(
                    [
                        {
                            "agreement_id": "AGR-LW-MEDICAID-NG-2026",
                            "sponsor_id": "sponsor-loveworld-medicaid",
                            "sponsor_name": "LoveWorld Medicaid Humanitarian Care Pool (NGN)",
                            "funding_type": "SPONSOR_DEFINED_SERVICES",
                            "currency": "NGN",
                            "committed_unfunded_minor": 500_000_000,
                            "funded_cash_minor": 1_200_000_000,
                            "active_reserved_minor": 0,
                            "redeemed_minor": 0,
                            "eligible_beneficiary_count": 24,
                            "version": 1,
                        },
                        {
                            "agreement_id": "AGR-LW-ESPEES-PARTNERS-2026",
                            "sponsor_id": "sponsor-loveworld-partners-esp",
                            "sponsor_name": "LoveWorld Partners Espees Care Pool (ESP)",
                            "funding_type": "SPONSOR_DEFINED_SERVICES",
                            "currency": "ESP",
                            "committed_unfunded_minor": 100_000,
                            "funded_cash_minor": 500_000,
                            "active_reserved_minor": 0,
                            "redeemed_minor": 0,
                            "eligible_beneficiary_count": 50,
                            "version": 1,
                        },
                    ]
                )
                .on_conflict_do_nothing(index_elements=["agreement_id"])
            )

        return await self.get_health_summary()

    async def get_health_summary(self) -> dict[str, Any]:
        if not self.is_postgres_configured or self._session_factory is None:
            return {"connected": False, "engine": "in-memory-fallback"}

        try:
            async with self._session_factory() as session:
                schemas_res = await session.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name IN ('identity','care_clinical','finance_ledger','governance_audit','analytics') "
                        "ORDER BY schema_name"
                    )
                )
                schemas = [r[0] for r in schemas_res.fetchall()]

                triggers_res = await session.execute(
                    text(
                        "SELECT trigger_name FROM information_schema.triggers "
                        "WHERE trigger_name LIKE 'trg_immutable_%' ORDER BY trigger_name"
                    )
                )
                triggers = sorted({r[0] for r in triggers_res.fetchall()})

                ep_count = await session.scalar(select(func.count()).select_from(CareEpisodeModel))
                enc_count = await session.scalar(select(func.count()).select_from(EncounterModel))
                doc_count = await session.scalar(
                    select(func.count()).select_from(ClinicalDocumentModel)
                )
                pool_count = await session.scalar(
                    select(func.count()).select_from(SponsorPoolModel)
                )
                clinician_count = await session.scalar(
                    select(func.count()).select_from(ClinicianCredentialModel)
                )

                return {
                    "connected": True,
                    "engine": "neon-postgresql-serverless",
                    "isolated_schemas": schemas,
                    "immutability_triggers": triggers,
                    "counts": {
                        "verified_clinicians": int(clinician_count or 0),
                        "sponsor_pools": int(pool_count or 0),
                        "care_episodes": int(ep_count or 0),
                        "encounters": int(enc_count or 0),
                        "signed_clinical_documents": int(doc_count or 0),
                    },
                }
        except (SQLAlchemyError, OSError, TimeoutError) as exc:
            return {"connected": False, "error_type": type(exc).__name__}

    async def persist_episode(self, ep: Any) -> None:
        if not self.is_postgres_configured or self._session_factory is None:
            return
        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(
                    pg_insert(CareEpisodeModel)
                    .values(
                        {
                            "id": ep.episode_id,
                            "patient_id": ep.patient_id,
                            "acting_proxy_grant_id": ep.acting_proxy_grant_id,
                            "consent_grant_id": ep.consent_grant_id,
                            "care_service": ep.care_service,
                            "jurisdiction": ep.jurisdiction,
                            "state": ep.state,
                            "chief_complaint_summary": ep.chief_complaint_summary,
                            "assigned_clinician_id": ep.assigned_clinician_id,
                            "active_protocol_outcome": ep.active_protocol_outcome,
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
        except (SQLAlchemyError, OSError, TimeoutError):
            raise RuntimeError("Clinical database write failed") from None

    async def persist_intake_and_protocol_run(
        self,
        *,
        episode_id: str,
        intake_id: str,
        revision: int,
        structured_answers: dict[str, Any],
        raw_patient_statement: str,
        ai_draft: dict[str, Any] | None,
        actor_id: str,
        proto_res: Any,
    ) -> None:
        if not self.is_postgres_configured or self._session_factory is None:
            return
        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(
                    pg_insert(IntakeAnswerSetModel)
                    .values(
                        {
                            "id": intake_id,
                            "episode_id": episode_id,
                            "revision": revision,
                            "structured_answers_json": structured_answers,
                            "raw_patient_statement": raw_patient_statement,
                            "language_code": "en-NG",
                            "ai_draft_json": ai_draft,
                            "submitted_by_actor_id": actor_id,
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                await session.execute(
                    pg_insert(ProtocolRunModel)
                    .values(
                        {
                            "id": proto_res.protocol_run_id,
                            "episode_id": episode_id,
                            "intake_id": intake_id,
                            "protocol_bundle_id": proto_res.protocol_bundle_id,
                            "protocol_version": proto_res.protocol_version,
                            "protocol_document_hash": proto_res.protocol_document_hash,
                            "outcome_type": proto_res.outcome_type.value,
                            "hard_stop_triggered": proto_res.hard_stop_triggered,
                            "executed_rule_ids_json": proto_res.executed_rule_ids,
                            "fired_rule_ids_json": proto_res.fired_rule_ids,
                            "unresolved_fields_json": proto_res.unresolved_fields,
                            "approved_content_id": proto_res.approved_content_id,
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
        except (SQLAlchemyError, OSError, TimeoutError):
            raise RuntimeError("Clinical database write failed") from None

    async def persist_signed_encounter(
        self,
        *,
        encounter_id: str,
        episode_id: str,
        patient_id: str,
        clinician_id: str,
        clinician_mdcn: str,
        modality_used: str,
        modality_limitations_noted: str,
        history_and_findings: str,
        clinical_assessment: str,
        management_plan: str,
        safety_net_instructions: str,
        prescriptions: list[dict[str, Any]],
        document_sha256: str,
        signature_ed25519_base64: str,
        signed_at: datetime,
    ) -> None:
        if not self.is_postgres_configured or self._session_factory is None:
            return
        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(
                    pg_insert(EncounterModel)
                    .values(
                        {
                            "id": encounter_id,
                            "episode_id": episode_id,
                            "patient_id": patient_id,
                            "clinician_id": clinician_id,
                            "status": "SIGNED",
                            "modality": modality_used,
                            "version": 3,
                            "remote_suitability_accepted": True,
                            "signed_at": signed_at,
                            "signed_document_hash": document_sha256,
                            "signature_ed25519_base64": signature_ed25519_base64,
                        }
                    )
                    .on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            "status": "SIGNED",
                            "signed_at": signed_at,
                            "signed_document_hash": document_sha256,
                            "signature_ed25519_base64": signature_ed25519_base64,
                        },
                    )
                )
                await session.execute(
                    pg_insert(ClinicalDocumentModel)
                    .values(
                        {
                            "id": f"doc-{encounter_id}",
                            "encounter_id": encounter_id,
                            "patient_id": patient_id,
                            "author_clinician_id": clinician_id,
                            "author_mdcn_licence": clinician_mdcn,
                            "modality_used": modality_used,
                            "modality_limitations_noted": modality_limitations_noted,
                            "history_and_findings": history_and_findings,
                            "clinical_assessment": clinical_assessment,
                            "management_plan": management_plan,
                            "safety_net_instructions": safety_net_instructions,
                            "prescriptions_json": prescriptions,
                            "document_sha256": document_sha256,
                            "signature_ed25519_base64": signature_ed25519_base64,
                            "signed_at": signed_at,
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                await session.execute(
                    pg_insert(EncounterEconomicsFactModel)
                    .values(
                        {
                            "encounter_id": encounter_id,
                            "payer_cohort": "SPONSOR_DEFINED_SERVICES",
                            "currency": "NGN",
                            "recognised_revenue_minor": 600_000,
                            "clinician_direct_cost_minor": 330_000,
                            "total_variable_cost_minor": 425_000,
                            "contribution_margin_minor": 175_000,
                        }
                    )
                    .on_conflict_do_nothing(index_elements=["encounter_id"])
                )
        except (SQLAlchemyError, OSError, TimeoutError):
            raise RuntimeError("Clinical database write failed") from None
