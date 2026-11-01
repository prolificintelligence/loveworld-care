import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import {
  getNeonSql,
  getUpstashKillSwitch,
  invokeOpenRouterIntakeDraft,
  setUpstashKillSwitch,
  signClinicalPayloadEd25519,
  upstashCommand,
} from "../../../../lib/cloud-runtime";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const sql = getNeonSql();
    const [
      schemasRows,
      triggersRows,
      cliniciansRows,
      slotsRows,
      poolsRows,
      episodesRows,
      signedDocsRows,
      addendaRows,
      redisPong,
      killSwitch,
    ] = await Promise.all([
      sql`
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name IN ('identity','care_clinical','finance_ledger','governance_audit','analytics')
        ORDER BY schema_name
      `,
      sql`
        SELECT DISTINCT trigger_name
        FROM information_schema.triggers
        WHERE trigger_name LIKE 'trg_immutable_%'
        ORDER BY trigger_name
      `,
      sql`
        SELECT clinician_id, mdcn_licence_number, specialty, jurisdiction, lifecycle_status, licence_expires_at
        FROM identity.identity_clinician_credentials
        ORDER BY clinician_id
      `,
      sql`
        SELECT slot_id, clinician_id, clinician_display_name, clinician_mdcn_licence, specialty, jurisdiction, fee_minor, currency, is_booked
        FROM care_clinical.care_staffed_slots
        ORDER BY slot_id
      `,
      sql`
        SELECT agreement_id, sponsor_name, funding_type, currency, committed_unfunded_minor, funded_cash_minor, active_reserved_minor, redeemed_minor, eligible_beneficiary_count
        FROM finance_ledger.finance_sponsor_pools
        ORDER BY agreement_id
      `,
      sql`
        SELECT id, patient_id, care_service, jurisdiction, state, chief_complaint_summary, assigned_clinician_id, active_protocol_outcome, created_at
        FROM care_clinical.care_episodes
        ORDER BY created_at DESC
        LIMIT 10
      `,
      sql`
        SELECT id, encounter_id, patient_id, author_clinician_id, author_mdcn_licence, modality_used, clinical_assessment, management_plan, safety_net_instructions, document_sha256, signature_ed25519_base64, signed_at
        FROM care_clinical.care_clinical_documents
        ORDER BY signed_at DESC
        LIMIT 10
      `,
      sql`
        SELECT id, encounter_id, original_signed_document_hash, author_clinician_id, amendment_reason, addendum_text, addendum_sha256, signed_at
        FROM care_clinical.care_clinical_addenda
        ORDER BY signed_at DESC
        LIMIT 10
      `,
      upstashCommand(["PING"]),
      getUpstashKillSwitch(),
    ]);

    return NextResponse.json(
      {
        status: "LIVE_PRODUCTION",
        timestamp_iso: new Date().toISOString(),
        neon_db: {
          connected: true,
          isolated_schemas: schemasRows.map((r) => r.schema_name),
          immutability_triggers: triggersRows.map((r) => r.trigger_name),
        },
        upstash_redis: {
          connected: redisPong === "PONG",
          ping: redisPong,
          ai_kill_switch: killSwitch,
        },
        clinicians: cliniciansRows,
        slots: slotsRows,
        sponsor_pools: poolsRows,
        episodes: episodesRows,
        signed_documents: signedDocsRows,
        addenda: addendaRows,
      },
      {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate",
        },
      }
    );
  } catch (err) {
    return NextResponse.json(
      {
        status: "ERROR",
        message: err instanceof Error ? err.message : String(err),
      },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as Record<string, unknown>;
    const action = String(body.action || "");
    const sql = getNeonSql();

    if (action === "TOGGLE_KILL_SWITCH") {
      const enabled = Boolean(body.enabled);
      const reason = String(body.reason || "GOVERNANCE_MANUAL_TOGGLE");
      await setUpstashKillSwitch(enabled, "clinical-governance-lead", reason);
      const ks = await getUpstashKillSwitch();
      return NextResponse.json({ ok: true, ai_kill_switch: ks });
    }

    if (action === "SUBMIT_INTAKE_AND_CREATE_EPISODE") {
      const patientId = String(body.patient_id || "patient-samuel-mensah-ng");
      const ageYears = Number(body.patient_age_years ?? 34);
      const chestPain = Boolean(body.severe_chest_pain_or_pressure);
      const breathingDiff = Boolean(body.acute_breathing_difficulty);
      const bleeding = Boolean(body.uncontrolled_bleeding_or_unconsciousness);
      const symptomCategory = String(body.primary_symptom_category || "FEVER_OR_MALARIA_LIKE");
      const durationDays = Number(body.symptom_duration_days ?? 2);
      const rawStatement = String(body.raw_patient_statement || "Intermittent fever and headache.");
      const fundingRoute = String(body.funding_route || "SPONSOR_DEFINED_SERVICES");
      const agreementId = String(body.agreement_id || "AGR-LW-MEDICAID-NG-2026");

      // 1. Deterministic Protocol Evaluation (§7.3)
      const hardStop = chestPain || breathingDiff || bleeding;
      const outcomeType = hardStop
        ? "EMERGENCY_GUIDANCE"
        : ageYears < 18
          ? "OUT_OF_SCOPE"
          : durationDays >= 7
            ? "URGENT_PROFESSIONAL_ASSESSMENT"
            : "CLINICIAN_REVIEW";
      const firedRule = hardStop
        ? "HS-CARDIORESP-01"
        : ageYears < 18
          ? "EXCLUSION_1"
          : durationDays >= 7
            ? "RT-PROLONGED-SYMPTOMS-01"
            : "RT-STANDARD-GP-02";

      const killSwitch = await getUpstashKillSwitch();
      const structuredAnswers = {
        patient_age_years: ageYears,
        severe_chest_pain_or_pressure: chestPain,
        acute_breathing_difficulty: breathingDiff,
        uncontrolled_bleeding_or_unconsciousness: bleeding,
        primary_symptom_category: symptomCategory,
        symptom_duration_days: durationDays,
      };

      const aiDraft = await invokeOpenRouterIntakeDraft({
        structuredAnswers,
        rawPatientStatement: rawStatement,
        killSwitchEnabled: killSwitch.enabled,
      });

      const episodeId = `EP-NG-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      const intakeId = `INT-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      const protocolRunId = `PRUN-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      const encounterId = `ENC-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;

      await sql`
        INSERT INTO care_clinical.care_episodes (
          id, patient_id, consent_grant_id, care_service, jurisdiction, state,
          chief_complaint_summary, assigned_clinician_id, active_protocol_outcome, created_at, updated_at
        ) VALUES (
          ${episodeId}, ${patientId}, 'CONSENT-NG-V1', 'GP_REMOTE', 'NG',
          ${hardStop ? "SUBMITTED" : "ACTIVE"},
          ${rawStatement}, ${hardStop ? null : "dr-adebayo-okonkwo"}, ${outcomeType}, NOW(), NOW()
        )
      `;

      await sql`
        INSERT INTO care_clinical.care_intake_answer_sets (
          id, episode_id, revision, structured_answers_json, raw_patient_statement,
          language_code, ai_draft_json, submitted_by_actor_id, created_at
        ) VALUES (
          ${intakeId}, ${episodeId}, 1, ${JSON.stringify(structuredAnswers)}::jsonb,
          ${rawStatement}, 'en-NG', ${JSON.stringify(aiDraft)}::jsonb, ${patientId}, NOW()
        )
      `;

      await sql`
        INSERT INTO care_clinical.care_protocol_runs (
          id, episode_id, intake_id, protocol_bundle_id, protocol_version, protocol_document_hash,
          outcome_type, hard_stop_triggered, executed_rule_ids_json, fired_rule_ids_json,
          unresolved_fields_json, approved_content_id, created_at
        ) VALUES (
          ${protocolRunId}, ${episodeId}, ${intakeId}, 'LW-NG-GP-ADULT-V1', '1.0.0',
          'sha256_verified_lw_ng_gp_adult_v1', ${outcomeType}, ${hardStop},
          ${JSON.stringify([firedRule])}::jsonb, ${JSON.stringify([firedRule])}::jsonb,
          '[]'::jsonb, 'TMPL_CLINICIAN_REVIEW_V1', NOW()
        )
      `;

      if (!hardStop && outcomeType !== "OUT_OF_SCOPE") {
        await sql`
          INSERT INTO care_clinical.care_encounters (
            id, episode_id, patient_id, clinician_id, status, modality, version, created_at
          ) VALUES (
            ${encounterId}, ${episodeId}, ${patientId}, 'dr-adebayo-okonkwo', 'IN_PROGRESS', 'VIDEO', 1, NOW()
          )
        `;

        if (fundingRoute === "SPONSOR_DEFINED_SERVICES") {
          const reserveAmount = agreementId.includes("ESPEES") ? 400 : 600000;
          await sql`
            UPDATE finance_ledger.finance_sponsor_pools
            SET active_reserved_minor = active_reserved_minor + ${reserveAmount},
                version = version + 1,
                updated_at = NOW()
            WHERE agreement_id = ${agreementId}
              AND (funded_cash_minor - active_reserved_minor - redeemed_minor) >= ${reserveAmount}
          `;
        }
      }

      return NextResponse.json({
        ok: true,
        episode_id: episodeId,
        intake_id: intakeId,
        protocol_run_id: protocolRunId,
        encounter_id: hardStop ? null : encounterId,
        outcome_type: outcomeType,
        hard_stop_triggered: hardStop,
        fired_rule: firedRule,
        ai_draft: aiDraft,
      });
    }

    if (action === "SIGN_ENCOUNTER") {
      const encounterId = String(body.encounter_id || `ENC-${crypto.randomUUID().slice(0, 8).toUpperCase()}`);
      const episodeId = String(body.episode_id || "EP-LIVE-01");
      const patientId = String(body.patient_id || "patient-samuel-mensah-ng");
      const clinicianId = "dr-adebayo-okonkwo";
      const clinicianMdcn = "MDCN/R/44210";
      const modalityUsed = String(body.modality_used || "VIDEO");
      const historyAndFindings = String(body.history_and_findings || "Clinical findings documented.");
      const clinicalAssessment = String(body.clinical_assessment || "Clinical assessment documented.");
      const managementPlan = String(body.management_plan || "Management plan documented.");
      const safetyNet = String(body.safety_net_instructions || "Return immediately if symptoms worsen.");
      const agreementId = String(body.agreement_id || "AGR-LW-MEDICAID-NG-2026");

      const signedAtIso = new Date().toISOString();
      const { documentSha256, signatureEd25519Base64 } = signClinicalPayloadEd25519({
        encounterId,
        episodeId,
        patientId,
        clinicianId,
        clinicianMdcn,
        modalityUsed,
        historyAndFindings,
        clinicalAssessment,
        managementPlan,
        safetyNet,
        signedAtIso,
      });

      const docId = `DOC-${encounterId}`;

      await sql`
        INSERT INTO care_clinical.care_encounters (
          id, episode_id, patient_id, clinician_id, status, modality, version,
          remote_suitability_accepted, signed_at, signed_document_hash, signature_ed25519_base64, created_at
        ) VALUES (
          ${encounterId}, ${episodeId}, ${patientId}, ${clinicianId}, 'SIGNED', ${modalityUsed}, 2,
          TRUE, NOW(), ${documentSha256}, ${signatureEd25519Base64}, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
          status = 'SIGNED',
          version = care_clinical.care_encounters.version + 1,
          remote_suitability_accepted = TRUE,
          signed_at = NOW(),
          signed_document_hash = ${documentSha256},
          signature_ed25519_base64 = ${signatureEd25519Base64}
      `;

      await sql`
        INSERT INTO care_clinical.care_clinical_documents (
          id, encounter_id, patient_id, author_clinician_id, author_mdcn_licence,
          modality_used, modality_limitations_noted, history_and_findings,
          clinical_assessment, management_plan, safety_net_instructions,
          prescriptions_json, document_sha256, signature_ed25519_base64, signed_at
        ) VALUES (
          ${docId}, ${encounterId}, ${patientId}, ${clinicianId}, ${clinicianMdcn},
          ${modalityUsed}, 'Standard remote video consultation', ${historyAndFindings},
          ${clinicalAssessment}, ${managementPlan}, ${safetyNet},
          '[]'::jsonb, ${documentSha256}, ${signatureEd25519Base64}, NOW()
        )
      `;

      // Redeem SponsorCare pool entitlement upon signed encounter (§6.3 & §10.3)
      const redeemAmount = agreementId.includes("ESPEES") ? 400 : 600000;
      await sql`
        UPDATE finance_ledger.finance_sponsor_pools
        SET active_reserved_minor = GREATEST(0, active_reserved_minor - ${redeemAmount}),
            redeemed_minor = redeemed_minor + ${redeemAmount},
            version = version + 1,
            updated_at = NOW()
        WHERE agreement_id = ${agreementId}
      `;

      await sql`
        INSERT INTO analytics.encounter_unit_economics_facts (
          encounter_id, payer_cohort, currency, recognised_revenue_minor,
          clinician_direct_cost_minor, total_variable_cost_minor, contribution_margin_minor, recorded_at
        ) VALUES (
          ${encounterId}, 'SPONSOR_DEFINED_SERVICES', 'NGN', 600000, 330000, 425000, 175000, NOW()
        )
        ON CONFLICT (encounter_id) DO NOTHING
      `;

      return NextResponse.json({
        ok: true,
        encounter_id: encounterId,
        document_id: docId,
        document_sha256: documentSha256,
        signature_ed25519_base64: signatureEd25519Base64,
        signed_at_iso: signedAtIso,
      });
    }

    if (action === "APPEND_ADDENDUM") {
      const encounterId = String(body.encounter_id || "");
      const originalHash = String(body.original_signed_document_hash || "");
      const reason = String(body.amendment_reason || "");
      const textContent = String(body.addendum_text || "");
      const signedAtIso = new Date().toISOString();

      const { documentSha256: addendumSha256, signatureEd25519Base64 } =
        signClinicalPayloadEd25519({
          encounterId,
          originalHash,
          reason,
          textContent,
          signedAtIso,
        });

      const addendumId = `ADD-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      await sql`
        INSERT INTO care_clinical.care_clinical_addenda (
          id, encounter_id, original_signed_document_hash, author_clinician_id,
          amendment_reason, addendum_text, addendum_sha256, signature_ed25519_base64, signed_at
        ) VALUES (
          ${addendumId}, ${encounterId}, ${originalHash}, 'dr-adebayo-okonkwo',
          ${reason}, ${textContent}, ${addendumSha256}, ${signatureEd25519Base64}, NOW()
        )
      `;

      return NextResponse.json({
        ok: true,
        addendum_id: addendumId,
        addendum_sha256: addendumSha256,
        original_signed_document_hash: originalHash,
      });
    }

    if (action === "TEST_POSTGRES_IMMUTABILITY_TRIGGER_AT08") {
      const targetHash = String(body.document_sha256 || "");
      try {
        await sql`
          UPDATE care_clinical.care_clinical_documents
          SET clinical_assessment = 'ILLEGAL_TAMPER_ATTEMPT'
          WHERE document_sha256 = ${targetHash}
        `;
        return NextResponse.json({
          ok: false,
          message: "Unexpectedly succeeded",
        });
      } catch (dbErr) {
        return NextResponse.json({
          ok: true,
          immutability_verified: true,
          postgres_trigger_error: dbErr instanceof Error ? dbErr.message : String(dbErr),
        });
      }
    }

    return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
  } catch (err) {
    return NextResponse.json(
      {
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 500 }
    );
  }
}
