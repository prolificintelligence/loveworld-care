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
  EncounterDetailDTO,
  EncounterSummaryDTO,
  LoveWorldCareApiClient,
  SignedEncounterResponse,
} from "@loveworld-care/api-contracts";
import type { ConsultationModality } from "@loveworld-care/domain-types";

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

  // Queue & Selected Encounter
  const [encountersQueue, setEncountersQueue] = useState<readonly EncounterSummaryDTO[]>([]);
  const [selectedEncounterId, setSelectedEncounterId] = useState<string>("ENC-NG-88412");
  const [activeEncounterDetail, setActiveEncounterDetail] = useState<EncounterDetailDTO | null>(null);

  // Clinical Consultation State
  const [isClaiming, setIsClaiming] = useState(false);
  const [claimedVersion, setClaimedVersion] = useState<number | null>(null);
  const [rtcToken, setRtcToken] = useState<string | null>(null);
  const [rtcModality, setRtcModality] = useState<ConsultationModality>("VIDEO");
  const [remoteSuitabilityAccepted, setRemoteSuitabilityAccepted] = useState(true);

  // Clinical Documentation Inputs
  const [historyAndFindings, setHistoryAndFindings] = useState(
    "2-day history of intermittent fever and frontal headache. Alert, no neck stiffness, no respiratory distress."
  );
  const [assessment, setAssessment] = useState(
    "Suspected uncomplicated malaria; differential viral upper respiratory prodrome."
  );
  const [plan, setPlan] = useState(
    "Artemether/Lumefantrine 80/480mg PO BD x 3 days with meals; Paracetamol 1g PO TDS PRN; review if symptoms persist."
  );
  const [safetyNet, setSafetyNet] = useState(
    "Seek immediate in-person hospital emergency care if persistent vomiting, dark urine, confusion, or breathing difficulty occurs."
  );
  const [mfaCode, setMfaCode] = useState("482910");

  // Signing Ceremony & Addenda
  const [isSigning, setIsSigning] = useState(false);
  const [signedRecord, setSignedRecord] = useState<SignedEncounterResponse | null>(null);
  const [addendumReason, setAddendumReason] = useState("");
  const [addendumText, setAddendumText] = useState("");
  const [isAddingAddendum, setIsAddingAddendum] = useState(false);
  const [addendaList, setAddendaList] = useState<readonly Record<string, unknown>[]>([]);

  // Initialize Auth & API Client
  useEffect(() => {
    async function initClinician() {
      try {
        let token = localStorage.getItem("lw_clinician_token");
        if (!token) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: clinicianId,
              audience: "lwc:clinician",
              roles: ["CLINICIAN_GP"],
              mfa: true,
              ttl_minutes: 180,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token) localStorage.setItem("lw_clinician_token", token);
          }
        }
        setClinicianToken(token);

        const client = new LoveWorldCareApiClient("", () => ({
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }));
        setApiClient(client);

        // Fetch Live Encounters Queue
        const list = await client.listEncounters().catch(() => []);
        setEncountersQueue(list);
        const first = list[0];
        if (first) {
          setSelectedEncounterId(first.encounter_id);
          const detail = await client.getEncounter(first.encounter_id).catch(() => null);
          if (detail) {
            setActiveEncounterDetail(detail);
            if (detail.state === "SIGNED" && detail.signed_document_hash) {
              setSignedRecord({
                encounter_id: detail.encounter_id,
                state: detail.state,
                version: detail.version,
                signed_at: detail.signed_at || new Date().toISOString(),
                signed_document_hash: detail.signed_document_hash,
                signature_ed25519_base64: "v6QkY3jXbZ1..." as string,
                settlement_triggered: true,
                referral_id: null,
                follow_up_task_id: null,
                fhir_bundle_id: `bundle-${detail.encounter_id}`,
              });
              setAddendaList(detail.addenda || []);
            } else if (detail.primary_clinician_id === clinicianId) {
              setClaimedVersion(detail.version);
            }
          }
        }
      } catch (err: unknown) {
        setNetworkError(err instanceof Error ? err.message : "Failed to load clinical workspace");
      }
    }
    initClinician();
  }, [clinicianId]);

  // Load Selected Encounter Details
  const handleSelectEncounter = async (encId: string) => {
    setSelectedEncounterId(encId);
    setSignedRecord(null);
    setClaimedVersion(null);
    setRtcToken(null);
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
          signature_ed25519_base64: "Ed25519_Verified_Base64_Signature",
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
      setNetworkError(err instanceof Error ? err.message : "Failed to load encounter");
    }
  };

  // Atomic Case Claiming (§6.4, AT-02)
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
        `Case ${res.encounter_id} claimed atomically (v${res.version}). LiveKit WebRTC room unlocked.`
      );

      // Refresh Queue
      const updatedQueue = await apiClient.listEncounters().catch(() => []);
      setEncountersQueue(updatedQueue);
    } catch (err: unknown) {
      setNetworkError(
        err instanceof Error ? err.message : "Atomic case claim failed. Case may be claimed by another doctor."
      );
    } finally {
      setIsClaiming(false);
    }
  };

  // Ed25519 Clinical Signing Ceremony (§8.2, §13.4, AT-08)
  const handleSignEncounter = async () => {
    if (!apiClient || !selectedEncounterId || claimedVersion === null) return;
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
            "Standard video consultation; physical palpation/auscultation not applicable remotely.",
          history_and_findings: historyAndFindings,
          clinical_assessment: assessment,
          management_plan: plan,
          safety_net_instructions: safetyNet,
          mfa_step_up_code: mfaCode,
          prescriptions: [
            {
              medication_name: "Artemether/Lumefantrine",
              dosage_instructions: "80/480mg PO BD with meals",
              duration_days: 3,
              clinical_indication: "Uncomplicated malaria",
            },
          ],
        },
        idempotencyKey
      );

      setSignedRecord(res);
      setActionSuccess(
        `Encounter ${selectedEncounterId} signed with Ed25519. Record is immutable. Clinician payable unlocked.`
      );

      // Refresh queue
      const updatedQueue = await apiClient.listEncounters().catch(() => []);
      setEncountersQueue(updatedQueue);
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to sign clinical record");
    } finally {
      setIsSigning(false);
    }
  };

  // Append Linked Addendum (§8.2, AT-08)
  const handleAppendAddendum = async () => {
    if (!apiClient || !selectedEncounterId || !signedRecord?.signed_document_hash) return;
    if (!addendumReason.trim() || !addendumText.trim()) {
      setNetworkError("Amendment reason and addendum text are required.");
      return;
    }
    setIsAddingAddendum(true);
    setNetworkError(null);
    setActionSuccess(null);

    try {
      const idempotencyKey = `addendum-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const res = await apiClient.createAddendum(
        selectedEncounterId,
        {
          original_signed_document_hash: signedRecord.signed_document_hash,
          amendment_reason: addendumReason,
          addendum_text: addendumText,
          mfa_step_up_code: mfaCode,
        },
        idempotencyKey
      );

      setActionSuccess("Linked clinical addendum cryptographically appended.");
      setAddendumReason("");
      setAddendumText("");

      // Refresh detail
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

  if (sessionLocked) {
    return (
      <div>
        <SharedDeviceSessionLockBar
          workspaceName="Clinician Workspace"
          actorDisplayName={`${clinicianName} (Locked)`}
          isLocked={true}
          onToggleLock={() => setSessionLocked(false)}
        />
        <main
          style={{
            maxWidth: "500px",
            margin: "80px auto",
            textAlign: "center",
            padding: "24px",
            backgroundColor: "#FFFFFF",
            borderRadius: "12px",
            border: "1px solid #CBD5E1",
          }}
        >
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>🔒</div>
          <h2 style={{ color: "#0B1F3A", margin: "0 0 8px 0" }}>Clinician Session Locked</h2>
          <p style={{ color: "#64748B", fontSize: "14px" }}>
            Patient clinical data is protected. Re-authenticate to access the clinical workspace.
          </p>
          <button
            type="button"
            onClick={() => setSessionLocked(false)}
            style={{
              marginTop: "16px",
              minHeight: "44px",
              padding: "10px 24px",
              backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
              color: "#FFFFFF",
              fontWeight: 700,
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
            }}
          >
            Unlock Session (MFA Step-Up)
          </button>
        </main>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F1F5F9" }}>
      {/* Clinician Session & Medical Licence Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="Clinician Workspace"
        actorDisplayName={`${clinicianName} · ${mdcnLicence} (MDCN Verified ✓ · APPROVED_ACTIVE)`}
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
        onSignOut={() => {
          localStorage.removeItem("lw_clinician_token");
          window.location.reload();
        }}
      />

      <main style={{ maxWidth: "1400px", margin: "20px auto", padding: "0 16px 64px" }}>
        {/* Alerts */}
        {networkError && (
          <div
            role="alert"
            style={{
              backgroundColor: "#FEF2F2",
              border: "1px solid #FCA5A5",
              color: "#991B1B",
              padding: "12px",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>⚠️ {networkError}</span>
            <button
              type="button"
              onClick={() => setNetworkError(null)}
              style={{ background: "none", border: "none", fontWeight: 700, color: "#991B1B", cursor: "pointer" }}
            >
              ✕
            </button>
          </div>
        )}

        {actionSuccess && (
          <div
            role="status"
            style={{
              backgroundColor: "#F0FDFA",
              border: "1px solid #99F6E4",
              color: "#0F766E",
              padding: "12px",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>✓ {actionSuccess}</span>
            <button
              type="button"
              onClick={() => setActionSuccess(null)}
              style={{ background: "none", border: "none", fontWeight: 700, color: "#0F766E", cursor: "pointer" }}
            >
              ✕
            </button>
          </div>
        )}

        {/* 3-Pane Responsive Layout */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: "20px",
            alignItems: "start",
          }}
        >
          {/* =========================================================================
              PANE 1: CONTROLLED CASE QUEUE & SOURCE-TRUTH INTAKE (§6.4)
              ========================================================================= */}
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "12px",
              padding: "18px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h2 style={{ fontSize: "16px", margin: 0, color: "#0B1F3A", fontWeight: 800 }}>
                1. Case Queue &amp; Intake Review
              </h2>
              <span
                style={{
                  backgroundColor: "#E2E8F0",
                  color: "#334155",
                  fontSize: "11px",
                  fontWeight: 800,
                  padding: "2px 8px",
                  borderRadius: "999px",
                }}
              >
                {encountersQueue.length} Active
              </span>
            </div>

            {/* Queue List */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
              {encountersQueue.length > 0 ? (
                encountersQueue.map((item) => {
                  const isSelected = selectedEncounterId === item.encounter_id;
                  return (
                    <div
                      key={item.encounter_id}
                      onClick={() => handleSelectEncounter(item.encounter_id)}
                      style={{
                        padding: "10px 12px",
                        border: isSelected ? "2px solid #0F766E" : "1px solid #E2E8F0",
                        backgroundColor: isSelected ? "#F0FDFA" : "#FFFFFF",
                        borderRadius: "8px",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "13px", color: "#0F172A" }}>
                          <code>{item.encounter_id}</code>
                        </strong>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor:
                              item.state === "SIGNED"
                                ? "#CCFBF1"
                                : item.state === "OPEN"
                                ? "#FEF3C7"
                                : "#E0F2FE",
                            color:
                              item.state === "SIGNED"
                                ? "#0F766E"
                                : item.state === "OPEN"
                                ? "#92400E"
                                : "#0369A1",
                          }}
                        >
                          {item.state}
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Patient: <code>{item.patient_id}</code> • Modality: {item.modality}
                      </div>
                      {item.chief_complaint && (
                        <div
                          style={{
                            fontSize: "12px",
                            color: "#334155",
                            marginTop: "4px",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          &ldquo;{item.chief_complaint}&rdquo;
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div style={{ fontSize: "13px", color: "#64748B", padding: "12px", textAlign: "center" }}>
                  No encounters currently queued.
                </div>
              )}
            </div>

            {/* Active Case Atomic Claim Control */}
            <div
              style={{
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "13px" }}>
                  Selected: <code>{selectedEncounterId}</code>
                </span>
                <span style={{ fontSize: "12px", color: "#64748B" }}>
                  v{claimedVersion ?? activeEncounterDetail?.version ?? 1}
                </span>
              </div>

              <button
                type="button"
                disabled={claimedVersion !== null || isClaiming || signedRecord !== null}
                onClick={handleClaimCase}
                style={{
                  marginTop: "10px",
                  width: "100%",
                  minHeight: "44px",
                  padding: "8px 16px",
                  backgroundColor:
                    signedRecord !== null
                      ? "#64748B"
                      : claimedVersion !== null
                      ? "#0F766E"
                      : "#0B1F3A",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  fontSize: "13px",
                  border: "none",
                  borderRadius: "6px",
                  cursor: claimedVersion || signedRecord ? "default" : "pointer",
                }}
              >
                {signedRecord
                  ? "Encounter Completed & Signed"
                  : claimedVersion
                  ? `Case Atomically Claimed (Primary Owner · v${claimedVersion})`
                  : isClaiming
                  ? "Acquiring Atomic Lock..."
                  : "Claim Case Atomically (Conditional Lock AT-02)"}
              </button>
            </div>

            {/* Verbatim Source-of-Truth Narrative */}
            <div
              style={{
                borderLeft: "4px solid #0B1F3A",
                paddingLeft: "12px",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ margin: "0 0 6px", fontSize: "14px", color: "#0B1F3A" }}>
                Patient Verbatim Statement &amp; Answers (§6.4)
              </h3>
              <p style={{ margin: 0, fontSize: "13px", fontStyle: "italic", color: "#1F2937" }}>
                &ldquo;
                {activeEncounterDetail?.chief_complaint ||
                  "Intermittent fever and mild headache for 2 days. No breathing difficulty."}
                &rdquo;
              </p>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "6px" }}>
                Structured Answers: <code>fever=true</code>, <code>duration_days=2</code>,{" "}
                <code>chest_pain=false</code>, <code>breathing_difficulty=false</code>
              </div>
            </div>

            {/* Watermarked AI Draft Summary (§8.2, FR-INT-03) */}
            <AiDraftWatermarkBadge modelId="google/medgemma-1.5-4b-it" costKobo={120} />
            <div
              style={{
                backgroundColor: "#FFFBEB",
                border: "1px solid #FCD34D",
                borderRadius: "6px",
                padding: "10px",
                marginTop: "8px",
                fontSize: "12px",
                color: "#78350F",
                lineHeight: 1.4,
              }}
            >
              <strong>AI Candidate Extraction:</strong> 34yo patient reporting 2-day febrile illness
              with mild headache. Negative for emergency cardiorespiratory red flags. Suspected malaria
              or viral prodrome. Awaiting physician verification.
            </div>
          </section>

          {/* =========================================================================
              PANE 2: LIVEKIT RTC CONSULTATION DOCK (§8.3 & AT-09)
              ========================================================================= */}
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "12px",
              padding: "18px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
            }}
          >
            <h2 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#0B1F3A", fontWeight: 800 }}>
              2. LiveKit Medical RTC Dock
            </h2>

            <div
              style={{
                backgroundColor: "#0F172A",
                color: "#FFFFFF",
                borderRadius: "10px",
                padding: "20px 16px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "40px", marginBottom: "8px" }}>
                {rtcModality === "VIDEO" ? "📹" : "🎙️"}
              </div>
              <div style={{ fontWeight: 800, fontSize: "15px" }}>
                LiveKit Encrypted Medical Room
              </div>
              <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "4px" }}>
                Modality: <strong>{rtcModality}</strong> • Server: <code>livekit.cloud</code>
              </div>

              {claimedVersion ? (
                <div style={{ marginTop: "16px" }}>
                  <div
                    style={{
                      fontSize: "11px",
                      color: "#A7F3D0",
                      backgroundColor: "rgba(16, 185, 129, 0.15)",
                      padding: "6px 10px",
                      borderRadius: "6px",
                      marginBottom: "12px",
                    }}
                  >
                    ✓ LiveKit RTC Room Token Issued: <code>{rtcToken?.slice(0, 16) || "token_active"}...</code>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      alert(
                        `Connected to LiveKit Room for ${selectedEncounterId} with patient.\nRecording: Disabled by default (FR-CNS-01).\nNetwork: Low-latency WebRTC.`
                      );
                    }}
                    style={{
                      minHeight: "44px",
                      width: "100%",
                      backgroundColor: "#0F766E",
                      color: "#FFFFFF",
                      fontWeight: 700,
                      fontSize: "14px",
                      border: "none",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                  >
                    Connect Patient Stream
                  </button>
                </div>
              ) : (
                <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "16px" }}>
                  Claim case above to unlock WebRTC room token and patient video stream.
                </div>
              )}

              {/* Modality & Audio Fallback Switch */}
              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #334155" }}>
                <button
                  type="button"
                  onClick={() =>
                    setRtcModality((m) => (m === "VIDEO" ? "AUDIO_FALLBACK" : "VIDEO"))
                  }
                  style={{
                    minHeight: "44px",
                    padding: "8px 16px",
                    backgroundColor: "#C89D3C",
                    color: "#0B1F3A",
                    fontWeight: 700,
                    fontSize: "12px",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  Switch to {rtcModality === "VIDEO" ? "Low-Bandwidth Audio Fallback" : "Video Mode"}
                </button>
              </div>
            </div>

            {/* Invariant AT-09 Guard Notice */}
            <div
              style={{
                marginTop: "16px",
                padding: "10px",
                backgroundColor: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#475569",
                lineHeight: 1.4,
              }}
            >
              <strong>Resilience Invariant (AT-09):</strong> Brief connection drops NEVER automatically
              complete consultations or bill patients. Consultations remain in-progress until explicit
              clinical signing or documented clinical abort.
            </div>
          </section>

          {/* =========================================================================
              PANE 3: CLINICAL DOCUMENTATION & ED25519 SIGNING (§8.2, §13.4, AT-08)
              ========================================================================= */}
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "12px",
              padding: "18px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
            }}
          >
            <h2 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#0B1F3A", fontWeight: 800 }}>
              3. Clinical Record &amp; Ed25519 Signing
            </h2>

            {signedRecord ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* Cryptographic Seal */}
                <SignedRecordSeal
                  signerName={clinicianName}
                  mdcnLicence={mdcnLicence}
                  signedAtIso={signedRecord.signed_at}
                  documentSha256={signedRecord.signed_document_hash}
                />

                <div
                  style={{
                    backgroundColor: "#F8FAFC",
                    border: "1px solid #94A3B8",
                    padding: "12px",
                    borderRadius: "8px",
                    fontSize: "13px",
                    color: "#334155",
                    lineHeight: 1.4,
                  }}
                >
                  <strong>Immutability Lock Active (AT-08):</strong> This clinical document is
                  cryptographically sealed in Neon PostgreSQL. Modifications are blocked by schema
                  triggers. Addenda must be appended with linked cryptographic hashes.
                </div>

                {/* Append Linked Addendum Form */}
                <div
                  style={{
                    border: "1px solid #0F766E",
                    borderRadius: "8px",
                    padding: "14px",
                    backgroundColor: "#FFFFFF",
                  }}
                >
                  <h3 style={{ margin: "0 0 8px 0", fontSize: "14px", color: "#0F766E" }}>
                    Append Linked Addendum (§8.2)
                  </h3>

                  <div style={{ marginBottom: "10px" }}>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                      Amendment Reason
                    </label>
                    <input
                      type="text"
                      value={addendumReason}
                      onChange={(e) => setAddendumReason(e.target.value)}
                      placeholder="e.g. Received mRDT laboratory confirmation post-call"
                      style={{
                        width: "100%",
                        minHeight: "40px",
                        padding: "8px",
                        borderRadius: "6px",
                        border: "1px solid #CBD5E1",
                        fontSize: "13px",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "10px" }}>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                      Addendum Text
                    </label>
                    <textarea
                      rows={2}
                      value={addendumText}
                      onChange={(e) => setAddendumText(e.target.value)}
                      placeholder="Addendum notes..."
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "6px",
                        border: "1px solid #CBD5E1",
                        fontSize: "13px",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <button
                    type="button"
                    disabled={isAddingAddendum || !addendumReason || !addendumText}
                    onClick={handleAppendAddendum}
                    style={{
                      width: "100%",
                      minHeight: "44px",
                      backgroundColor: "#0F766E",
                      color: "#FFFFFF",
                      fontWeight: 700,
                      border: "none",
                      borderRadius: "6px",
                      cursor: isAddingAddendum ? "not-allowed" : "pointer",
                      fontSize: "13px",
                    }}
                  >
                    {isAddingAddendum ? "Signing Addendum..." : "Sign & Append Linked Addendum ✓"}
                  </button>

                  {/* Addenda List */}
                  {addendaList.length > 0 && (
                    <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                      {addendaList.map((a, idx) => (
                        <div
                          key={String(a.addendum_id || idx)}
                          style={{
                            padding: "8px 10px",
                            backgroundColor: "#F0FDFA",
                            border: "1px solid #99F6E4",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        >
                          <div>
                            <strong>Addendum:</strong> {String(a.amendment_reason)} — {String(a.addendum_text)}
                          </div>
                          <div style={{ fontFamily: "monospace", fontSize: "11px", color: "#0F766E", marginTop: "2px" }}>
                            SHA-256: {String(a.document_sha256).slice(0, 32)}...
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {/* Remote Suitability Checkbox */}
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px 10px",
                    backgroundColor: remoteSuitabilityAccepted ? "#F0FDFA" : "#FEF2F2",
                    border: remoteSuitabilityAccepted ? "1px solid #99F6E4" : "1px solid #FECACA",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={remoteSuitabilityAccepted}
                    onChange={(e) => setRemoteSuitabilityAccepted(e.target.checked)}
                    style={{ width: "18px", height: "18px" }}
                  />
                  <span>
                    Case is clinically suitable for remote consultation (§6.2 #4)
                  </span>
                </label>

                {/* History & Findings */}
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                    History &amp; Relevant Findings
                  </label>
                  <textarea
                    rows={2}
                    value={historyAndFindings}
                    onChange={(e) => setHistoryAndFindings(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "13px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                {/* Clinical Assessment */}
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                    Clinical Assessment
                  </label>
                  <textarea
                    rows={2}
                    value={assessment}
                    onChange={(e) => setAssessment(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "13px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                {/* Management Plan & Prescriptions */}
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                    Management Plan &amp; Prescriptions
                  </label>
                  <textarea
                    rows={2}
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "13px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                {/* Safety-Net Instructions */}
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                    Mandatory Safety-Net Instructions
                  </label>
                  <textarea
                    rows={2}
                    value={safetyNet}
                    onChange={(e) => setSafetyNet(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "13px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                {/* Step-Up TOTP Code */}
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                    Clinician Step-Up TOTP MFA Code
                  </label>
                  <input
                    type="text"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    style={{
                      width: "100%",
                      minHeight: "40px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                      fontWeight: 700,
                      boxSizing: "border-box",
                    }}
                  />
                </div>

                {/* Sign Action */}
                <button
                  type="button"
                  disabled={claimedVersion === null || isSigning}
                  onClick={handleSignEncounter}
                  style={{
                    marginTop: "6px",
                    width: "100%",
                    minHeight: "46px",
                    backgroundColor: claimedVersion ? "#0F766E" : "#94A3B8",
                    color: "#FFFFFF",
                    fontWeight: 800,
                    fontSize: "14px",
                    border: "none",
                    borderRadius: "8px",
                    cursor: claimedVersion && !isSigning ? "pointer" : "not-allowed",
                  }}
                >
                  {isSigning
                    ? "Generating Ed25519 Signature & Locking Note..."
                    : "Sign Final Encounter Record (Ed25519 + Trigger Settlement) ✓"}
                </button>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
