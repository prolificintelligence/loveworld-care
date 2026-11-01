"use client";

import React, { useState } from "react";
import {
  AiDraftWatermarkBadge,
  SharedDeviceSessionLockBar,
  SignedRecordSeal,
} from "@loveworld-care/design-system";

export default function ClinicianWorkspacePage() {
  const [sessionLocked, setSessionLocked] = useState(false);
  const [claimedVersion, setClaimedVersion] = useState<number | null>(null);
  const [rtcModality, setRtcModality] = useState<"VIDEO" | "AUDIO_FALLBACK">("VIDEO");
  const [remoteSuitabilityAccepted, setRemoteSuitabilityAccepted] = useState(true);
  const [historyAndFindings, setHistoryAndFindings] = useState(
    "2-day history of intermittent fever and frontal headache. Alert, no neck stiffness, no dyspnea."
  );
  const [assessment, setAssessment] = useState(
    "Suspected uncomplicated malaria; differential viral upper respiratory prodrome."
  );
  const [plan, setPlan] = useState(
    "Refer for rapid diagnostic test (mRDT) at participating clinic; paracetamol 1g PO PRN; review with results."
  );
  const [safetyNet, setSafetyNet] = useState(
    "Attend emergency room immediately if persistent vomiting, confusion, dark urine, or shortness of breath develops."
  );
  const [mfaCode, setMfaCode] = useState("482910");
  const [signedHash, setSignedHash] = useState<string | null>(null);
  const [addendumReason, setAddendumReason] = useState("");
  const [addendumText, setAddendumText] = useState("");
  const [addendaList, setAddendaList] = useState<
    { reason: string; text: string; hash: string; signedAt: string }[]
  >([]);

  if (sessionLocked) {
    return (
      <div>
        <SharedDeviceSessionLockBar
          workspaceName="Clinician Workspace"
          actorDisplayName="Dr. Adebayo Okonkwo (Session Locked)"
          isLocked={true}
          onToggleLock={() => setSessionLocked(false)}
        />
      </div>
    );
  }

  return (
    <div>
      <SharedDeviceSessionLockBar
        workspaceName="Clinician PWA"
        actorDisplayName="Dr. Adebayo Okonkwo · MDCN/R/44210 (APPROVED_ACTIVE · MFA Verified)"
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
      />

      <main style={{ maxWidth: "1200px", margin: "24px auto", padding: "0 16px 64px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
            gap: "24px",
          }}
        >
          {/* Left Column: Controlled Case Queue, Raw Patient Statement & Watermarked AI Draft (§6.4) */}
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "10px",
              padding: "20px",
            }}
          >
            <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
              1. Controlled Queue & Source-Truth Intake Review (§6.4)
            </h2>
            <div
              style={{
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontWeight: 700 }}>
                Encounter <code>ENC-NG-88412</code> · Service: DoctorNow GP Remote
              </div>
              <div style={{ fontSize: "13px", color: "#334155", marginTop: "4px" }}>
                Protocol Run: <code>LW-NG-GP-ADULT-V1 (v1.0.0)</code> · Outcome:{" "}
                <strong>CLINICIAN_REVIEW</strong> · Fired Rule: <code>RT-STANDARD-GP-02</code>
              </div>
              <div style={{ marginTop: "10px" }}>
                <button
                  type="button"
                  disabled={claimedVersion !== null}
                  onClick={() => setClaimedVersion(2)}
                  style={{
                    minHeight: "44px",
                    padding: "8px 16px",
                    backgroundColor: claimedVersion ? "#0F766E" : "#0B1F3A",
                    color: "#FFFFFF",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "6px",
                    cursor: claimedVersion ? "default" : "pointer",
                  }}
                >
                  {claimedVersion
                    ? `Case Atomically Claimed (Primary Owner · v${claimedVersion})`
                    : "Claim Case Atomically (Conditional Lock AT-02)"}
                </button>
              </div>
            </div>

            <div
              style={{
                borderLeft: "4px solid #0B1F3A",
                paddingLeft: "12px",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>
                Original Patient Verbatim Statement & Structured Answers (Source of Truth)
              </h3>
              <p style={{ margin: 0, fontSize: "14px", fontStyle: "italic" }}>
                &ldquo;Intermittent fever and mild headache for 2 days.&rdquo;
              </p>
              <div style={{ fontSize: "12px", color: "#475569", marginTop: "6px" }}>
                Structured Fields: <code>patient_age_years=34</code>,{" "}
                <code>severe_chest_pain_or_pressure=false</code>,{" "}
                <code>acute_breathing_difficulty=false</code>,{" "}
                <code>symptom_duration_days=2</code>
              </div>
            </div>

            <AiDraftWatermarkBadge modelId="google/medgemma-1.5-4b-it" costKobo={120} />
            <div
              style={{
                backgroundColor: "#FFFBEB",
                border: "1px solid #FCD34D",
                borderRadius: "6px",
                padding: "10px",
                marginTop: "8px",
                fontSize: "13px",
              }}
            >
              <strong>AI Extracted Candidate Summary:</strong> Adult patient reporting 2-day history
              of febrile symptoms and headache; negative for cardio-respiratory hard-stop red flags.
            </div>

            {/* LiveKit WebRTC Room & Low-Bandwidth Audio Fallback (§8.3 & AT-09) */}
            <div
              style={{
                marginTop: "16px",
                padding: "12px",
                backgroundColor: "#0F172A",
                color: "#FFFFFF",
                borderRadius: "8px",
              }}
            >
              <div style={{ fontWeight: 700, fontSize: "14px" }}>
                LiveKit Secure Consultation Room (Recording Disabled by Default — FR-CNS-01)
              </div>
              <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "4px" }}>
                Active Modality: <strong>{rtcModality}</strong> · Brief connection drop NEVER triggers
                auto-billing (AT-09).
              </div>
              <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() =>
                    setRtcModality((m) => (m === "VIDEO" ? "AUDIO_FALLBACK" : "VIDEO"))
                  }
                  style={{
                    minHeight: "44px",
                    padding: "8px 14px",
                    backgroundColor: "#C89D3C",
                    color: "#0B1F3A",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  Switch to {rtcModality === "VIDEO" ? "Low-Bandwidth Audio Fallback" : "Video Mode"}
                </button>
              </div>
            </div>
          </section>

          {/* Right Column: Clinical Documentation, Ed25519 Signing & Immutable Addenda (§8.2, §13.4, AT-08) */}
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "10px",
              padding: "20px",
            }}
          >
            <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
              2. Clinical Documentation, Ed25519 Signature & Addenda
            </h2>

            {signedHash ? (
              <div style={{ display: "grid", gap: "16px" }}>
                <SignedRecordSeal
                  signerName="Dr. Adebayo Okonkwo"
                  mdcnLicence="MDCN/R/44210"
                  signedAtIso={new Date().toISOString()}
                  documentSha256={signedHash}
                />
                <div
                  style={{
                    backgroundColor: "#F8FAFC",
                    border: "1px solid #94A3B8",
                    padding: "12px",
                    borderRadius: "6px",
                    fontSize: "13px",
                  }}
                >
                  <strong>Immutability Lock Active (AT-08):</strong> The original signed encounter
                  note above is permanently locked against editing. Any clinical clarification or
                  correction must be appended as a cryptographically signed addendum below.
                </div>

                {/* Append-Only Signed Addendum Builder */}
                <div
                  style={{
                    border: "1px solid #0B1F3A",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <h3 style={{ marginTop: 0, fontSize: "15px" }}>
                    Append Signed Clinical Addendum (Linked to Original Hash)
                  </h3>
                  <label style={{ display: "block", fontWeight: 600, fontSize: "13px", marginBottom: "8px" }}>
                    Amendment Reason
                    <input
                      type="text"
                      value={addendumReason}
                      onChange={(e) => setAddendumReason(e.target.value)}
                      placeholder="e.g., Lab result received post-consultation"
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
                  <label style={{ display: "block", fontWeight: 600, fontSize: "13px", marginBottom: "8px" }}>
                    Addendum Text
                    <textarea
                      rows={2}
                      value={addendumText}
                      onChange={(e) => setAddendumText(e.target.value)}
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
                    onClick={() => {
                      if (!addendumReason || !addendumText) return;
                      setAddendaList((prev) => [
                        ...prev,
                        {
                          reason: addendumReason,
                          text: addendumText,
                          hash: `addendum_sha256_${Date.now().toString(16)}`,
                          signedAt: new Date().toISOString(),
                        },
                      ]);
                      setAddendumReason("");
                      setAddendumText("");
                    }}
                    style={{
                      minHeight: "44px",
                      padding: "8px 16px",
                      backgroundColor: "#0B1F3A",
                      color: "#FFFFFF",
                      fontWeight: 700,
                      border: "none",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                  >
                    Sign & Append Linked Addendum
                  </button>

                  {addendaList.map((a) => (
                    <div
                      key={a.hash}
                      style={{
                        marginTop: "10px",
                        padding: "10px",
                        backgroundColor: "#F0FDFA",
                        border: "1px solid #0F766E",
                        borderRadius: "6px",
                        fontSize: "12px",
                      }}
                    >
                      <div>
                        <strong>Addendum ({a.signedAt}):</strong> {a.reason} — {a.text}
                      </div>
                      <div style={{ fontFamily: "monospace" }}>
                        Links to Original SHA-256: {signedHash.slice(0, 24)}... | Addendum SHA-256:{" "}
                        {a.hash}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                <label style={{ display: "flex", alignItems: "center", minHeight: "44px", gap: "8px", fontWeight: 600 }}>
                  <input
                    type="checkbox"
                    checked={remoteSuitabilityAccepted}
                    onChange={(e) => setRemoteSuitabilityAccepted(e.target.checked)}
                  />
                  Remote Consultation Clinically Suitable (§6.2 #4: Uncheck to decline remote
                  suitability, issue in-person referral & release sponsor reservation)
                </label>

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  History & Relevant Findings
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
                  Management Plan, Prescriptions & Referral (SpecialistBridge / Facility)
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
                  Mandatory Safety-Net & Escalation Instructions
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

                <label style={{ fontWeight: 600, fontSize: "14px" }}>
                  Clinician Step-Up TOTP MFA Code (Required for Cryptographic Signing)
                  <input
                    type="text"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
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

                <button
                  type="button"
                  disabled={claimedVersion === null}
                  onClick={() =>
                    setSignedHash(
                      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                    )
                  }
                  style={{
                    minHeight: "44px",
                    padding: "12px 20px",
                    backgroundColor: claimedVersion ? "#0F766E" : "#94A3B8",
                    color: "#FFFFFF",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "6px",
                    cursor: claimedVersion ? "pointer" : "not-allowed",
                  }}
                >
                  Sign Final Encounter Record (Ed25519 + Trigger Settlement)
                </button>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
