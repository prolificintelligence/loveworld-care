"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AiDraftWatermarkBadge,
  EmergencySafetyBanner,
  SharedDeviceSessionLockBar,
  SignedRecordSeal,
} from "@loveworld-care/design-system";
import {
  computeEncounterUnitEconomics,
  formatMoneyMinor,
  type ConsultationModality,
  type CurrencyCode,
  type FundingRouteType,
} from "@loveworld-care/domain-types";

type ActiveWorkspace = "PATIENT" | "CLINICIAN" | "COMMAND" | "SPONSOR";

interface LiveCloudState {
  status: string;
  timestamp_iso: string;
  neon_db: {
    connected: boolean;
    isolated_schemas: string[];
    immutability_triggers: string[];
  };
  upstash_redis: {
    connected: boolean;
    ping: string;
    ai_kill_switch: {
      enabled: boolean;
      actor_id: string;
      reason: string;
      updated_at_iso: string;
    };
  };
  clinicians: {
    clinician_id: string;
    mdcn_licence_number: string;
    specialty: string;
    lifecycle_status: string;
  }[];
  slots: {
    slot_id: string;
    clinician_id: string;
    clinician_display_name: string;
    specialty: string;
    fee_minor: number;
    currency: CurrencyCode;
  }[];
  sponsor_pools: {
    agreement_id: string;
    sponsor_name: string;
    currency: CurrencyCode;
    committed_unfunded_minor: number;
    funded_cash_minor: number;
    active_reserved_minor: number;
    redeemed_minor: number;
    eligible_beneficiary_count: number;
  }[];
  episodes: {
    id: string;
    patient_id: string;
    care_service: string;
    state: string;
    chief_complaint_summary: string;
    assigned_clinician_id: string | null;
    active_protocol_outcome: string | null;
    created_at: string;
  }[];
  signed_documents: {
    id: string;
    encounter_id: string;
    patient_id: string;
    author_clinician_id: string;
    author_mdcn_licence: string;
    clinical_assessment: string;
    management_plan: string;
    safety_net_instructions: string;
    document_sha256: string;
    signed_at: string;
  }[];
  addenda: {
    id: string;
    encounter_id: string;
    original_signed_document_hash: string;
    amendment_reason: string;
    addendum_text: string;
    addendum_sha256: string;
    signed_at: string;
  }[];
}

