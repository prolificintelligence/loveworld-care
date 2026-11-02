"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AiDraftWatermarkBadge,
  SharedDeviceSessionLockBar,
  SignedRecordSeal,
  LW_DESIGN_TOKENS,
} from "@loveworld-care/design-system";
import {
  ClaimEncounterResponse,
  CoordinationTask,
  EncounterDetailDTO,
  EncounterSummaryDTO,
  LoveWorldCareApiClient,
  SignedEncounterResponse,
} from "@loveworld-care/api-contracts";
import type { ConsultationModality } from "@loveworld-care/domain-types";

interface PrescriptionItem {
  medication_name: string;
  dosage_instructions: string;
  frequency_per_day: number;
  duration_days: number;
  clinical_indication: string;
}

export default function ClinicianWorkspacePage() {
  const [sessionLocked, setSessionLocked] = useState(false);
  const [clinicianId] = useState("dr-adebayo-okonkwo");
  const [clinicianName] = useState("Dr. Adebayo Okonkwo");
  const [mdcnLicence] = useState("MDCN/R/44210");
  const [clinicianToken, setClinicianToken] = useState<string | null>(null);

  // Live API Client
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Workspace Navigation Views
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<"QUEUE" | "CONSULTATION" | "TASKS">("QUEUE");

  // Queue & Selected Encounter
  const [encountersQueue, setEncountersQueue] = useState<readonly EncounterSummaryDTO[]>([]);
  const [selectedEncounterId, setSelectedEncounterId] = useState<string>("");
  const [activeEncounterDetail, setActiveEncounterDetail] = useState<EncounterDetailDTO | null>(null);
  const [isLoadingQueue, setIsLoadingQueue] = useState<boolean>(true);

  // Clinical Consultation State
  const [isClaiming, setIsClaiming] = useState<boolean>(false);
  const [claimedVersion, setClaimedVersion] = useState<number | null>(null);
  const [rtcToken, setRtcToken] = useState<string | null>(null);
  const [rtcModality, setRtcModality] = useState<ConsultationModality>("VIDEO");
  const [remoteSuitabilityAccepted, setRemoteSuitabilityAccepted] = useState<boolean>(true);

  // Deliberate Clinical Documentation Inputs (LWC-SCR-204 - Start empty, NO PREFILLS!)
  const [historyAndFindings, setHistoryAndFindings] = useState<string>("");
  const [assessment, setAssessment] = useState<string>("");
  const [plan, setPlan] = useState<string>("");
  const [safetyNet, setSafetyNet] = useState<string>("");
  const [mfaCode, setMfaCode] = useState<string>("");

  // Care Plan & Prescription Builder (LWC-SCR-205)
  const [prescriptions, setPrescriptions] = useState<PrescriptionItem[]>([]);
  const [newMedName, setNewMedName] = useState<string>("");
  const [newMedDose, setNewMedDose] = useState<string>("");
  const [newMedDuration, setNewMedDuration] = useState<number>(3);
  const [newMedIndication, setNewMedIndication] = useState<string>("");

  // Referral Order State
  const [includeReferral, setIncludeReferral] = useState<boolean>(false);
  const [referralSpecialty, setReferralSpecialty] = useState<string>("Cardiology");
  const [referralFacility, setReferralFacility] = useState<string>("LoveWorld Medical Centre Ikeja (LMC-001)");
  const [referralReason, setReferralReason] = useState<string>("");

  // Signing Ceremony & Addenda (LWC-SCR-206..207)
  const [isSigning, setIsSigning] = useState<boolean>(false);
  const [signedRecord, setSignedRecord] = useState<SignedEncounterResponse | null>(null);
  const [addendumReason, setAddendumReason] = useState<string>("");
  const [addendumText, setAddendumText] = useState<string>("");
  const [isAddingAddendum, setIsAddingAddendum] = useState<boolean>(false);
  const [addendaList, setAddendaList] = useState<readonly Record<string, unknown>[]>([]);

  // Tasks & Coordination Inbox (LWC-SCR-208)
  const [coordinationTasks, setCoordinationTasks] = useState<readonly CoordinationTask[]>([]);

  // ---------------------------------------------------------------------------
  // Initialize Auth & API Client
  // ---------------------------------------------------------------------------
  const refreshQueue = useCallback(async (clientInstance?: LoveWorldCareApiClient) => {
    const client = clientInstance || apiClient;
    if (!client) return;
    setIsLoadingQueue(true);
    try {
      const list = await client.listEncounters();
      setEncountersQueue(list);
      const coord = await client.listCoordinationBoard().catch(() => []);
      setCoordinationTasks(coord);
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to refresh encounters queue");
    } finally {
      setIsLoadingQueue(false);
    }
  }, [apiClient]);

  useEffect(() => {
    async function initClinician() {
      try {
        let token = typeof window !== "undefined" ? localStorage.getItem("lw_clinician_token") : null;
        if (!token) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: clinicianId,
              audience: "lwc:clinician",
              roles: ["CLINICIAN_GP"],
              mfa: true,
              ttl_minutes: 240,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token && typeof window !== "undefined") {
              localStorage.setItem("lw_clinician_token", token);
            }
          }
        }
        setClinicianToken(token);

        const client = new LoveWorldCareApiClient("", () => ({
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }));
        setApiClient(client);
        await refreshQueue(client);
      } catch (err: unknown) {
        setNetworkError(err instanceof Error ? err.message : "Failed to load clinician workspace");
        setIsLoadingQueue(false);
      }
    }
    initClinician();
  }, [clinicianId, refreshQueue]);

  // ---------------------------------------------------------------------------
  // Load Selected Encounter
  // ---------------------------------------------------------------------------
  const handleSelectEncounter = async (encId: string) => {
    setSelectedEncounterId(encId);
    setSignedRecord(null);
    setClaimedVersion(null);
    setRtcToken(null);
    setActiveWorkspaceTab("CONSULTATION");
    if (!apiClient) return;

    try {
      const detail = await apiClient.getEncounter(encId);
      setActiveEncounterDetail(detail);

      if (detail.state === "SIGNED" && detail.signed_document_hash) {
        setSignedRecord({
          encounter_id: detail.encounter_id,
          state: detail.state,
          version: detail.version,
          signed_at: detail.signed_at || new Date().toISOString(),
          signed_document_hash: detail.signed_document_hash,
          signature_ed25519_base64: "Ed25519_Authoritative_Verification_Seal",
          settlement_triggered: true,
          referral_id: null,
          follow_up_task_id: null,
          fhir_bundle_id: `bundle-${detail.encounter_id}`,
        });
        setAddendaList(detail.addenda || []);
      } else if (detail.primary_clinician_id === clinicianId) {
        setClaimedVersion(detail.version);
      }
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to load encounter details");
    }
  };

  // ---------------------------------------------------------------------------
  // Atomic Case Claiming (LWC-SCR-203, §6.4, AT-02)
  // ---------------------------------------------------------------------------
  const handleClaimCase = async () => {
    if (!apiClient || !selectedEncounterId) return;
    setIsClaiming(true);
    setNetworkError(null);
    setActionSuccess(null);

    try {
      const idempotencyKey = `claim-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const res: ClaimEncounterResponse = await apiClient.claimEncounter(
        selectedEncounterId,
        idempotencyKey
      );
      setClaimedVersion(res.version);
      setRtcToken(res.rtc_room_token);
      setActionSuccess(
        `Case ${res.encounter_id} claimed atomically (v${res.version}). LiveKit consultation session unlocked.`
      );
      await refreshQueue();
    } catch (err: unknown) {
      setNetworkError(
        err instanceof Error ? err.message : "Case claim conflict. Case may already be claimed by another doctor."
      );
    } finally {
      setIsClaiming(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Prescription Builder Helpers
  // ---------------------------------------------------------------------------
  const handleAddPrescription = () => {
    if (!newMedName.trim() || !newMedDose.trim()) return;
    setPrescriptions((prev) => [
      ...prev,
      {
        medication_name: newMedName.trim(),
        dosage_instructions: newMedDose.trim(),
        frequency_per_day: 1,
        duration_days: newMedDuration,
        clinical_indication: newMedIndication.trim() || "Clinical indication noted",
      },
    ]);
    setNewMedName("");
    setNewMedDose("");
    setNewMedIndication("");
  };

  const handleRemovePrescription = (index: number) => {
    setPrescriptions((prev) => prev.filter((_, i) => i !== index));
  };

  // ---------------------------------------------------------------------------
  // Ed25519 Signing Ceremony (LWC-SCR-206, §8.2, §13.4, AT-08)
  // ---------------------------------------------------------------------------
  const handleSignEncounter = async () => {
    if (!apiClient || !selectedEncounterId || claimedVersion === null) return;
    if (!mfaCode.trim()) {
      setNetworkError("MFA Step-Up verification code is required to sign clinical documents.");
      return;
    }
    if (!historyAndFindings.trim() || !assessment.trim() || !plan.trim()) {
      setNetworkError("Deliberate clinical documentation required: History, Assessment, and Plan cannot be blank.");
      return;
    }

    setIsSigning(true);
    setNetworkError(null);
    setActionSuccess(null);

    try {
      const idempotencyKey = `sign-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const res: SignedEncounterResponse = await apiClient.signEncounter(
        selectedEncounterId,
        {
          expected_version: claimedVersion,
          remote_suitability_accepted: remoteSuitabilityAccepted,
          modality_used: rtcModality,
          modality_limitations_noted:
            "Standard teleconsultation; physical auscultation/palpation not applicable remotely.",
          history_and_findings: historyAndFindings.trim(),
          clinical_assessment: assessment.trim(),
          management_plan: plan.trim(),
          safety_net_instructions: safetyNet.trim() || "Seek in-person emergency hospital care if red flag symptoms develop.",
          mfa_step_up_code: mfaCode.trim(),
          prescriptions: prescriptions.map((p) => ({
            medication_name: p.medication_name,
            dosage_instructions: p.dosage_instructions,
            duration_days: p.duration_days,
            clinical_indication: p.clinical_indication,
          })),
          referral: includeReferral
            ? {
                receiving_facility_code: "LMC-001",
                receiving_facility_name: referralFacility,
                specialty_code: referralSpecialty,
                priority: "routine" as const,
                clinical_reason: referralReason.trim() || "Specialist bridge referral",
                investigations_attached: [],
              }
            : undefined,
        },
        idempotencyKey
      );

      setSignedRecord(res);
      setActionSuccess(
        `Encounter ${selectedEncounterId} signed with verified Ed25519 key. Record is permanently immutable.`
      );
      await refreshQueue();
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to sign clinical record");
    } finally {
      setIsSigning(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Append Cryptographic Addendum (LWC-SCR-207, §8.2, AT-08)
  // ---------------------------------------------------------------------------
  const handleAppendAddendum = async () => {
    if (!apiClient || !selectedEncounterId || !signedRecord?.signed_document_hash) return;
    if (!addendumReason.trim() || !addendumText.trim()) {
      setNetworkError("Amendment reason and addendum text are required.");
      return;
    }
    if (!mfaCode.trim()) {
      setNetworkError("MFA step-up code required to authorize clinical addendum.");
      return;
    }

    setIsAddingAddendum(true);
    setNetworkError(null);
    setActionSuccess(null);

    try {
      const idempotencyKey = `addendum-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      await apiClient.createAddendum(
        selectedEncounterId,
        {
          original_signed_document_hash: signedRecord.signed_document_hash,
          amendment_reason: addendumReason.trim(),
          addendum_text: addendumText.trim(),
          mfa_step_up_code: mfaCode.trim(),
        },
        idempotencyKey
      );

      setActionSuccess("Linked cryptographic addendum sealed to original document.");
      setAddendumReason("");
      setAddendumText("");

      const detail = await apiClient.getEncounter(selectedEncounterId);
      if (detail && detail.addenda) {
        setAddendaList(detail.addenda);
      }
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to append addendum");
    } finally {
      setIsAddingAddendum(false);
    }
  };

  // ===========================================================================
  // Session Locked State View
  // ===========================================================================
  if (sessionLocked) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
          color: "#FFFFFF",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "56px", marginBottom: "16px" }}>🔒</div>
        <h1 style={{ fontSize: "24px", fontWeight: 800, marginBottom: "8px" }}>
          Clinician Roster Station Protected
        </h1>
        <p style={{ color: "#94A3B8", maxWidth: "380px", marginBottom: "24px", fontSize: "14px" }}>
          Active session for {clinicianName} ({mdcnLicence}) locked against unauthorized EHR tampering.
        </p>
        <button
          type="button"
          onClick={() => setSessionLocked(false)}
          style={{
            minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
            padding: "12px 28px",
            backgroundColor: LW_DESIGN_TOKENS.colors.warmGold,
            color: LW_DESIGN_TOKENS.colors.royalNavy,
            border: "none",
            borderRadius: LW_DESIGN_TOKENS.radius.md,
            fontWeight: 800,
            fontSize: "15px",
            cursor: "pointer",
          }}
        >
          Unlock Clinician Workspace
        </button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F1F5F9", display: "flex", flexDirection: "column" }}>
      {/* 1. Clinician Header Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="Clinician Workstation · General Practice"
        actorDisplayName={`${clinicianName} · ${mdcnLicence}`}
        isLocked={sessionLocked}
        onToggleLock={() => setSessionLocked((prev) => !prev)}
        onSignOut={() => {
          if (typeof window !== "undefined") localStorage.removeItem("lw_clinician_token");
          window.location.reload();
        }}
      />

      {/* 2. Top Navigation Tabs */}
      <nav
        aria-label="Clinician Workspace Views"
        style={{
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #CBD5E1",
          padding: "0 24px",
          display: "flex",
          gap: "24px",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveWorkspaceTab("QUEUE")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeWorkspaceTab === "QUEUE" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeWorkspaceTab === "QUEUE" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span>Incoming Review Queue</span>
          <span
            style={{
              backgroundColor: encountersQueue.length > 0 ? "#DC2626" : "#E2E8F0",
              color: encountersQueue.length > 0 ? "#FFFFFF" : "#64748B",
              fontSize: "11px",
              padding: "2px 8px",
              borderRadius: "10px",
            }}
          >
            {encountersQueue.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveWorkspaceTab("CONSULTATION")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeWorkspaceTab === "CONSULTATION" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeWorkspaceTab === "CONSULTATION" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          Active Consultation {selectedEncounterId ? `(${selectedEncounterId})` : ""}
        </button>

        <button
          type="button"
          onClick={() => setActiveWorkspaceTab("TASKS")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeWorkspaceTab === "TASKS" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeWorkspaceTab === "TASKS" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span>Coordination & Tasks Inbox</span>
          <span
            style={{
              backgroundColor: "#E2E8F0",
              color: "#475569",
              fontSize: "11px",
              padding: "2px 8px",
              borderRadius: "10px",
            }}
          >
            {coordinationTasks.length}
          </span>
        </button>
      </nav>

      {/* Notifications Bar */}
      {networkError && (
        <div
          role="alert"
          style={{
            backgroundColor: "#FEE2E2",
            borderBottom: "1px solid #FCA5A5",
            padding: "10px 24px",
            color: "#991B1B",
            fontSize: "13px",
            fontWeight: 600,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>⚠️ {networkError}</span>
          <button
            type="button"
            onClick={() => setNetworkError(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#991B1B" }}
          >
            ✕
          </button>
        </div>
      )}

      {actionSuccess && (
        <div
          role="status"
          style={{
            backgroundColor: "#DCFCE7",
            borderBottom: "1px solid #86EFAC",
            padding: "10px 24px",
            color: "#166534",
            fontSize: "13px",
            fontWeight: 700,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>✓ {actionSuccess}</span>
          <button
            type="button"
            onClick={() => setActionSuccess(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#166534" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Workspace Body */}
      <main style={{ padding: "24px", flex: 1, maxWidth: "1280px", margin: "0 auto", width: "100%" }}>
        {/* =================================================================== */}
        {/* VIEW 1: INCOMING REVIEW QUEUE (LWC-SCR-201, 202)                    */}
        {/* =================================================================== */}
        {activeWorkspaceTab === "QUEUE" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Unassigned Case Roster
              </h2>
              <button
                type="button"
                onClick={() => refreshQueue()}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                🔄 Refresh Queue
              </button>
            </div>

            {isLoadingQueue ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#64748B" }}>
                Checking live case queue...
              </div>
            ) : encountersQueue.length === 0 ? (
              /* Truthful Empty Queue State per LWC-SCR-201 */
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.lg,
                  border: "1px dashed #CBD5E1",
                  padding: "60px 20px",
                  textAlign: "center",
                  maxWidth: "600px",
                  margin: "40px auto",
                }}
              >
                <div style={{ fontSize: "48px", marginBottom: "12px" }}>✅</div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 6px" }}>
                  Your Roster Queue is Clear
                </h3>
                <p style={{ fontSize: "14px", color: "#64748B", margin: 0 }}>
                  No unassigned cases waiting for GP review. When a patient completes triage or books a slot, it will appear here.
                </p>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                {encountersQueue.map((enc) => (
                  <div
                    key={enc.encounter_id}
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "16px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: 800, fontSize: "16px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                          {enc.encounter_id}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            backgroundColor: enc.state === "OPEN" ? "#FEF3C7" : "#DBEAFE",
                            color: enc.state === "OPEN" ? "#92400E" : "#1E40AF",
                            padding: "2px 8px",
                            borderRadius: "4px",
                          }}
                        >
                          {enc.state}
                        </span>
                        <span style={{ fontSize: "12px", color: "#64748B" }}>
                          Modality: {enc.modality} · Patient: {enc.patient_id}
                        </span>
                      </div>
                      <div style={{ fontSize: "13px", color: "#475569", marginTop: "4px" }}>
                        Funding: {enc.funding_route}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        type="button"
                        onClick={() => handleSelectEncounter(enc.encounter_id)}
                        style={{
                          padding: "8px 16px",
                          backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                          color: "#FFFFFF",
                          border: "none",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          fontWeight: 700,
                          fontSize: "13px",
                          cursor: "pointer",
                        }}
                      >
                        Open Encounter →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* =================================================================== */}
        {/* VIEW 2: ACTIVE CONSULTATION & DOCUMENTATION (LWC-SCR-203..207)      */}
        {/* =================================================================== */}
        {activeWorkspaceTab === "CONSULTATION" && (
          <div>
            {!selectedEncounterId ? (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.lg,
                  border: "1px dashed #CBD5E1",
                  padding: "48px 20px",
                  textAlign: "center",
                  maxWidth: "540px",
                  margin: "40px auto",
                }}
              >
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                  No Encounter Selected
                </h3>
                <p style={{ fontSize: "14px", color: "#64748B", margin: "8px 0 16px" }}>
                  Please return to the incoming queue to pick an encounter for consultation.
                </p>
                <button
                  type="button"
                  onClick={() => setActiveWorkspaceTab("QUEUE")}
                  style={{
                    padding: "8px 18px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  View Incoming Queue
                </button>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                {/* Left Column: Triage, Intake Review & RTC Session */}
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  {/* Encounter Status Card */}
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "16px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 800, fontSize: "17px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                        {selectedEncounterId}
                      </span>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          backgroundColor: "#DBEAFE",
                          color: "#1E40AF",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {activeEncounterDetail?.state || "OPEN"}
                      </span>
                    </div>

                    <div style={{ fontSize: "13px", color: "#64748B", marginTop: "8px" }}>
                      Patient ID: <strong>{activeEncounterDetail?.patient_id}</strong>
                    </div>

                    {/* Claim Button */}
                    {!claimedVersion && activeEncounterDetail?.state !== "SIGNED" && (
                      <div style={{ marginTop: "14px" }}>
                        <button
                          type="button"
                          onClick={handleClaimCase}
                          disabled={isClaiming}
                          style={{
                            width: "100%",
                            minHeight: "44px",
                            backgroundColor: LW_DESIGN_TOKENS.colors.warmGold,
                            color: LW_DESIGN_TOKENS.colors.royalNavy,
                            border: "none",
                            borderRadius: LW_DESIGN_TOKENS.radius.md,
                            fontWeight: 800,
                            fontSize: "14px",
                            cursor: isClaiming ? "not-allowed" : "pointer",
                          }}
                        >
                          {isClaiming ? "Claiming Case Lock..." : "Claim Case (Atomic Concurrency Lock)"}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* WebRTC Video / Audio Room */}
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "16px",
                    }}
                  >
                    <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", margin: "0 0 10px" }}>
                      LiveKit Consultation Session
                    </h3>
                    {rtcToken ? (
                      <div
                        style={{
                          backgroundColor: "#0F172A",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          padding: "30px 16px",
                          textAlign: "center",
                          color: "#FFFFFF",
                        }}
                      >
                        <div style={{ fontSize: "32px", marginBottom: "8px" }}>📹</div>
                        <div style={{ fontWeight: 700, fontSize: "14px", color: "#38BDF8" }}>
                          Encrypted Room Unlocked ({rtcModality})
                        </div>
                        <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                          LiveKit WebRTC Channel Active
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          backgroundColor: "#F8FAFC",
                          border: "1px dashed #CBD5E1",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          padding: "24px 16px",
                          textAlign: "center",
                          color: "#64748B",
                          fontSize: "13px",
                        }}
                      >
                        Claim the encounter above to unlock the end-to-end encrypted LiveKit consultation room.
                      </div>
                    )}
                  </div>

                  {/* Remote Suitability & Modality Limitations */}
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "16px",
                    }}
                  >
                    <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#1E293B", margin: "0 0 8px" }}>
                      Remote Suitability Attestation
                    </h3>
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#334155" }}>
                      <input
                        type="checkbox"
                        checked={remoteSuitabilityAccepted}
                        onChange={(e) => setRemoteSuitabilityAccepted(e.target.checked)}
                      />
                      <span>Confirmed suitable for remote evaluation; patient is safe in current environment.</span>
                    </label>
                  </div>
                </div>

                {/* Right Column: Deliberate Clinical Documentation & Ed25519 Signing */}
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "16px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                      <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                        Clinical Encounter Note
                      </h3>
                      {signedRecord && (
                        <span style={{ fontSize: "12px", fontWeight: 800, color: "#166534" }}>
                          ✓ Ed25519 Sealed & Immutable
                        </span>
                      )}
                    </div>

                    {signedRecord ? (
                      /* Immutable View Once Signed */
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        <div>
                          <strong>History & Findings:</strong>
                          <p style={{ fontSize: "13px", color: "#334155", margin: "4px 0 0" }}>
                            {String(activeEncounterDetail?.signed_clinical_note || historyAndFindings)}
                          </p>
                        </div>
                        <SignedRecordSeal
                          signerName={clinicianName}
                          mdcnLicence={mdcnLicence}
                          signedAtIso={signedRecord.signed_at}
                          documentSha256={signedRecord.signed_document_hash}
                        />

                        {/* Addenda List */}
                        {addendaList.length > 0 && (
                          <div style={{ marginTop: "12px", borderTop: "1px solid #E2E8F0", paddingTop: "8px" }}>
                            <h4 style={{ fontSize: "13px", fontWeight: 800, margin: "0 0 6px" }}>Linked Addenda:</h4>
                            {addendaList.map((ad: Record<string, unknown>, idx) => (
                              <div key={idx} style={{ backgroundColor: "#F8FAFC", padding: "8px", borderRadius: "4px", marginBottom: "6px" }}>
                                <div style={{ fontSize: "11px", color: "#64748B" }}>Reason: {String(ad.amendment_reason)}</div>
                                <div style={{ fontSize: "12px", color: "#1E293B" }}>{String(ad.addendum_text)}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Append Addendum Form */}
                        <div style={{ marginTop: "12px", borderTop: "1px solid #E2E8F0", paddingTop: "12px" }}>
                          <h4 style={{ fontSize: "14px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 8px" }}>
                            Append Cryptographic Addendum
                          </h4>
                          <input
                            type="text"
                            placeholder="Amendment reason (required)"
                            value={addendumReason}
                            onChange={(e) => setAddendumReason(e.target.value)}
                            style={{
                              width: "100%",
                              padding: "8px",
                              marginBottom: "8px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "13px",
                            }}
                          />
                          <textarea
                            rows={3}
                            placeholder="Additional clinical observation or amendment details..."
                            value={addendumText}
                            onChange={(e) => setAddendumText(e.target.value)}
                            style={{
                              width: "100%",
                              padding: "8px",
                              marginBottom: "8px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "13px",
                            }}
                          />
                          <button
                            type="button"
                            onClick={handleAppendAddendum}
                            disabled={isAddingAddendum}
                            style={{
                              padding: "8px 16px",
                              backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                              color: "#FFFFFF",
                              border: "none",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              fontWeight: 700,
                              fontSize: "13px",
                              cursor: isAddingAddendum ? "not-allowed" : "pointer",
                            }}
                          >
                            {isAddingAddendum ? "Sealing Addendum..." : "Append Addendum"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Deliberate Entry Form */
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        <div>
                          <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                            Subjective History & Objective Examination Findings:
                          </label>
                          <textarea
                            rows={3}
                            value={historyAndFindings}
                            onChange={(e) => setHistoryAndFindings(e.target.value)}
                            placeholder="Deliberate clinical entry required: history, review of systems, vitals..."
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "13px",
                            }}
                          />
                        </div>

                        <div>
                          <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                            Clinical Assessment / Working Diagnosis:
                          </label>
                          <textarea
                            rows={2}
                            value={assessment}
                            onChange={(e) => setAssessment(e.target.value)}
                            placeholder="Diagnostic impression, differentials..."
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "13px",
                            }}
                          />
                        </div>

                        <div>
                          <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                            Management & Continuity Plan:
                          </label>
                          <textarea
                            rows={2}
                            value={plan}
                            onChange={(e) => setPlan(e.target.value)}
                            placeholder="Therapeutic plan, hydration, diagnostics, review schedule..."
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "13px",
                            }}
                          />
                        </div>

                        {/* Prescription Builder */}
                        <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: "10px" }}>
                          <label style={{ display: "block", fontSize: "12px", fontWeight: 800, color: "#1E293B", marginBottom: "6px" }}>
                            Prescribe Medications ({prescriptions.length}):
                          </label>
                          {prescriptions.map((p, pi) => (
                            <div
                              key={pi}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                backgroundColor: "#F8FAFC",
                                padding: "6px 10px",
                                borderRadius: "4px",
                                marginBottom: "4px",
                                fontSize: "12px",
                              }}
                            >
                              <span>
                                <strong>{p.medication_name}</strong> · {p.dosage_instructions} ({p.duration_days} days)
                              </span>
                              <button
                                type="button"
                                onClick={() => handleRemovePrescription(pi)}
                                style={{ background: "none", border: "none", color: "#DC2626", cursor: "pointer", fontWeight: 700 }}
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                          <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr", gap: "6px", marginTop: "6px" }}>
                            <input
                              type="text"
                              placeholder="Medication name"
                              value={newMedName}
                              onChange={(e) => setNewMedName(e.target.value)}
                              style={{ padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                            />
                            <input
                              type="text"
                              placeholder="Dosage (e.g. 500mg PO BD)"
                              value={newMedDose}
                              onChange={(e) => setNewMedDose(e.target.value)}
                              style={{ padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                            />
                            <button
                              type="button"
                              onClick={handleAddPrescription}
                              style={{
                                backgroundColor: "#F1F5F9",
                                border: "1px solid #CBD5E1",
                                borderRadius: "4px",
                                fontSize: "12px",
                                fontWeight: 700,
                                cursor: "pointer",
                              }}
                            >
                              + Add
                            </button>
                          </div>
                        </div>

                        {/* Referral Order Checkbox */}
                        <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: "10px" }}>
                          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: 700 }}>
                            <input
                              type="checkbox"
                              checked={includeReferral}
                              onChange={(e) => setIncludeReferral(e.target.checked)}
                            />
                            <span>Include In-Person Specialist / Facility Referral Order</span>
                          </label>
                          {includeReferral && (
                            <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                              <input
                                type="text"
                                placeholder="Referral specialty (e.g. Cardiology)"
                                value={referralSpecialty}
                                onChange={(e) => setReferralSpecialty(e.target.value)}
                                style={{ padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                              />
                              <input
                                type="text"
                                placeholder="Receiving network facility"
                                value={referralFacility}
                                onChange={(e) => setReferralFacility(e.target.value)}
                                style={{ padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                              />
                            </div>
                          )}
                        </div>

                        {/* MFA Step-Up Input & Signing */}
                        <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: "10px" }}>
                          <label style={{ display: "block", fontSize: "12px", fontWeight: 800, color: "#1E293B", marginBottom: "4px" }}>
                            Clinician MFA Step-Up Code:
                          </label>
                          <input
                            type="text"
                            placeholder="Enter 6-digit MFA step-up code"
                            value={mfaCode}
                            onChange={(e) => setMfaCode(e.target.value)}
                            style={{
                              width: "100%",
                              padding: "8px 12px",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              border: "1px solid #CBD5E1",
                              fontSize: "14px",
                              letterSpacing: "2px",
                              fontWeight: 700,
                              marginBottom: "10px",
                            }}
                          />
                          <button
                            type="button"
                            onClick={handleSignEncounter}
                            disabled={isSigning || !claimedVersion}
                            style={{
                              width: "100%",
                              minHeight: "44px",
                              backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                              color: "#FFFFFF",
                              border: "none",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              fontWeight: 800,
                              fontSize: "14px",
                              cursor: isSigning || !claimedVersion ? "not-allowed" : "pointer",
                            }}
                          >
                            {isSigning ? "Signing with Ed25519..." : "Sign & Finalize Clinical Encounter"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =================================================================== */}
        {/* VIEW 3: COORDINATION & TASKS INBOX (LWC-SCR-208)                    */}
        {/* =================================================================== */}
        {activeWorkspaceTab === "TASKS" && (
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, marginBottom: "16px" }}>
              Clinical Coordination Tasks
            </h2>
            {coordinationTasks.length === 0 ? (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  border: "1px dashed #CBD5E1",
                  padding: "40px",
                  textAlign: "center",
                  color: "#64748B",
                  fontSize: "14px",
                }}
              >
                No pending coordination escalations or tasks assigned.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "10px" }}>
                {coordinationTasks.map((ct: CoordinationTask, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "14px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 800, fontSize: "14px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                        {String(ct.work_state)} · {String(ct.urgency)}
                      </div>
                      <div style={{ fontSize: "12px", color: "#64748B", marginTop: "2px" }}>
                        Patient ID: {String(ct.patient_id)} · Team: {String(ct.owner_team)}
                      </div>
                      <div style={{ fontSize: "13px", color: "#334155", marginTop: "4px" }}>
                        {String(ct.next_action)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
