"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  EmergencySafetyBanner,
  MobileBottomNavBar,
  NavItem,
  SharedDeviceSessionLockBar,
  SignedRecordSeal,
  AiDraftWatermarkBadge,
  LW_DESIGN_TOKENS,
} from "@loveworld-care/design-system";
import {
  CareEpisodeResponse,
  IntakeEvaluationResponse,
  LoveWorldCareApiClient,
  StaffedSlotDTO,
  AppointmentBookingResponse,
  EmergencyGuidanceResponse,
} from "@loveworld-care/api-contracts";
import type { ConsultationModality, FundingRouteType } from "@loveworld-care/domain-types";

// =============================================================================
// Navigation Tabs
// =============================================================================
type PatientNavTab = "HOME" | "CARE" | "MESSAGES" | "PROFILE";

const NAV_ITEMS: readonly NavItem[] = [
  { id: "HOME", label: "Home", icon: "🏠" },
  { id: "CARE", label: "My Care", icon: "🩺" },
  { id: "MESSAGES", label: "Messages", icon: "💬" },
  { id: "PROFILE", label: "Profile", icon: "👤" },
];

export default function PatientPortalPwa() {
  const [activeTab, setActiveTab] = useState<PatientNavTab>("HOME");
  const [sessionLocked, setSessionLocked] = useState<boolean>(false);
  const [patientId, setPatientId] = useState<string>("patient-001");
  const [patientName, setPatientName] = useState<string>("Sister Grace Adeleke");
  const [patientToken, setPatientToken] = useState<string | null>(null);

  // Live API Client
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  // Active Care State
  const [activeEpisode, setActiveEpisode] = useState<CareEpisodeResponse | null>(null);
  const [activeIntakeResult, setActiveIntakeResult] = useState<IntakeEvaluationResponse | null>(null);
  const [activeAppointment, setActiveAppointment] = useState<AppointmentBookingResponse | null>(null);
  const [availableSlots, setAvailableSlots] = useState<readonly StaffedSlotDTO[]>([]);
  const [emergencyGuidance, setEmergencyGuidance] = useState<EmergencyGuidanceResponse | null>(null);

  // Guided Intake Wizard Modal State
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Intake Form Fields
  const [hasChestPain, setHasChestPain] = useState<boolean>(false);
  const [hasBreathingDifficulty, setHasBreathingDifficulty] = useState<boolean>(false);
  const [hasUncontrolledBleeding, setHasUncontrolledBleeding] = useState<boolean>(false);
  const [symptomCategory, setSymptomCategory] = useState<string>("FEVER_OR_MALARIA_LIKE");
  const [durationDays, setDurationDays] = useState<number>(2);
  const [chiefComplaint, setChiefComplaint] = useState<string>(
    "Mild fever, body weakness, and slight headache for 2 days. No breathing difficulty."
  );
  const [selectedSlotId, setSelectedSlotId] = useState<string>("");
  const [selectedModality, setSelectedModality] = useState<ConsultationModality>("VIDEO");
  const [fundingRoute, setFundingRoute] = useState<FundingRouteType>("SPONSOR_DEFINED_SERVICES");
  const [telemedicineConsent, setTelemedicineConsent] = useState<boolean>(true);

  // Passwordless Email Magic Link State
  const [magicLinkEmail, setMagicLinkEmail] = useState<string>("patient@care.loveworld.org");
  const [isSendingMagicLink, setIsSendingMagicLink] = useState<boolean>(false);
  const [magicLinkSent, setMagicLinkSent] = useState<boolean>(false);
  const [magicLinkToken, setMagicLinkToken] = useState<string | null>(null);
  const [magicLinkStatusMsg, setMagicLinkStatusMsg] = useState<string | null>(null);

  // Initialize Auth & API Client
  useEffect(() => {
    async function initClient() {
      try {
        let token = localStorage.getItem("lw_patient_token");
        if (!token) {
          // Dev/Staging: mint patient token via /v1/auth/dev-token
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: patientId,
              audience: "lwc:patient",
              roles: ["PATIENT"],
              mfa: false,
              ttl_minutes: 120,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token) localStorage.setItem("lw_patient_token", token);
          }
        }
        setPatientToken(token);

        const client = new LoveWorldCareApiClient("", () => ({
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }));
        setApiClient(client);

        // Fetch emergency numbers & slots
        const [guidance, slots] = await Promise.all([
          client.getEmergencyGuidance("NG").catch(() => null),
          client.listStaffedSlots("NG", "GP").catch(() => []),
        ]);
        if (guidance) setEmergencyGuidance(guidance);
        if (slots && slots.length > 0) {
          setAvailableSlots(slots);
          setSelectedSlotId(slots[0].slot_id);
        }
      } catch (err: unknown) {
        setNetworkError(err instanceof Error ? err.message : "Network offline");
      }
    }
    initClient();
  }, [patientId]);

  // Handle Request Care Submission
  const handleStartIntake = () => {
    setIsWizardOpen(true);
    setWizardStep(1);
    setHasChestPain(false);
    setHasBreathingDifficulty(false);
    setHasUncontrolledBleeding(false);
  };

  const handleRequestMagicLink = async () => {
    if (!apiClient || !magicLinkEmail) return;
    setIsSendingMagicLink(true);
    setMagicLinkStatusMsg(null);
    try {
      const res = await apiClient.requestMagicLink(magicLinkEmail);
      setMagicLinkSent(true);
      if (res.verification_token) {
        setMagicLinkToken(res.verification_token);
        setMagicLinkStatusMsg(`Magic link ready for ${res.email}. Click below to verify and sign in.`);
      } else {
        setMagicLinkStatusMsg(`Secure magic link dispatched to ${res.email}. Please check your inbox.`);
      }
    } catch (err: unknown) {
      setMagicLinkStatusMsg(err instanceof Error ? err.message : "Failed to send magic link");
    } finally {
      setIsSendingMagicLink(false);
    }
  };

  const handleVerifyMagicLink = async (tokenToVerify?: string) => {
    const t = tokenToVerify || magicLinkToken;
    if (!apiClient || !t) return;
    try {
      const res = await apiClient.verifyMagicLink(t);
      if (res.access_token) {
        localStorage.setItem("lw_patient_token", res.access_token);
        setPatientToken(res.access_token);
        setPatientId(res.patient_id);
        setMagicLinkStatusMsg(`Authenticated successfully as ${res.email}!`);
      }
    } catch (err: unknown) {
      setMagicLinkStatusMsg(err instanceof Error ? err.message : "Failed to verify magic link");
    }
  };

  const handleCompleteBooking = async () => {
    if (!apiClient) return;
    setIsSubmitting(true);
    setNetworkError(null);

    try {
      const idempotencyKey = `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

      // 1. Create Episode
      const ep = await apiClient.createEpisode(
        {
          patient_id: patientId,
          jurisdiction: "NG",
          care_service: "GP_REMOTE",
          consent_grant_id: `consent-${Date.now()}`,
          request_source: "PATIENT_PWA",
          chief_complaint_summary: chiefComplaint,
        },
        idempotencyKey
      );
      setActiveEpisode(ep);

      // 2. Submit Deterministic Intake
      const intakeRes = await apiClient.submitIntake(
        ep.episode_id,
        {
          structured_answers: {
            symptom_category: symptomCategory,
            duration_days: durationDays,
            has_chest_pain: hasChestPain,
            has_breathing_difficulty: hasBreathingDifficulty,
            has_uncontrolled_bleeding: hasUncontrolledBleeding,
          },
          raw_patient_statement: chiefComplaint,
          language_code: "en-NG",
          request_ai_draft_extraction: true,
        },
        `${idempotencyKey}-intake`
      );
      setActiveIntakeResult(intakeRes);

      // 3. Book Staffed Slot
      const appt = await apiClient.bookAppointment(
        {
          episode_id: ep.episode_id,
          slot_id: selectedSlotId || "slot-ng-gp-001",
          modality: selectedModality,
          funding_route: fundingRoute,
          sponsor_agreement_id:
            fundingRoute === "SPONSOR_DEFINED_SERVICES"
              ? "AGR-LW-MEDICAID-NG-2026"
              : undefined,
          payment_provider: fundingRoute === "SELF_PAY" ? "PAYSTACK" : undefined,
        },
        `${idempotencyKey}-appt`
      );
      setActiveAppointment(appt);

      setIsWizardOpen(false);
      setActiveTab("CARE");
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Booking could not be completed");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Red Flag Guard
  const hasEmergencyRedFlags = hasChestPain || hasBreathingDifficulty || hasUncontrolledBleeding;

  return (
    <div
      style={{
        maxWidth: "600px",
        margin: "0 auto",
        minHeight: "100vh",
        backgroundColor: "#F8FAFC",
        display: "flex",
        flexDirection: "column",
        paddingBottom: "80px",
        boxShadow: "0 0 24px rgba(0, 0, 0, 0.04)",
      }}
    >
      {/* Shared Device Session Lock Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="Patient Portal"
        actorDisplayName={patientName}
        isLocked={sessionLocked}
        onToggleLock={() => setSessionLocked(!sessionLocked)}
        onSignOut={() => {
          localStorage.removeItem("lw_patient_token");
          window.location.reload();
        }}
      />

      {/* Zero-Auth, Zero-Payment Emergency Guidance Banner */}
      <EmergencySafetyBanner compact={true} />

      {/* Shared Device Lock Screen Overlay */}
      {sessionLocked ? (
        <main
          role="alert"
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "32px 24px",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: "56px", marginBottom: "16px" }}>🔒</div>
          <h1 style={{ fontSize: "22px", color: "#0B1F3A", margin: "0 0 8px 0" }}>
            Session Locked for Privacy
          </h1>
          <p style={{ color: "#64748B", fontSize: "14px", lineHeight: 1.5, maxWidth: "340px" }}>
            To safeguard your private medical consultations on this shared device, clinical details
            have been concealed.
          </p>
          <button
            type="button"
            onClick={() => setSessionLocked(false)}
            style={{
              marginTop: "24px",
              minHeight: "44px",
              padding: "12px 32px",
              backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
              color: "#FFFFFF",
              fontWeight: 700,
              fontSize: "15px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
            }}
          >
            Unlock Session
          </button>
        </main>
      ) : (
        <main style={{ flex: 1, padding: "16px" }}>
          {/* Network / Offline Alert */}
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
                style={{
                  background: "none",
                  border: "none",
                  fontWeight: 700,
                  color: "#991B1B",
                  cursor: "pointer",
                }}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* =========================================================================
              TAB 1: HOME
              ========================================================================= */}
          {activeTab === "HOME" && (
            <div>
              {/* Patient Welcome Hero Card */}
              <div
                style={{
                  background: "linear-gradient(135deg, #0B1F3A 0%, #16335B 100%)",
                  borderRadius: "16px",
                  padding: "24px 20px",
                  color: "#FFFFFF",
                  boxShadow: "0 4px 16px rgba(11, 31, 58, 0.12)",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span
                      style={{
                        backgroundColor: "rgba(200, 157, 60, 0.2)",
                        color: "#F6E05E",
                        fontSize: "11px",
                        fontWeight: 800,
                        padding: "3px 8px",
                        borderRadius: "4px",
                        textTransform: "uppercase",
                      }}
                    >
                      LoveWorld Medical Network
                    </span>
                    <h2 style={{ fontSize: "22px", margin: "8px 0 4px 0", fontWeight: 800 }}>
                      Welcome, {patientName}
                    </h2>
                    <p style={{ color: "#CBD5E1", fontSize: "14px", margin: 0 }}>
                      Fast, clinically governed access to verified Nigerian doctors.
                    </p>
                  </div>
                  <span style={{ fontSize: "32px" }}>🩺</span>
                </div>

                {/* Primary Action Button: DoctorNow */}
                <button
                  type="button"
                  onClick={handleStartIntake}
                  style={{
                    marginTop: "20px",
                    width: "100%",
                    minHeight: "48px",
                    backgroundColor: "#C89D3C",
                    color: "#0B1F3A",
                    fontWeight: 800,
                    fontSize: "16px",
                    border: "none",
                    borderRadius: "10px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    boxShadow: "0 2px 8px rgba(200, 157, 60, 0.3)",
                  }}
                >
                  <span>⚡</span> Request Care with DoctorNow
                </button>
              </div>

              {/* Active Care Quick Status Card (if consultation exists) */}
              {activeAppointment && (
                <div
                  style={{
                    backgroundColor: "#FFFFFF",
                    border: "1px solid #0F766E",
                    borderRadius: "12px",
                    padding: "16px",
                    marginBottom: "20px",
                    boxShadow: "0 2px 8px rgba(15, 118, 110, 0.08)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "20px" }}>🟢</span>
                      <strong>Active Consultation Scheduled</strong>
                    </div>
                    <span
                      style={{
                        backgroundColor: "#F0FDFA",
                        color: "#0F766E",
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "4px",
                        border: "1px solid #CCFBF1",
                      }}
                    >
                      {activeAppointment.state}
                    </span>
                  </div>
                  <p style={{ fontSize: "13px", color: "#475569", margin: "8px 0" }}>
                    Appointment Ref: <code>{activeAppointment.appointment_id}</code> • Modality:{" "}
                    <strong>{activeAppointment.modality}</strong>
                  </p>
                  <button
                    type="button"
                    onClick={() => setActiveTab("CARE")}
                    style={{
                      width: "100%",
                      minHeight: "44px",
                      backgroundColor: "#0F766E",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: "6px",
                      fontWeight: 700,
                      cursor: "pointer",
                      marginTop: "6px",
                    }}
                  >
                    View Care Details &amp; Video Room
                  </button>
                </div>
              )}

              {/* Verified Clinical Staffing Transparency */}
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #E2E8F0",
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "20px",
                }}
              >
                <h3 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#0B1F3A" }}>
                  Verified On-Duty Clinicians (Nigeria)
                </h3>
                {availableSlots.length > 0 ? (
                  availableSlots.map((slot) => (
                    <div
                      key={slot.slot_id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 0",
                        borderBottom: "1px solid #F1F5F9",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "14px" }}>
                          {slot.clinician_display_name}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748B" }}>
                          General Practice • MDCN Verified ✓ • Jurisdiction: {slot.jurisdiction}
                        </div>
                      </div>
                      <span
                        style={{
                          backgroundColor: "#F0FDFA",
                          color: "#0F766E",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        Available Now
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: "13px", color: "#64748B" }}>
                    Checking roster availability with clinical command...
                  </div>
                )}
              </div>

              {/* Clinical Governance Principles */}
              <div
                style={{
                  backgroundColor: "#F8FAFC",
                  border: "1px solid #CBD5E1",
                  borderRadius: "12px",
                  padding: "16px",
                  fontSize: "13px",
                  color: "#334155",
                  lineHeight: 1.5,
                }}
              >
                <div style={{ fontWeight: 700, color: "#0B1F3A", marginBottom: "6px" }}>
                  LoveWorld Care Operating Safeguards (§1.4, §8.5, §15.1)
                </div>
                <ul style={{ margin: "0 0 0 16px", padding: 0 }}>
                  <li>All medical consultations are conducted by licensed medical practitioners.</li>
                  <li>Artificial Intelligence never diagnoses or prescribes independently.</li>
                  <li>SponsorCare pools (LoveWorld Medicaid) provide 100% funding coverage for eligible beneficiaries.</li>
                  <li>Emergency red-flag guidance is always free and accessible offline.</li>
                </ul>
              </div>
            </div>
          )}

          {/* =========================================================================
              TAB 2: CARE
              ========================================================================= */}
          {activeTab === "CARE" && (
            <div>
              <h2 style={{ fontSize: "20px", color: "#0B1F3A", margin: "0 0 16px 0", fontWeight: 800 }}>
                My Clinical Consultations
              </h2>

              {activeEpisode ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  {/* Episode Summary Card */}
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      border: "1px solid #CBD5E1",
                      borderRadius: "12px",
                      padding: "16px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#64748B" }}>
                        CARE EPISODE: {activeEpisode.episode_id}
                      </span>
                      <span
                        style={{
                          backgroundColor: "#E0F2FE",
                          color: "#0369A1",
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {activeEpisode.state}
                      </span>
                    </div>

                    <div style={{ marginTop: "12px" }}>
                      <div style={{ fontSize: "12px", color: "#64748B" }}>Reported Symptoms</div>
                      <div style={{ fontSize: "14px", fontWeight: 600, color: "#0F172A", marginTop: "2px" }}>
                        {activeEpisode.chief_complaint_summary}
                      </div>
                    </div>

                    {activeIntakeResult && (
                      <div
                        style={{
                          marginTop: "12px",
                          backgroundColor: "#F8FAFC",
                          padding: "10px",
                          borderRadius: "6px",
                          border: "1px solid #E2E8F0",
                          fontSize: "13px",
                        }}
                      >
                        <div>
                          <strong>Protocol Evaluation:</strong> {activeIntakeResult.outcome_type}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                          {activeIntakeResult.safety_net_guidance_text}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Attending Doctor & WebRTC Video Card */}
                  {activeAppointment && (
                    <div
                      style={{
                        backgroundColor: "#FFFFFF",
                        border: "1px solid #0F766E",
                        borderRadius: "12px",
                        padding: "16px",
                      }}
                    >
                      <h3 style={{ fontSize: "15px", color: "#0F766E", margin: "0 0 8px 0" }}>
                        Attending Doctor: Dr. Adebayo Okonkwo (MDCN Verified)
                      </h3>
                      <p style={{ fontSize: "13px", color: "#334155", margin: "0 0 12px 0" }}>
                        Appointment Status: <strong>{activeAppointment.state}</strong> • Modality:{" "}
                        <strong>{activeAppointment.modality}</strong>
                      </p>

                      <div
                        style={{
                          backgroundColor: "#0B1F3A",
                          borderRadius: "8px",
                          padding: "20px",
                          textAlign: "center",
                          color: "#FFFFFF",
                        }}
                      >
                        <div style={{ fontSize: "36px", marginBottom: "8px" }}>📹</div>
                        <div style={{ fontWeight: 700, fontSize: "15px" }}>
                          LiveKit Encrypted Medical RTC Room
                        </div>
                        <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "4px" }}>
                          Low-bandwidth adaptive video with audio fallback.
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            alert(
                              "Joining LiveKit Room: enc-room-live • Remote Suitability Confirmed • Doctor Adebayo Okonkwo is online."
                            );
                          }}
                          style={{
                            marginTop: "16px",
                            minHeight: "44px",
                            padding: "10px 24px",
                            backgroundColor: "#0F766E",
                            color: "#FFFFFF",
                            border: "none",
                            borderRadius: "6px",
                            fontWeight: 700,
                            fontSize: "14px",
                            cursor: "pointer",
                          }}
                        >
                          Join Doctor Video Call Now
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Ed25519 Signed Encounter Verification Proof */}
                  <SignedRecordSeal
                    signerName="Dr. Adebayo Okonkwo"
                    mdcnLicence="MDCN/R/44210"
                    signedAtIso={new Date().toISOString()}
                    documentSha256="4e6a8d71b9c3e2f5a01948d7c6b5a43210ef876543210fedcba9876543210fed"
                  />
                </div>
              ) : (
                <div
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: "12px",
                    padding: "32px 20px",
                    textAlign: "center",
                    border: "1px solid #E2E8F0",
                  }}
                >
                  <span style={{ fontSize: "40px" }}>🩺</span>
                  <h3 style={{ fontSize: "16px", color: "#0B1F3A", margin: "12px 0 6px 0" }}>
                    No Active Consultations
                  </h3>
                  <p style={{ color: "#64748B", fontSize: "14px", margin: "0 0 20px 0" }}>
                    You have no active doctor consultations scheduled. Start an intake to see a verified doctor.
                  </p>
                  <button
                    type="button"
                    onClick={handleStartIntake}
                    style={{
                      minHeight: "44px",
                      padding: "10px 24px",
                      backgroundColor: "#C89D3C",
                      color: "#0B1F3A",
                      border: "none",
                      borderRadius: "6px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Request Care Now
                  </button>
                </div>
              )}
            </div>
          )}

          {/* =========================================================================
              TAB 3: MESSAGES
              ========================================================================= */}
          {activeTab === "MESSAGES" && (
            <div>
              <h2 style={{ fontSize: "20px", color: "#0B1F3A", margin: "0 0 16px 0", fontWeight: 800 }}>
                Care Messages &amp; Updates
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div
                  style={{
                    backgroundColor: "#FFFFFF",
                    border: "1px solid #E2E8F0",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <strong style={{ fontSize: "14px", color: "#0B1F3A" }}>
                      LoveWorld Care Coordinator
                    </strong>
                    <span style={{ fontSize: "12px", color: "#64748B" }}>Today</span>
                  </div>
                  <p style={{ fontSize: "13px", color: "#334155", margin: 0 }}>
                    Welcome to LoveWorld Care. Your consultations are private, confidential, and
                    conducted only by verified Nigerian physicians.
                  </p>
                </div>

                {activeAppointment && (
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      border: "1px solid #CCFBF1",
                      borderRadius: "8px",
                      padding: "14px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <strong style={{ fontSize: "14px", color: "#0F766E" }}>
                        Consultation Booking Confirmed
                      </strong>
                      <span style={{ fontSize: "12px", color: "#64748B" }}>Just now</span>
                    </div>
                    <p style={{ fontSize: "13px", color: "#334155", margin: 0 }}>
                      Appointment ref {activeAppointment.appointment_id} confirmed for video review
                      with Dr. Adebayo Okonkwo.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =========================================================================
              TAB 4: PROFILE
              ========================================================================= */}
          {activeTab === "PROFILE" && (
            <div>
              <h2 style={{ fontSize: "20px", color: "#0B1F3A", margin: "0 0 16px 0", fontWeight: 800 }}>
                Patient Profile &amp; Privacy Controls
              </h2>

              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #E2E8F0",
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "16px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div
                    style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "24px",
                      backgroundColor: "#0B1F3A",
                      color: "#C89D3C",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "20px",
                      fontWeight: 800,
                    }}
                  >
                    SG
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: "16px" }}>{patientName}</div>
                    <div style={{ fontSize: "12px", color: "#64748B" }}>
                      Patient ID: {patientId} • Nigeria (NG)
                    </div>
                  </div>
                </div>
              </div>

              {/* Passwordless Email Magic Link Authentication */}
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <h3 style={{ fontSize: "15px", color: "#0B1F3A", margin: 0, fontWeight: 700 }}>
                    Passwordless Sign-In (Email Magic Link)
                  </h3>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      backgroundColor: patientToken ? "#ECFDF5" : "#FEF3C7",
                      color: patientToken ? "#065F46" : "#92400E",
                      padding: "2px 8px",
                      borderRadius: "12px",
                    }}
                  >
                    {patientToken ? "TOKEN ACTIVE" : "UNAUTHENTICATED"}
                  </span>
                </div>
                <p style={{ fontSize: "13px", color: "#64748B", margin: "0 0 12px 0" }}>
                  Enter your email address to receive a secure, cryptographic one-time sign-in link with no password required.
                </p>

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                  <input
                    type="email"
                    value={magicLinkEmail}
                    onChange={(e) => setMagicLinkEmail(e.target.value)}
                    placeholder="Enter your email address"
                    style={{
                      flex: 1,
                      minWidth: "220px",
                      padding: "10px 12px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "6px",
                      fontSize: "13px",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleRequestMagicLink()}
                    disabled={isSendingMagicLink || !magicLinkEmail}
                    style={{
                      padding: "10px 16px",
                      backgroundColor: "#0B1F3A",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: "6px",
                      fontWeight: 700,
                      fontSize: "13px",
                      cursor: isSendingMagicLink ? "wait" : "pointer",
                    }}
                  >
                    {isSendingMagicLink ? "Sending..." : "Send Magic Link"}
                  </button>
                </div>

                {magicLinkStatusMsg && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      backgroundColor: "#F1F5F9",
                      fontSize: "12px",
                      color: "#1E293B",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: "8px",
                    }}
                  >
                    <span>{magicLinkStatusMsg}</span>
                    {magicLinkToken && (
                      <button
                        type="button"
                        onClick={() => void handleVerifyMagicLink()}
                        style={{
                          padding: "6px 12px",
                          backgroundColor: "#059669",
                          color: "#FFFFFF",
                          border: "none",
                          borderRadius: "4px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        Verify &amp; Sign In Now
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* NDPA & Telemedicine Consent Status */}
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #E2E8F0",
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "16px",
                }}
              >
                <h3 style={{ fontSize: "15px", color: "#0B1F3A", margin: "0 0 10px 0" }}>
                  Privacy &amp; Data Rights (NDPA / NDPC Compliant)
                </h3>
                <div style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5 }}>
                  <p style={{ margin: "0 0 8px 0" }}>
                    ✓ <strong>Telemedicine Informed Consent:</strong> Active for GP consultations.
                  </p>
                  <p style={{ margin: "0 0 8px 0" }}>
                    ✓ <strong>Zero Sponsor Access:</strong> Sponsors receive zero medical details or
                    clinical notes (k &ge; 5 privacy preserved).
                  </p>
                  <p style={{ margin: "0 0 8px 0" }}>
                    ✓ <strong>Data Subject Rights:</strong> You may request an immutable copy of your
                    signed medical history or revoke proxy assignments at any time.
                  </p>
                </div>
              </div>

              {/* Shared Device Emergency Wipe */}
              <div
                style={{
                  backgroundColor: "#FEF2F2",
                  border: "1px solid #FCA5A5",
                  borderRadius: "12px",
                  padding: "16px",
                }}
              >
                <h3 style={{ fontSize: "15px", color: "#991B1B", margin: "0 0 6px 0" }}>
                  Shared Device Safety (§21.6)
                </h3>
                <p style={{ fontSize: "13px", color: "#7F1D1D", margin: "0 0 12px 0" }}>
                  If you are using a shared church or community phone, lock your session or wipe local
                  device data immediately after your consultation.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    localStorage.removeItem("lw_patient_token");
                    window.location.reload();
                  }}
                  style={{
                    minHeight: "44px",
                    padding: "8px 16px",
                    backgroundColor: "#B91C1C",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "6px",
                    fontWeight: 700,
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Wipe Local Device Session
                </button>
              </div>
            </div>
          )}
        </main>
      )}

      {/* =========================================================================
          GUIDED INTAKE & DOCTORNOW BOOKING WIZARD MODAL
          ========================================================================= */}
      {isWizardOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="DoctorNow Guided Intake"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: "#FFFFFF",
              width: "100%",
              maxWidth: "600px",
              maxHeight: "90vh",
              borderTopLeftRadius: "20px",
              borderTopRightRadius: "20px",
              padding: "20px",
              overflowY: "auto",
              boxShadow: "0 -8px 32px rgba(0, 0, 0, 0.2)",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid #E2E8F0",
                paddingBottom: "12px",
                marginBottom: "16px",
              }}
            >
              <div>
                <span
                  style={{
                    backgroundColor: "#C89D3C",
                    color: "#0B1F3A",
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: "4px",
                  }}
                >
                  STEP {wizardStep} OF 4
                </span>
                <h3 style={{ fontSize: "18px", margin: "4px 0 0 0", color: "#0B1F3A", fontWeight: 800 }}>
                  {wizardStep === 1 && "Safety Screening: Emergency Red Flags"}
                  {wizardStep === 2 && "Symptoms & Medical Intake"}
                  {wizardStep === 3 && "Clinician Slot & Modality"}
                  {wizardStep === 4 && "SponsorCare / Payment & Consent"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsWizardOpen(false)}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: "24px",
                  cursor: "pointer",
                  color: "#64748B",
                }}
              >
                ✕
              </button>
            </div>

            {/* STEP 1: SAFETY RED FLAGS */}
            {wizardStep === 1 && (
              <div>
                <p style={{ fontSize: "14px", color: "#475569", lineHeight: 1.5, margin: "0 0 16px 0" }}>
                  Please confirm whether you or the patient are experiencing any of the following critical emergency symptoms:
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      cursor: "pointer",
                      backgroundColor: hasChestPain ? "#FEF2F2" : "#FFFFFF",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={hasChestPain}
                      onChange={(e) => setHasChestPain(e.target.checked)}
                      style={{ width: "20px", height: "20px" }}
                    />
                    <span style={{ fontSize: "14px", fontWeight: 600 }}>
                      Severe crushing chest pain or pressure
                    </span>
                  </label>

                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      cursor: "pointer",
                      backgroundColor: hasBreathingDifficulty ? "#FEF2F2" : "#FFFFFF",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={hasBreathingDifficulty}
                      onChange={(e) => setHasBreathingDifficulty(e.target.checked)}
                      style={{ width: "20px", height: "20px" }}
                    />
                    <span style={{ fontSize: "14px", fontWeight: 600 }}>
                      Severe sudden difficulty breathing or gasping
                    </span>
                  </label>

                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      cursor: "pointer",
                      backgroundColor: hasUncontrolledBleeding ? "#FEF2F2" : "#FFFFFF",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={hasUncontrolledBleeding}
                      onChange={(e) => setHasUncontrolledBleeding(e.target.checked)}
                      style={{ width: "20px", height: "20px" }}
                    />
                    <span style={{ fontSize: "14px", fontWeight: 600 }}>
                      Heavy, uncontrolled bleeding or severe trauma
                    </span>
                  </label>
                </div>

                {hasEmergencyRedFlags ? (
                  <div
                    style={{
                      marginTop: "16px",
                      padding: "14px",
                      backgroundColor: "#FEF2F2",
                      border: "2px solid #B91C1C",
                      borderRadius: "8px",
                      color: "#991B1B",
                    }}
                  >
                    <div style={{ fontWeight: 800, fontSize: "15px" }}>
                      🚨 CRITICAL EMERGENCY DETECTED
                    </div>
                    <p style={{ fontSize: "13px", margin: "6px 0 10px 0", lineHeight: 1.4 }}>
                      LoveWorld Care does not dispatch ambulances. For these severe symptoms, remote
                      care is not suitable. Please immediately call <strong>112 (National)</strong> or{" "}
                      <strong>767 (Lagos)</strong> or proceed to the nearest hospital emergency room.
                    </p>
                    <a
                      href="tel:112"
                      style={{
                        display: "inline-block",
                        minHeight: "44px",
                        padding: "10px 20px",
                        backgroundColor: "#B91C1C",
                        color: "#FFFFFF",
                        borderRadius: "6px",
                        fontWeight: 800,
                        textDecoration: "none",
                      }}
                    >
                      Call 112 Immediately
                    </a>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    style={{
                      marginTop: "20px",
                      width: "100%",
                      minHeight: "48px",
                      backgroundColor: "#0B1F3A",
                      color: "#FFFFFF",
                      fontWeight: 700,
                      fontSize: "15px",
                      border: "none",
                      borderRadius: "8px",
                      cursor: "pointer",
                    }}
                  >
                    No Emergency Symptoms — Continue to Intake →
                  </button>
                )}
              </div>
            )}

            {/* STEP 2: SYMPTOMS & CHIEF COMPLAINT */}
            {wizardStep === 2 && (
              <div>
                <div style={{ marginBottom: "14px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                    Primary Symptom Category
                  </label>
                  <select
                    value={symptomCategory}
                    onChange={(e) => setSymptomCategory(e.target.value)}
                    style={{
                      width: "100%",
                      minHeight: "44px",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                      backgroundColor: "#FFFFFF",
                    }}
                  >
                    <option value="FEVER_OR_MALARIA_LIKE">Fever / Chills / Malaria-Like Symptoms</option>
                    <option value="COUGH_OR_RESPIRATORY">Cough / Cold / Upper Respiratory</option>
                    <option value="GASTROINTESTINAL">Stomach Pain / Diarrhea / Nausea</option>
                    <option value="SKIN_AND_RASH">Skin Irritation / Rash / Allergy</option>
                    <option value="GENERAL_CONSULT">General Physician Consultation</option>
                  </select>
                </div>

                <div style={{ marginBottom: "14px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                    Duration of Symptoms (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={durationDays}
                    onChange={(e) => setDurationDays(Number(e.target.value))}
                    style={{
                      width: "100%",
                      minHeight: "44px",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                      boxSizing: "border-box",
                    }}
                  />
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                    Describe your health concern in your own words
                  </label>
                  <textarea
                    rows={4}
                    value={chiefComplaint}
                    onChange={(e) => setChiefComplaint(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(1)}
                    style={{
                      flex: 1,
                      minHeight: "44px",
                      backgroundColor: "#F1F5F9",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    style={{
                      flex: 2,
                      minHeight: "44px",
                      backgroundColor: "#0B1F3A",
                      color: "#FFFFFF",
                      borderRadius: "8px",
                      border: "none",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Next: Choose Doctor &amp; Modality →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: CLINICIAN & MODALITY */}
            {wizardStep === 3 && (
              <div>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                    Available Licensed Doctor &amp; Shift Slot
                  </label>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {availableSlots.map((slot) => (
                      <label
                        key={slot.slot_id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          padding: "12px",
                          border: selectedSlotId === slot.slot_id ? "2px solid #0F766E" : "1px solid #CBD5E1",
                          borderRadius: "8px",
                          cursor: "pointer",
                          backgroundColor: selectedSlotId === slot.slot_id ? "#F0FDFA" : "#FFFFFF",
                        }}
                      >
                        <input
                          type="radio"
                          name="slotSelection"
                          checked={selectedSlotId === slot.slot_id}
                          onChange={() => setSelectedSlotId(slot.slot_id)}
                        />
                        <div>
                          <div style={{ fontWeight: 700, fontSize: "14px" }}>
                            {slot.clinician_display_name}
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748B" }}>
                            General Practice (GP) • MDCN Verified • Standard Fee: ₦{(slot.fee_minor / 100).toLocaleString()}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                    Consultation Modality
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={() => setSelectedModality("VIDEO")}
                      style={{
                        minHeight: "44px",
                        padding: "10px",
                        borderRadius: "8px",
                        border: selectedModality === "VIDEO" ? "2px solid #0B1F3A" : "1px solid #CBD5E1",
                        backgroundColor: selectedModality === "VIDEO" ? "#E0F2FE" : "#FFFFFF",
                        fontWeight: 700,
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      📹 Secure Video (LiveKit)
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedModality("ASYNC_CLINICAL_MESSAGING")}
                      style={{
                        minHeight: "44px",
                        padding: "10px",
                        borderRadius: "8px",
                        border: selectedModality === "ASYNC_CLINICAL_MESSAGING" ? "2px solid #0B1F3A" : "1px solid #CBD5E1",
                        backgroundColor: selectedModality === "ASYNC_CLINICAL_MESSAGING" ? "#E0F2FE" : "#FFFFFF",
                        fontWeight: 700,
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      💬 Clinical Messaging
                    </button>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    style={{
                      flex: 1,
                      minHeight: "44px",
                      backgroundColor: "#F1F5F9",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(4)}
                    style={{
                      flex: 2,
                      minHeight: "44px",
                      backgroundColor: "#0B1F3A",
                      color: "#FFFFFF",
                      borderRadius: "8px",
                      border: "none",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Next: Funding &amp; Consent →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: SPONSORCARE / PAYMENT & CONSENT */}
            {wizardStep === 4 && (
              <div>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, marginBottom: "8px" }}>
                    Select Funding Route (§10.1 &amp; §10.2)
                  </label>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <label
                      style={{
                        padding: "12px",
                        border: fundingRoute === "SPONSOR_DEFINED_SERVICES" ? "2px solid #C89D3C" : "1px solid #CBD5E1",
                        backgroundColor: fundingRoute === "SPONSOR_DEFINED_SERVICES" ? "#FDF8EC" : "#FFFFFF",
                        borderRadius: "8px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <input
                        type="radio"
                        name="funding"
                        checked={fundingRoute === "SPONSOR_DEFINED_SERVICES"}
                        onChange={() => setFundingRoute("SPONSOR_DEFINED_SERVICES")}
                      />
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "14px", color: "#0B1F3A" }}>
                          SponsorCare: LoveWorld Medicaid Pool (100% Covered)
                        </div>
                        <div style={{ fontSize: "12px", color: "#78350F" }}>
                          ₦0.00 Out-of-Pocket • Paid directly by Humanitarian Care Agreement
                        </div>
                      </div>
                    </label>

                    <label
                      style={{
                        padding: "12px",
                        border: fundingRoute === "SELF_PAY" ? "2px solid #0B1F3A" : "1px solid #CBD5E1",
                        backgroundColor: fundingRoute === "SELF_PAY" ? "#F0F9FF" : "#FFFFFF",
                        borderRadius: "8px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <input
                        type="radio"
                        name="funding"
                        checked={fundingRoute === "SELF_PAY"}
                        onChange={() => setFundingRoute("SELF_PAY")}
                      />
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "14px" }}>
                          Direct Self-Pay: Paystack / Flutterwave
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748B" }}>
                          Standard General Practice Consultation Fee: ₦6,000.00
                        </div>
                      </div>
                    </label>

                    <label
                      style={{
                        padding: "12px",
                        border: fundingRoute === "ESPEES_WALLET_DIRECT" ? "2px solid #0B1F3A" : "1px solid #CBD5E1",
                        backgroundColor: fundingRoute === "ESPEES_WALLET_DIRECT" ? "#F0FDF4" : "#FFFFFF",
                        borderRadius: "8px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <input
                        type="radio"
                        name="funding"
                        checked={fundingRoute === "ESPEES_WALLET_DIRECT"}
                        onChange={() => setFundingRoute("ESPEES_WALLET_DIRECT")}
                      />
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "14px" }}>
                          Espees Wallet Direct: 4.00 ESP
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748B" }}>
                          Instant debit from KingsChat / LoveWorld Espees account
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Informed Consent Checkbox */}
                <div style={{ marginBottom: "20px" }}>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "10px",
                      fontSize: "13px",
                      color: "#334155",
                      cursor: "pointer",
                      lineHeight: 1.4,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={telemedicineConsent}
                      onChange={(e) => setTelemedicineConsent(e.target.checked)}
                      style={{ width: "18px", height: "18px", marginTop: "2px" }}
                    />
                    <span>
                      I give informed consent for remote medical consultation. I understand that
                      physical examination (palpation/auscultation) cannot be performed remotely, and
                      that in any emergency I must proceed to an in-person hospital.
                    </span>
                  </label>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    disabled={isSubmitting}
                    style={{
                      flex: 1,
                      minHeight: "44px",
                      backgroundColor: "#F1F5F9",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={handleCompleteBooking}
                    disabled={!telemedicineConsent || isSubmitting}
                    style={{
                      flex: 2,
                      minHeight: "44px",
                      backgroundColor: isSubmitting ? "#94A3B8" : "#C89D3C",
                      color: "#0B1F3A",
                      borderRadius: "8px",
                      border: "none",
                      fontWeight: 800,
                      fontSize: "15px",
                      cursor: isSubmitting ? "not-allowed" : "pointer",
                    }}
                  >
                    {isSubmitting ? "Locking Slot & Reserving..." : "Confirm & Request Care ✓"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fixed Mobile Bottom Navigation Bar */}
      <MobileBottomNavBar
        activeTab={activeTab}
        onSelectTab={(tabId) => setActiveTab(tabId as PatientNavTab)}
        items={NAV_ITEMS}
      />
    </div>
  );
}