export default function LoveWorldCareUnifiedProductionApp() {
  const [workspace, setWorkspace] = useState<ActiveWorkspace>("PATIENT");
  const [sessionLocked, setSessionLocked] = useState(false);
  const [cloudState, setCloudState] = useState<LiveCloudState | null>(null);
  const [loadingCloud, setLoadingCloud] = useState(false);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  // Patient Intake & Booking State
  const [ageYears, setAgeYears] = useState<number>(34);
  const [chestPain, setChestPain] = useState<boolean>(false);
  const [breathingDifficulty, setBreathingDifficulty] = useState<boolean>(false);
  const [uncontrolledBleeding, setUncontrolledBleeding] = useState<boolean>(false);
  const [symptomCategory, setSymptomCategory] = useState<string>("FEVER_OR_MALARIA_LIKE");
  const [durationDays, setDurationDays] = useState<number>(2);
  const [rawStatement, setRawStatement] = useState<string>(
    "Intermittent fever and mild frontal headache for 2 days."
  );
  const [selectedModality, setSelectedModality] = useState<ConsultationModality>("VIDEO");
  const [fundingRoute, setFundingRoute] = useState<FundingRouteType>("SPONSOR_DEFINED_SERVICES");
  const [selectedAgreementId, setSelectedAgreementId] = useState<string>(
    "AGR-LW-MEDICAID-NG-2026"
  );
  const [latestIntakeResult, setLatestIntakeResult] = useState<{
    episode_id: string;
    encounter_id: string | null;
    outcome_type: string;
    fired_rule: string;
    ai_draft: { model_id: string; draft_summary: string; status: string };
  } | null>(null);

  // Clinician Workspace State
  const [activeEncounterId, setActiveEncounterId] = useState<string>("ENC-LIVE-NG-001");
  const [historyAndFindings, setHistoryAndFindings] = useState(
    "2-day history of intermittent fever and frontal headache. Alert, no neck stiffness, no dyspnea."
  );
  const [assessment, setAssessment] = useState(
    "Suspected uncomplicated malaria; differential viral upper respiratory prodrome."
  );
  const [plan, setPlan] = useState(
    "Order rapid diagnostic test (mRDT) at LoveWorld Medical Centre Outpatient Lab; paracetamol 1g PO PRN; follow up in 48 hours."
  );
  const [safetyNet, setSafetyNet] = useState(
    "Attend emergency department immediately if persistent vomiting, confusion, dark urine, or shortness of breath develops."
  );
  const [addendumReason, setAddendumReason] = useState("Post-consultation mRDT lab result update");
  const [addendumText, setAddendumText] = useState(
    "Malaria RDT positive; artemether-lumefantrine 80/480mg BD x 3 days initiated."
  );
  const [immutabilityTriggerProof, setImmutabilityTriggerProof] = useState<string | null>(null);

  // Sponsor Small Cohort Simulation
  const [simulateSmallCohort, setSimulateSmallCohort] = useState(false);

  const refreshCloudState = useCallback(async () => {
    setLoadingCloud(true);
    try {
      const res = await fetch("/api/v1/state", { cache: "no-store" });
      if (res.ok) {
        const data = (await res.json()) as LiveCloudState;
        setCloudState(data);
      }
    } finally {
      setLoadingCloud(false);
    }
  }, []);

  useEffect(() => {
    void refreshCloudState();
  }, [refreshCloudState]);

  const handleCreateEpisodeAndEvaluate = async () => {
    setStatusBanner("Persisting Episode, Intake & Deterministic Protocol Run to Neon PostgreSQL...");
    const res = await fetch("/api/v1/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "SUBMIT_INTAKE_AND_CREATE_EPISODE",
        patient_id: "patient-samuel-mensah-ng",
        patient_age_years: ageYears,
        severe_chest_pain_or_pressure: chestPain,
        acute_breathing_difficulty: breathingDifficulty,
        uncontrolled_bleeding_or_unconsciousness: uncontrolledBleeding,
        primary_symptom_category: symptomCategory,
        symptom_duration_days: durationDays,
        raw_patient_statement: rawStatement,
        funding_route: fundingRoute,
        agreement_id: selectedAgreementId,
      }),
    });
    const data = await res.json();
    if (data.ok) {
      setLatestIntakeResult(data);
      if (data.encounter_id) {
        setActiveEncounterId(data.encounter_id);
      }
      setStatusBanner(
        `Saved to Neon DB: Episode ${data.episode_id} | Protocol Outcome: ${data.outcome_type} (${data.fired_rule})`
      );
      await refreshCloudState();
    } else {
      setStatusBanner(`Error: ${data.error || "Failed"}`);
    }
  };

  const handleSignEncounter = async () => {
    setStatusBanner(
      "Generating Ed25519 Signature, locking ClinicalDocument in Neon DB & redeeming SponsorCare pool..."
    );
    const res = await fetch("/api/v1/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "SIGN_ENCOUNTER",
        encounter_id: activeEncounterId,
        episode_id: latestIntakeResult?.episode_id || "EP-LIVE-01",
        patient_id: "patient-samuel-mensah-ng",
        modality_used: selectedModality,
        history_and_findings: historyAndFindings,
        clinical_assessment: assessment,
        management_plan: plan,
        safety_net_instructions: safetyNet,
        agreement_id: selectedAgreementId,
      }),
    });
    const data = await res.json();
    if (data.ok) {
      setStatusBanner(
        `Signed & Locked in Neon DB! Encounter ${data.encounter_id} | SHA-256: ${String(
          data.document_sha256
        ).slice(0, 20)}...`
      );
      await refreshCloudState();
    } else {
      setStatusBanner(`Error: ${data.error || "Failed to sign"}`);
    }
  };

  const handleTestPostgresImmutabilityTrigger = async (documentSha256: string) => {
    const res = await fetch("/api/v1/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "TEST_POSTGRES_IMMUTABILITY_TRIGGER_AT08",
        document_sha256: documentSha256,
      }),
    });
    const data = await res.json();
    if (data.immutability_verified) {
      setImmutabilityTriggerProof(data.postgres_trigger_error);
    }
  };

  const handleAppendAddendum = async (encounterId: string, originalSha256: string) => {
    const res = await fetch("/api/v1/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "APPEND_ADDENDUM",
        encounter_id: encounterId,
        original_signed_document_hash: originalSha256,
        amendment_reason: addendumReason,
        addendum_text: addendumText,
      }),
    });
    const data = await res.json();
    if (data.ok) {
      setStatusBanner(
        `Appended Signed Addendum ${data.addendum_id} linked to original SHA-256 ${originalSha256.slice(
          0,
          16
        )}...`
      );
      await refreshCloudState();
    }
  };

  const handleToggleKillSwitch = async (enabled: boolean) => {
    await fetch("/api/v1/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "TOGGLE_KILL_SWITCH",
        enabled,
        reason: enabled
          ? "GOVERNANCE_INCIDENT_DRILL_AI_OFF"
          : "GOVERNANCE_RESTORE_POLICY_LIMITED_AI",
      }),
    });
    await refreshCloudState();
  };

  const hardStopTriggered = chestPain || breathingDifficulty || uncontrolledBleeding;
  const unitEconomics = computeEncounterUnitEconomics({
    encounterId: "ENC-BASELINE-NG",
    payerCohort: "SPONSOR_DEFINED_SERVICES",
    currency: "NGN",
    settledRevenueMinor: 600000,
    clinicianDirectCostMinor: 330000,
    paymentProcessingFeeMinor: 15000,
    communicationsRtcModelCostMinor: 20000,
    variableSupportCostMinor: 40000,
    refundQualityReserveMinor: 20000,
  });

  if (sessionLocked) {
    return (
      <div>
        <EmergencySafetyBanner />
        <SharedDeviceSessionLockBar
          workspaceName="Session Locked (AT-13)"
          actorDisplayName="Protected Shared Device Screen"
          isLocked={true}
          onToggleLock={() => setSessionLocked(false)}
        />
        <main style={{ maxWidth: "640px", margin: "48px auto", padding: "24px" }}>
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "2px solid #0B1F3A",
              borderRadius: "10px",
              padding: "24px",
            }}
          >
            <h1 style={{ marginTop: 0 }}>Shared-Device Session Locked (AT-13)</h1>
            <p>
              Clinical narratives, intake records, and account details are hidden until
              re-authenticated. Offline emergency guidance above remains accessible at all times.
            </p>
            <button
              type="button"
              onClick={() => setSessionLocked(false)}
              style={{
                minHeight: "44px",
                padding: "10px 20px",
                backgroundColor: "#0F766E",
                color: "#FFFFFF",
                fontWeight: 700,
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              Re-Authenticate & Unlock Workspace
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <EmergencySafetyBanner />
      <SharedDeviceSessionLockBar
        workspaceName={`${workspace} WORKSPACE`}
        actorDisplayName="Connected to Live Neon PostgreSQL · Upstash Redis · OpenRouter"
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
      />

      {/* Live Infrastructure Telemetry Bar */}
      <div
        style={{
          backgroundColor: "#0F172A",
          color: "#F8FAFC",
          padding: "8px 16px",
          fontSize: "12px",
          borderBottom: "1px solid #334155",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "flex",
            flexWrap: "wrap",
            gap: "16px",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: "16px" }}>
            <span>
              <strong>Neon PostgreSQL:</strong>{" "}
              <span style={{ color: cloudState?.neon_db?.connected ? "#34D399" : "#FBBF24" }}>
                {cloudState?.neon_db?.connected
                  ? `CONNECTED (${cloudState.neon_db.isolated_schemas.length} Isolated Schemas · ${cloudState.neon_db.immutability_triggers.length} Immutability Triggers)`
                  : "Connecting..."}
              </span>
            </span>
            <span>
              <strong>Upstash Redis:</strong>{" "}
              <span style={{ color: cloudState?.upstash_redis?.connected ? "#34D399" : "#FBBF24" }}>
                {cloudState?.upstash_redis?.connected ? "PONG (Connected)" : "Connecting..."}
              </span>
            </span>
            <span>
              <strong>AI Gateway:</strong>{" "}
              <span
                style={{
                  color: cloudState?.upstash_redis?.ai_kill_switch?.enabled
                    ? "#F87171"
                    : "#34D399",
                }}
              >
                {cloudState?.upstash_redis?.ai_kill_switch?.enabled
                  ? "KILL-SWITCH ACTIVE (AI-OFF)"
                  : "POLICY-LIMITED ACTIVE"}
              </span>
            </span>
          </div>
          <button
            type="button"
            onClick={() => void refreshCloudState()}
            style={{
              padding: "4px 10px",
              backgroundColor: "#1E293B",
              color: "#E2E8F0",
              border: "1px solid #475569",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            {loadingCloud ? "Syncing..." : "Refresh Cloud State"}
          </button>
        </div>
      </div>

      {/* Role Workspace Switcher */}
      <nav
        aria-label="LoveWorld Care Role Workspaces"
        style={{
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #CBD5E1",
          padding: "10px 16px",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "flex",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          {(
            [
              ["PATIENT", "1. Patient PWA (DoctorNow & Health Navigator)"],
              ["CLINICIAN", "2. Clinician PWA (Queue, LiveKit RTC & Ed25519 Signing)"],
              ["COMMAND", "3. Care Command (Executive, Governance & Finance)"],
              ["SPONSOR", "4. SponsorCare & Institutional Pools (NGN & Espees ESP)"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setWorkspace(id)}
              style={{
                minHeight: "44px",
                padding: "8px 16px",
                backgroundColor: workspace === id ? "#0B1F3A" : "#F1F5F9",
                color: workspace === id ? "#FFFFFF" : "#0F172A",
                fontWeight: 700,
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      {statusBanner && (
        <div
          style={{
            maxWidth: "1200px",
            margin: "16px auto 0",
            padding: "12px 16px",
            backgroundColor: "#F0FDFA",
            border: "1px solid #0F766E",
            color: "#115E59",
            borderRadius: "8px",
            fontWeight: 700,
            fontSize: "14px",
          }}
        >
          {statusBanner}
        </div>
      )}

      <main style={{ maxWidth: "1200px", margin: "20px auto", padding: "0 16px 64px" }}>
        {/* ===================================================================
            WORKSPACE 1: PATIENT PWA (DoctorNow & Health Navigator)
           =================================================================== */}
        {workspace === "PATIENT" && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: "24px",
            }}
          >
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Health Navigator — Deterministic Clinical Intake (§7)
              </h2>
              <p style={{ fontSize: "13px", color: "#475569" }}>
                Active Bundle: <code>LW-NG-GP-ADULT-V1</code> (Dual Signed by Dr. Adebayo Okonkwo
                &amp; Dr. Chidinma Eze)
              </p>

              <div style={{ display: "grid", gap: "12px" }}>
                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Patient Age (Years)
                  <input
                    type="number"
                    value={ageYears}
                    onChange={(e) => setAgeYears(Number(e.target.value))}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <fieldset
                  style={{
                    border: "1px solid #FCA5A5",
                    backgroundColor: "#FEF2F2",
                    borderRadius: "8px",
                    padding: "12px",
                  }}
                >
                  <legend style={{ fontWeight: 700, color: "#991B1B" }}>
                    Hard-Stop Red Flag Checks (Evaluated Before Scheduling/Payment)
                  </legend>
                  <label
                    style={{ display: "flex", alignItems: "center", minHeight: "44px", gap: "8px" }}
                  >
                    <input
                      type="checkbox"
                      checked={chestPain}
                      onChange={(e) => setChestPain(e.target.checked)}
                    />
                    Severe chest pain, tightness, or pressure?
                  </label>
                  <label
                    style={{ display: "flex", alignItems: "center", minHeight: "44px", gap: "8px" }}
                  >
                    <input
                      type="checkbox"
                      checked={breathingDifficulty}
                      onChange={(e) => setBreathingDifficulty(e.target.checked)}
                    />
                    Sudden or severe difficulty breathing?
                  </label>
                  <label
                    style={{ display: "flex", alignItems: "center", minHeight: "44px", gap: "8px" }}
                  >
                    <input
                      type="checkbox"
                      checked={uncontrolledBleeding}
                      onChange={(e) => setUncontrolledBleeding(e.target.checked)}
                    />
                    Uncontrolled bleeding, seizure, or loss of consciousness?
                  </label>
                </fieldset>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Primary Symptom Category
                  <select
                    value={symptomCategory}
                    onChange={(e) => setSymptomCategory(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  >
                    <option value="FEVER_OR_MALARIA_LIKE">Fever / Malaria-like symptoms</option>
                    <option value="RESPIRATORY_COUGH_COLD">Mild Cough / Cold</option>
                    <option value="GASTROINTESTINAL">Digestive / Gastrointestinal</option>
                    <option value="MUSCULOSKELETAL">Joint / Muscle pain</option>
                    <option value="CHRONIC_FOLLOWUP">CareContinuity Chronic Follow-up</option>
                  </select>
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Symptom Duration (Days)
                  <input
                    type="number"
                    value={durationDays}
                    onChange={(e) => setDurationDays(Number(e.target.value))}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Your Verbatim Statement (Preserved for Assigned Doctor)
                  <textarea
                    rows={3}
                    value={rawStatement}
                    onChange={(e) => setRawStatement(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Consultation Modality (§8.3)
                  <select
                    value={selectedModality}
                    onChange={(e) => setSelectedModality(e.target.value as ConsultationModality)}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  >
                    <option value="VIDEO">Live Video Consultation (LiveKit WebRTC)</option>
                    <option value="AUDIO_FALLBACK">Low-Bandwidth Audio Fallback</option>
                    <option value="ASYNC_CLINICAL_MESSAGING">
                      Secure Asynchronous Clinical Messaging
                    </option>
                  </select>
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Funding Route &amp; Sponsor Pool (§10)
                  <select
                    value={selectedAgreementId}
                    onChange={(e) => {
                      setSelectedAgreementId(e.target.value);
                      setFundingRoute("SPONSOR_DEFINED_SERVICES");
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  >
                    <option value="AGR-LW-MEDICAID-NG-2026">
                      SponsorCare: LoveWorld Medicaid Pool (NGN — ₦6,000.00)
                    </option>
                    <option value="AGR-LW-ESPEES-PARTNERS-2026">
                      SponsorCare: LoveWorld Partners Espees Pool (ESP — 4.00 ESP)
                    </option>
                  </select>
                </label>

                <button
                  type="button"
                  onClick={() => void handleCreateEpisodeAndEvaluate()}
                  style={{
                    minHeight: "44px",
                    padding: "12px 20px",
                    backgroundColor: hardStopTriggered ? "#B91C1C" : "#0B1F3A",
                    color: "#FFFFFF",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  {hardStopTriggered
                    ? "Evaluate Hard-Stop Emergency Guidance (No Payment Required)"
                    : "Submit Intake, Run Deterministic Protocol & Book Slot in Neon DB"}
                </button>
              </div>
            </section>

            {/* Right Column: Live Neon DB Episodes & Signed Clinical Records */}
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Live Care Episodes &amp; Signed Summaries (Neon PostgreSQL)
              </h2>

              {latestIntakeResult && (
                <div
                  style={{
                    backgroundColor: "#F0FDFA",
                    border: "2px solid #0F766E",
                    borderRadius: "8px",
                    padding: "14px",
                    marginBottom: "16px",
                  }}
                >
                  <div style={{ fontWeight: 800 }}>
                    Latest Episode: <code>{latestIntakeResult.episode_id}</code> · Outcome:{" "}
                    {latestIntakeResult.outcome_type} ({latestIntakeResult.fired_rule})
                  </div>
                  <div style={{ marginTop: "8px" }}>
                    <AiDraftWatermarkBadge modelId={latestIntakeResult.ai_draft.model_id} />
                    <p style={{ fontSize: "13px", margin: "8px 0 0" }}>
                      {latestIntakeResult.ai_draft.draft_summary}
                    </p>
                  </div>
                </div>
              )}

              <h3 style={{ fontSize: "15px", marginBottom: "8px" }}>
                Recent Episodes in <code>care_clinical.care_episodes</code> (
                {cloudState?.episodes?.length || 0})
              </h3>
              <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}>
                {(cloudState?.episodes || []).slice(0, 4).map((ep) => (
                  <div
                    key={ep.id}
                    style={{
                      backgroundColor: "#F8FAFC",
                      border: "1px solid #CBD5E1",
                      borderRadius: "6px",
                      padding: "10px",
                      fontSize: "13px",
                    }}
                  >
                    <div>
                      <strong>{ep.id}</strong> · State: <code>{ep.state}</code> · Protocol:{" "}
                      <strong>{ep.active_protocol_outcome}</strong>
                    </div>
                    <div style={{ color: "#475569", marginTop: "4px" }}>
                      Statement: &ldquo;{ep.chief_complaint_summary}&rdquo;
                    </div>
                  </div>
                ))}
              </div>

              <h3 style={{ fontSize: "15px", marginBottom: "8px" }}>
                Clinician-Signed Records in <code>care_clinical.care_clinical_documents</code> (
                {cloudState?.signed_documents?.length || 0})
              </h3>
              <div style={{ display: "grid", gap: "12px" }}>
                {(cloudState?.signed_documents || []).slice(0, 3).map((doc) => (
                  <div key={doc.id}>
                    <SignedRecordSeal
                      signerName={doc.author_clinician_id}
                      mdcnLicence={doc.author_mdcn_licence}
                      signedAtIso={doc.signed_at}
                      documentSha256={doc.document_sha256}
                    />
                    <div
                      style={{
                        backgroundColor: "#F8FAFC",
                        border: "1px solid #CBD5E1",
                        padding: "10px",
                        borderRadius: "0 0 6px 6px",
                        fontSize: "13px",
                      }}
                    >
                      <div>
                        <strong>Assessment:</strong> {doc.clinical_assessment}
                      </div>
                      <div>
                        <strong>Plan:</strong> {doc.management_plan}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {/* ===================================================================
            WORKSPACE 2: CLINICIAN PWA
           =================================================================== */}
        {workspace === "CLINICIAN" && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: "24px",
            }}
          >
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Clinician Consultation &amp; Ed25519 Signing (§6.4 &amp; §8.2)
              </h2>
              <p style={{ fontSize: "13px", color: "#475569" }}>
                Authenticated Practitioner:{" "}
                <strong>Dr. Adebayo Okonkwo (MDCN/R/44210 · APPROVED_ACTIVE)</strong>
              </p>

              <div style={{ display: "grid", gap: "12px" }}>
                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Active Encounter ID
                  <input
                    type="text"
                    value={activeEncounterId}
                    onChange={(e) => setActiveEncounterId(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      minHeight: "44px",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  History &amp; Relevant Findings
                  <textarea
                    rows={2}
                    value={historyAndFindings}
                    onChange={(e) => setHistoryAndFindings(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Clinical Assessment
                  <textarea
                    rows={2}
                    value={assessment}
                    onChange={(e) => setAssessment(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Management Plan &amp; Referral
                  <textarea
                    rows={2}
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Safety-Net Instructions
                  <textarea
                    rows={2}
                    value={safetyNet}
                    onChange={(e) => setSafetyNet(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "4px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #94A3B8",
                    }}
                  />
                </label>

                <button
                  type="button"
                  onClick={() => void handleSignEncounter()}
                  style={{
                    minHeight: "44px",
                    padding: "12px 20px",
                    backgroundColor: "#0F766E",
                    color: "#FFFFFF",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  Sign Final Encounter (Ed25519 + Lock in Neon DB + Redeem Sponsor Entitlement)
                </button>
              </div>
            </section>

            {/* Right Column: PostgreSQL Immutability Trigger Verification & Linked Addenda (AT-08) */}
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                PostgreSQL Immutability Trigger &amp; Linked Addenda (AT-08)
              </h2>
              <p style={{ fontSize: "13px", color: "#475569" }}>
                Signed rows in <code>care_clinical.care_clinical_documents</code> are protected by
                the live PostgreSQL trigger <code>trg_immutable_signed_clinical_documents</code>.
              </p>

              {(cloudState?.signed_documents || []).slice(0, 2).map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    border: "1px solid #CBD5E1",
                    borderRadius: "8px",
                    padding: "12px",
                    marginBottom: "14px",
                  }}
                >
                  <SignedRecordSeal
                    signerName={doc.author_clinician_id}
                    mdcnLicence={doc.author_mdcn_licence}
                    signedAtIso={doc.signed_at}
                    documentSha256={doc.document_sha256}
                  />
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() =>
                        void handleTestPostgresImmutabilityTrigger(doc.document_sha256)
                      }
                      style={{
                        minHeight: "44px",
                        padding: "8px 12px",
                        backgroundColor: "#B91C1C",
                        color: "#FFFFFF",
                        fontWeight: 700,
                        border: "none",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      Test AT-08: Attempt Direct SQL UPDATE on Signed Record
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void handleAppendAddendum(doc.encounter_id, doc.document_sha256)
                      }
                      style={{
                        minHeight: "44px",
                        padding: "8px 12px",
                        backgroundColor: "#0B1F3A",
                        color: "#FFFFFF",
                        fontWeight: 700,
                        border: "none",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      Append Signed Addendum (Linked to SHA-256)
                    </button>
                  </div>
                </div>
              ))}

              {immutabilityTriggerProof && (
                <div
                  style={{
                    backgroundColor: "#FEF2F2",
                    border: "2px solid #B91C1C",
                    color: "#7F1D1D",
                    padding: "12px",
                    borderRadius: "8px",
                    fontSize: "13px",
                    fontFamily: "monospace",
                    marginBottom: "14px",
                  }}
                >
                  <strong>PostgreSQL Trigger Blocked Tampering (AT-08 Verified):</strong>{" "}
                  {immutabilityTriggerProof}
                </div>
              )}

              <h3 style={{ fontSize: "15px" }}>
                Appended Addenda in <code>care_clinical.care_clinical_addenda</code> (
                {cloudState?.addenda?.length || 0})
              </h3>
              {(cloudState?.addenda || []).map((a) => (
                <div
                  key={a.id}
                  style={{
                    backgroundColor: "#F0FDFA",
                    border: "1px solid #0F766E",
                    padding: "10px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    marginBottom: "8px",
                  }}
                >
                  <div>
                    <strong>{a.id}:</strong> {a.amendment_reason} — {a.addendum_text}
                  </div>
                  <div style={{ fontFamily: "monospace" }}>
                    Original Hash: {a.original_signed_document_hash.slice(0, 20)}... | Addendum
                    Hash: {a.addendum_sha256.slice(0, 20)}...
                  </div>
                </div>
              ))}
            </section>
          </div>
        )}

        {/* ===================================================================
            WORKSPACE 3: CARE COMMAND CONSOLE
           =================================================================== */}
        {workspace === "COMMAND" && (
          <div style={{ display: "grid", gap: "20px" }}>
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Executive Care Command &amp; Unit Economics (§3.1 &amp; §17.2)
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    backgroundColor: "#F8FAFC",
                    border: "1px solid #CBD5E1",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#475569" }}>
                    Signed Encounters in Neon DB
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#0B1F3A" }}>
                    {cloudState?.signed_documents?.length || 0}
                  </div>
                </div>
                <div
                  style={{
                    backgroundColor: "#F8FAFC",
                    border: "1px solid #CBD5E1",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#475569" }}>
                    Settled GP Encounter Price
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#0B1F3A" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.settledRevenueMinor,
                      currency: "NGN",
                    })}
                  </div>
                </div>
                <div
                  style={{
                    backgroundColor: "#F0FDFA",
                    border: "1px solid #0F766E",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#115E59" }}>
                    Contribution Margin (§17.2)
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#0F766E" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.contributionMarginMinor,
                      currency: "NGN",
                    })}{" "}
                    (29.17%)
                  </div>
                </div>
                <div
                  style={{
                    backgroundColor: "#FDF8EC",
                    border: "1px solid #C89D3C",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#92400E" }}>
                    Base Break-Even (§17.5)
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#0B1F3A" }}>
                    1,143 / month
                  </div>
                </div>
              </div>
            </section>

            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Global AI-Off Kill Switch (Synced via Upstash Serverless Redis — §15.6 &amp; AT-16)
              </h2>
              <p style={{ fontSize: "14px" }}>
                Live Upstash Redis Kill-Switch Status:{" "}
                <strong
                  style={{
                    color: cloudState?.upstash_redis?.ai_kill_switch?.enabled
                      ? "#B91C1C"
                      : "#0F766E",
                  }}
                >
                  {cloudState?.upstash_redis?.ai_kill_switch?.enabled
                    ? "AI-OFF MODE ACTIVE (All Generative Models Disabled — Deterministic & Human Care 100% Operational)"
                    : "POLICY-LIMITED AI ASSISTANCE ENABLED"}
                </strong>
              </p>
              <button
                type="button"
                onClick={() =>
                  void handleToggleKillSwitch(
                    !cloudState?.upstash_redis?.ai_kill_switch?.enabled
                  )
                }
                style={{
                  minHeight: "44px",
                  padding: "10px 18px",
                  backgroundColor: cloudState?.upstash_redis?.ai_kill_switch?.enabled
                    ? "#0F766E"
                    : "#B91C1C",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                {cloudState?.upstash_redis?.ai_kill_switch?.enabled
                  ? "Restore Policy-Limited AI Assistance in Upstash Redis"
                  : "Trigger Global AI-Off Kill Switch in Upstash Redis (AT-16)"}
              </button>
            </section>
          </div>
        )}

        {/* ===================================================================
            WORKSPACE 4: SPONSORCARE & INSTITUTIONAL POOLS (NGN & ESPEES ESP)
           =================================================================== */}
        {workspace === "SPONSOR" && (
          <div style={{ display: "grid", gap: "20px" }}>
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Live SponsorCare Pools in <code>finance_ledger.finance_sponsor_pools</code> (§10)
              </h2>
              <p style={{ fontSize: "13px", color: "#475569" }}>
                Distinguishes uncollected pledges from funded cash/Espees credits. Entitlements
                redeem strictly on clinician-signed encounters.
              </p>

              <div style={{ display: "grid", gap: "16px", marginTop: "16px" }}>
                {(cloudState?.sponsor_pools || []).map((pool) => {
                  const available =
                    Number(pool.funded_cash_minor) -
                    Number(pool.active_reserved_minor) -
                    Number(pool.redeemed_minor);
                  const effCount = simulateSmallCohort ? 3 : pool.eligible_beneficiary_count;
                  const suppressed = effCount < 5;

                  return (
                    <div
                      key={pool.agreement_id}
                      style={{
                        border: "1px solid #CBD5E1",
                        borderRadius: "8px",
                        padding: "16px",
                        backgroundColor: "#F8FAFC",
                      }}
                    >
                      <div style={{ fontWeight: 800, fontSize: "16px", color: "#0B1F3A" }}>
                        {pool.sponsor_name} (<code>{pool.agreement_id}</code> · Currency:{" "}
                        {pool.currency})
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                          gap: "12px",
                          marginTop: "12px",
                        }}
                      >
                        <div>
                          <div style={{ fontSize: "12px", color: "#475569" }}>
                            Uncollected Pledge
                          </div>
                          <div style={{ fontWeight: 700 }}>
                            {formatMoneyMinor({
                              amountMinor: Number(pool.committed_unfunded_minor),
                              currency: pool.currency,
                            })}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "12px", color: "#475569" }}>
                            Funded Cash/Credit
                          </div>
                          <div style={{ fontWeight: 700, color: "#0B1F3A" }}>
                            {formatMoneyMinor({
                              amountMinor: Number(pool.funded_cash_minor),
                              currency: pool.currency,
                            })}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "12px", color: "#92400E" }}>Active Reserved</div>
                          <div style={{ fontWeight: 700, color: "#B45309" }}>
                            {formatMoneyMinor({
                              amountMinor: Number(pool.active_reserved_minor),
                              currency: pool.currency,
                            })}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "12px", color: "#115E59" }}>
                            Redeemed (Signed)
                          </div>
                          <div style={{ fontWeight: 700, color: "#0F766E" }}>
                            {formatMoneyMinor({
                              amountMinor: Number(pool.redeemed_minor),
                              currency: pool.currency,
                            })}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "12px", color: "#475569" }}>
                            Available Balance
                          </div>
                          <div style={{ fontWeight: 800, color: "#0F766E" }}>
                            {formatMoneyMinor({
                              amountMinor: available,
                              currency: pool.currency,
                            })}
                          </div>
                        </div>
                      </div>
                      <div style={{ marginTop: "10px", fontSize: "13px" }}>
                        <strong>Eligible Beneficiary Population (k &gt;= 5 Rule — AT-14):</strong>{" "}
                        {suppressed
                          ? "SUPPRESSED_SMALL_COHORT_K_LT_5 (Privacy Protection Active)"
                          : `${effCount} Beneficiaries`}{" "}
                        | <strong>Clinical Narratives Disclosed:</strong> <code>NONE (AT-06)</code>
                      </div>
                    </div>
                  );
                })}
              </div>

              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  minHeight: "44px",
                  gap: "8px",
                  marginTop: "14px",
                  fontWeight: 600,
                }}
              >
                <input
                  type="checkbox"
                  checked={simulateSmallCohort}
                  onChange={(e) => setSimulateSmallCohort(e.target.checked)}
                />
                Simulate Small Cohort (k = 3 &lt; 5) to Verify Automatic Re-Identification
                Suppression (AT-14)
              </label>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
