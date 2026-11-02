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
  CareContinuityPlan,
  CareEpisodeResponse,
  CareRelationship,
  CareTask,
  ClinicalObservation,
  CompanionChatResponse,
  EmergencyGuidanceResponse,
  IntakeEvaluationResponse,
  LoveWorldCareApiClient,
  MedicationInstruction,
  PatientDashboardResponse,
  PatientSubject,
  StaffedSlotDTO,
  AppointmentBookingResponse,
} from "@loveworld-care/api-contracts";
import type { ConsultationModality, FundingRouteType } from "@loveworld-care/domain-types";

// =============================================================================
// §4 & §5 Navigation Tabs per Blueprint LWC-UX-001 & LWC-SCR-101..112
// =============================================================================
type PatientNavTab = "TODAY" | "COMPANION" | "CARE" | "RECORDS" | "ACCOUNT";

const NAV_ITEMS: readonly NavItem[] = [
  { id: "TODAY", label: "Today", icon: "☀️" },
  { id: "COMPANION", label: "Companion", icon: "💬" },
  { id: "CARE", label: "My Care", icon: "🩺" },
  { id: "RECORDS", label: "Records", icon: "📋" },
  { id: "ACCOUNT", label: "Account", icon: "👤" },
];

export default function PatientPortalPwa() {
  const [activeTab, setActiveTab] = useState<PatientNavTab>("TODAY");
  const [sessionLocked, setSessionLocked] = useState<boolean>(false);
  const [patientToken, setPatientToken] = useState<string | null>(null);

  // Identity & Multi-Subject Context (LWC-ACC-001..005)
  const [accountUserId, setAccountUserId] = useState<string>("patient-001");
  const [accountEmail, setAccountEmail] = useState<string>("patient@care.loveworld.org");
  const [subjects, setSubjects] = useState<readonly PatientSubject[]>([]);
  const [activeSubjectId, setActiveSubjectId] = useState<string>("");
  const [isLoadingSubjects, setIsLoadingSubjects] = useState<boolean>(true);
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState<boolean>(false);

  // New Subject Form Fields
  const [newSubjName, setNewSubjName] = useState<string>("");
  const [newSubjDob, setNewSubjDob] = useState<string>("");
  const [newSubjGender, setNewSubjGender] = useState<string>("FEMALE");
  const [newSubjRel, setNewSubjRel] = useState<string>("CHILD");
  const [isCreatingSubject, setIsCreatingSubject] = useState<boolean>(false);

  // Live API Client & Network States
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [emergencyGuidance, setEmergencyGuidance] = useState<EmergencyGuidanceResponse | null>(null);

  // Today Dashboard State (LWC-SCR-101)
  const [dashboardData, setDashboardData] = useState<PatientDashboardResponse | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState<boolean>(false);

  // Companion Chat State (LWC-SCR-102)
  const [chatMessages, setChatMessages] = useState<
    Array<{
      sender: "USER" | "COMPANION";
      text: string;
      emergency?: boolean;
      contacts?: readonly { region: string; label: string; phone: string }[];
      actions?: readonly string[];
      provenance?: { source: string; protocol_id: string; timestamp: string; disclaimer: string };
    }>
  >([]);
  const [chatInput, setChatInput] = useState<string>("");
  const [isSendingChat, setIsSendingChat] = useState<boolean>(false);

  // My Care State (LWC-SCR-103..106)
  const [carePlans, setCarePlans] = useState<readonly CareContinuityPlan[]>([]);
  const [medications, setMedications] = useState<readonly MedicationInstruction[]>([]);
  const [availableSlots, setAvailableSlots] = useState<readonly StaffedSlotDTO[]>([]);
  const [isLoadingCare, setIsLoadingCare] = useState<boolean>(false);

  // Guided Intake Wizard Modal State (LWC-SCR-103)
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [isSubmittingIntake, setIsSubmittingIntake] = useState<boolean>(false);
  const [hasChestPain, setHasChestPain] = useState<boolean>(false);
  const [hasBreathingDifficulty, setHasBreathingDifficulty] = useState<boolean>(false);
  const [hasUncontrolledBleeding, setHasUncontrolledBleeding] = useState<boolean>(false);
  const [symptomCategory, setSymptomCategory] = useState<string>("FEVER_OR_MALARIA_LIKE");
  const [durationDays, setDurationDays] = useState<number>(1);
  const [chiefComplaint, setChiefComplaint] = useState<string>("");
  const [intakeLanguage, setIntakeLanguage] = useState<string>("en-NG");
  const [selectedSlotId, setSelectedSlotId] = useState<string>("");
  const [selectedModality, setSelectedModality] = useState<ConsultationModality>("VIDEO");
  const [fundingRoute, setFundingRoute] = useState<FundingRouteType>("SPONSOR_DEFINED_SERVICES");
  const [intakeResult, setIntakeResult] = useState<IntakeEvaluationResponse | null>(null);
  const [bookingResult, setBookingResult] = useState<AppointmentBookingResponse | null>(null);

  // Records & Observations State (LWC-SCR-107..108)
  const [recordsTimeline, setRecordsTimeline] = useState<readonly Record<string, unknown>[]>([]);
  const [isLoadingRecords, setIsLoadingRecords] = useState<boolean>(false);
  const [isObservationModalOpen, setIsObservationModalOpen] = useState<boolean>(false);
  const [obsKind, setObsKind] = useState<"SYMPTOM" | "VITAL" | "LAB_RESULT" | "DOCUMENT">("VITAL");
  const [obsName, setObsName] = useState<string>("Blood Pressure (Systolic/Diastolic)");
  const [obsValue, setObsValue] = useState<string>("");
  const [obsUnit, setObsUnit] = useState<string>("mmHg");
  const [obsNotes, setObsNotes] = useState<string>("");
  const [isSavingObs, setIsSavingObs] = useState<boolean>(false);

  // Account & Proxy State (LWC-SCR-109..112)
  const [magicLinkEmail, setMagicLinkEmail] = useState<string>("patient@care.loveworld.org");
  const [isSendingMagicLink, setIsSendingMagicLink] = useState<boolean>(false);
  const [magicLinkSent, setMagicLinkSent] = useState<boolean>(false);
  const [magicLinkToken, setMagicLinkToken] = useState<string | null>(null);
  const [magicLinkStatusMsg, setMagicLinkStatusMsg] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Initialize Client & Auth
  // ---------------------------------------------------------------------------
  useEffect(() => {
    async function initClient() {
      try {
        let token = typeof window !== "undefined" ? localStorage.getItem("lw_patient_token") : null;
        if (!token) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: accountUserId,
              audience: "lwc:patient",
              roles: ["PATIENT"],
              mfa: false,
              ttl_minutes: 180,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token && typeof window !== "undefined") {
              localStorage.setItem("lw_patient_token", token);
            }
          }
        }
        setPatientToken(token);

        const client = new LoveWorldCareApiClient("", () => ({
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }));
        setApiClient(client);

        const guidance = await client.getEmergencyGuidance("NG").catch(() => null);
        if (guidance) setEmergencyGuidance(guidance);

        // Fetch subjects
        const subjList = await client.listSubjects().catch(() => []);
        setSubjects(subjList);
        if (subjList.length > 0) {
          setActiveSubjectId(subjList[0].patient_id);
        }
        setIsLoadingSubjects(false);
      } catch (err: unknown) {
        setNetworkError(err instanceof Error ? err.message : "Service temporarily unreachable");
        setIsLoadingSubjects(false);
      }
    }
    initClient();
  }, [accountUserId]);

  // ---------------------------------------------------------------------------
  // Refresh Data When Active Subject Changes
  // ---------------------------------------------------------------------------
  const refreshSubjectData = useCallback(async () => {
    if (!apiClient || !activeSubjectId) return;
    setNetworkError(null);

    // Refresh Dashboard
    setIsLoadingDashboard(true);
    try {
      const db = await apiClient.getPatientDashboard(activeSubjectId);
      setDashboardData(db);
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Unable to load dashboard");
    } finally {
      setIsLoadingDashboard(false);
    }

    // Refresh Care plans & meds
    setIsLoadingCare(true);
    try {
      const [plans, meds, slots] = await Promise.all([
        apiClient.listCarePlans(activeSubjectId).catch(() => []),
        apiClient.listMedications(activeSubjectId).catch(() => []),
        apiClient.listStaffedSlots("NG", "GP").catch(() => []),
      ]);
      setCarePlans(plans);
      setMedications(meds);
      setAvailableSlots(slots);
      if (slots.length > 0 && !selectedSlotId) {
        setSelectedSlotId(slots[0].slot_id);
      }
    } catch {
      // Non-critical background fetch failure handled gracefully
    } finally {
      setIsLoadingCare(false);
    }

    // Refresh Records
    setIsLoadingRecords(true);
    try {
      const recs = await apiClient.listRecords(activeSubjectId);
      setRecordsTimeline(recs);
    } catch {
      // Fallback empty
    } finally {
      setIsLoadingRecords(false);
    }
  }, [apiClient, activeSubjectId, selectedSlotId]);

  useEffect(() => {
    if (activeSubjectId) {
      refreshSubjectData();
    }
  }, [activeSubjectId, refreshSubjectData]);

  // ---------------------------------------------------------------------------
  // Subject Creation Handler
  // ---------------------------------------------------------------------------
  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiClient || !newSubjName.trim() || !newSubjDob) return;
    setIsCreatingSubject(true);
    setNetworkError(null);
    try {
      const created = await apiClient.createSubject({
        full_name: newSubjName.trim(),
        dob_iso: new Date(newSubjDob).toISOString(),
        gender: newSubjGender,
        relationship: newSubjRel,
        jurisdiction: "NG",
      });
      setSubjects((prev) => [...prev, created]);
      setActiveSubjectId(created.patient_id);
      setIsAddSubjectModalOpen(false);
      setNewSubjName("");
      setNewSubjDob("");
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to create subject");
    } finally {
      setIsCreatingSubject(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Companion Chat Handler
  // ---------------------------------------------------------------------------
  const handleSendChatMessage = async (presetText?: string) => {
    const textToSend = presetText || chatInput;
    if (!apiClient || !textToSend.trim()) return;

    const userMsg = textToSend.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "USER", text: userMsg }]);
    setIsSendingChat(true);

    try {
      const res: CompanionChatResponse = await apiClient.companionChat({
        patient_id: activeSubjectId || undefined,
        message: userMsg,
        jurisdiction: "NG",
      });

      setChatMessages((prev) => [
        ...prev,
        {
          sender: "COMPANION",
          text: res.reply,
          emergency: res.emergency,
          contacts: res.emergency_contacts,
          actions: res.suggested_actions,
          provenance: res.provenance,
        },
      ]);
    } catch (err: unknown) {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "COMPANION",
          text: "I am experiencing network connectivity disruption. If this is an urgent health concern, please call 112 or visit the nearest medical facility immediately.",
        },
      ]);
    } finally {
      setIsSendingChat(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Care Task Resolution
  // ---------------------------------------------------------------------------
  const handleResolveTask = async (taskId: string) => {
    if (!apiClient || !activeSubjectId) return;
    try {
      await apiClient.resolveTask(activeSubjectId, taskId, { self_reported: true });
      refreshSubjectData();
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to resolve care task");
    }
  };

  // ---------------------------------------------------------------------------
  // Medication Adherence Reporting
  // ---------------------------------------------------------------------------
  const handleReportAdherence = async (medicationId: string, status: "TAKEN" | "SKIPPED" | "ISSUE") => {
    if (!apiClient || !activeSubjectId) return;
    try {
      await apiClient.reportMedicationAdherence(activeSubjectId, medicationId, { status });
      refreshSubjectData();
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to record adherence");
    }
  };

  // ---------------------------------------------------------------------------
  // Log Observation / Vital
  // ---------------------------------------------------------------------------
  const handleSaveObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiClient || !activeSubjectId || !obsValue.trim()) return;
    setIsSavingObs(true);
    try {
      await apiClient.addObservation(activeSubjectId, {
        kind: obsKind,
        name: obsName,
        value: obsValue.trim(),
        unit: obsUnit.trim() || undefined,
        notes: obsNotes.trim() || undefined,
        source: "PATIENT_REPORTED",
      });
      setIsObservationModalOpen(false);
      setObsValue("");
      setObsNotes("");
      refreshSubjectData();
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to save observation");
    } finally {
      setIsSavingObs(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Atomic Intake & Booking Wizard Submission
  // ---------------------------------------------------------------------------
  const handleCompleteBooking = async () => {
    if (!apiClient || !activeSubjectId) return;
    if (!chiefComplaint.trim()) {
      setNetworkError("Please provide a description of your primary symptom or health concern.");
      return;
    }

    setIsSubmittingIntake(true);
    setNetworkError(null);

    try {
      const idempotencyKey = `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

      // 1. Create Episode
      const ep = await apiClient.createEpisode(
        {
          patient_id: activeSubjectId,
          jurisdiction: "NG",
          care_service: "GP_REMOTE",
          consent_grant_id: `consent-${Date.now()}`,
          request_source: "PATIENT_PWA",
          chief_complaint_summary: chiefComplaint.trim(),
        },
        idempotencyKey
      );

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
          raw_patient_statement: chiefComplaint.trim(),
          language_code: intakeLanguage,
          request_ai_draft_extraction: true,
        },
        `${idempotencyKey}-intake`
      );
      setIntakeResult(intakeRes);

      // 3. Book Staffed Slot
      const targetSlot = selectedSlotId || (availableSlots.length > 0 ? availableSlots[0].slot_id : "slot-ng-gp-001");
      const appt = await apiClient.bookAppointment(
        {
          episode_id: ep.episode_id,
          slot_id: targetSlot,
          modality: selectedModality,
          funding_route: fundingRoute,
          sponsor_agreement_id:
            fundingRoute === "SPONSOR_DEFINED_SERVICES" ? "AGR-LW-MEDICAID-NG-2026" : undefined,
          payment_provider: fundingRoute === "SELF_PAY" ? "PAYSTACK" : undefined,
        },
        `${idempotencyKey}-appt`
      );
      setBookingResult(appt);

      setIsWizardOpen(false);
      setChiefComplaint("");
      setActiveTab("CARE");
      refreshSubjectData();
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Intake and booking could not be completed");
    } finally {
      setIsSubmittingIntake(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Magic Link Passwordless Flow
  // ---------------------------------------------------------------------------
  const handleRequestMagicLink = async () => {
    if (!apiClient || !magicLinkEmail) return;
    setIsSendingMagicLink(true);
    setMagicLinkStatusMsg(null);
    try {
      const res = await apiClient.requestMagicLink(magicLinkEmail);
      setMagicLinkSent(true);
      if (res.verification_token) {
        setMagicLinkToken(res.verification_token);
        setMagicLinkStatusMsg(`Verification token generated for ${res.email}. Click below to confirm.`);
      } else {
        setMagicLinkStatusMsg(`Sign-in link dispatched to ${res.email}. Please verify.`);
      }
    } catch (err: unknown) {
      setMagicLinkStatusMsg(err instanceof Error ? err.message : "Failed to request magic link");
    } finally {
      setIsSendingMagicLink(false);
    }
  };

  const handleVerifyMagicLink = async () => {
    if (!apiClient || !magicLinkToken) return;
    try {
      const res = await apiClient.verifyMagicLink(magicLinkToken);
      if (res.access_token) {
        localStorage.setItem("lw_patient_token", res.access_token);
        setPatientToken(res.access_token);
        setAccountUserId(res.patient_id);
        setAccountEmail(res.email);
        setMagicLinkStatusMsg(`Authenticated successfully as ${res.email}!`);
      }
    } catch (err: unknown) {
      setMagicLinkStatusMsg(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const activeSubject = subjects.find((s) => s.patient_id === activeSubjectId);
  const hasEmergencyRedFlags = hasChestPain || hasBreathingDifficulty || hasUncontrolledBleeding;

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
          LoveWorld Care Session Protected
        </h1>
        <p style={{ color: "#94A3B8", maxWidth: "380px", marginBottom: "24px", fontSize: "14px" }}>
          This device session has been locked to protect sensitive health records and personal data.
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
          Unlock Patient Session
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: "680px",
        margin: "0 auto",
        minHeight: "100vh",
        backgroundColor: "#F8FAFC",
        display: "flex",
        flexDirection: "column",
        paddingBottom: "80px",
      }}
    >
      {/* 1. Shared Device Session Lock Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="LoveWorld Care · Patient Portal"
        actorDisplayName={activeSubject ? activeSubject.full_name : accountEmail}
        isLocked={sessionLocked}
        onToggleLock={() => setSessionLocked((prev) => !prev)}
        onSignOut={() => {
          if (typeof window !== "undefined") localStorage.removeItem("lw_patient_token");
          window.location.reload();
        }}
      />

      {/* 2. Zero-Auth Emergency Safety Banner */}
      <EmergencySafetyBanner compact={true} />

      {/* 3. Multi-Subject Context Bar (LWC-ACC-005) */}
      <section
        aria-label="Active Patient Context"
        style={{
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #E2E8F0",
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "13px", fontWeight: 600, color: "#64748B" }}>Care for:</span>
          {isLoadingSubjects ? (
            <span style={{ fontSize: "13px", color: "#94A3B8" }}>Loading profiles...</span>
          ) : subjects.length > 0 ? (
            <select
              aria-label="Select Active Patient"
              value={activeSubjectId}
              onChange={(e) => setActiveSubjectId(e.target.value)}
              style={{
                fontSize: "14px",
                fontWeight: 700,
                color: LW_DESIGN_TOKENS.colors.royalNavy,
                padding: "6px 12px",
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                border: "1px solid #CBD5E1",
                backgroundColor: "#F1F5F9",
                cursor: "pointer",
              }}
            >
              {subjects.map((s) => (
                <option key={s.patient_id} value={s.patient_id}>
                  {s.full_name} ({s.relationship_to_account})
                </option>
              ))}
            </select>
          ) : (
            <span style={{ fontSize: "13px", color: "#DC2626", fontWeight: 600 }}>
              No subject registered
            </span>
          )}
          {activeSubject && (
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                backgroundColor: "#E0F2FE",
                color: "#0369A1",
                padding: "2px 8px",
                borderRadius: "12px",
              }}
            >
              {activeSubject.relationship_to_account}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setIsAddSubjectModalOpen(true)}
          style={{
            minHeight: "36px",
            padding: "6px 12px",
            fontSize: "12px",
            fontWeight: 700,
            color: LW_DESIGN_TOKENS.colors.royalNavy,
            backgroundColor: "#FFFFFF",
            border: `1px solid ${LW_DESIGN_TOKENS.colors.warmGold}`,
            borderRadius: LW_DESIGN_TOKENS.radius.md,
            cursor: "pointer",
          }}
        >
          + Add Dependent
        </button>
      </section>

      {/* Network Error Toast */}
      {networkError && (
        <div
          role="alert"
          style={{
            margin: "12px 16px 0",
            padding: "10px 14px",
            backgroundColor: "#FEE2E2",
            border: "1px solid #FCA5A5",
            borderRadius: LW_DESIGN_TOKENS.radius.md,
            color: "#991B1B",
            fontSize: "13px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>⚠️ {networkError}</span>
          <button
            type="button"
            onClick={() => setNetworkError(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#991B1B", fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content Area by Active Tab */}
      <main style={{ padding: "16px", flex: 1 }}>
        {/* ================================================================= */}
        {/* TAB 1: TODAY (LWC-SCR-101)                                        */}
        {/* ================================================================= */}
        {activeTab === "TODAY" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {isLoadingDashboard ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#64748B" }}>
                <div style={{ fontSize: "28px", marginBottom: "8px" }}>⏳</div>
                <p style={{ fontWeight: 600 }}>Syncing care itinerary...</p>
              </div>
            ) : dashboardData ? (
              <>
                {/* Orientation / Next Action Card */}
                {dashboardData.next_action && (
                  <div
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.lg,
                      border: `2px solid ${LW_DESIGN_TOKENS.colors.warmGold}`,
                      padding: "16px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.warmGold, textTransform: "uppercase" }}>
                        Primary Next Action
                      </span>
                    </div>
                    <h2 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 6px" }}>
                      {dashboardData.next_action.label}
                    </h2>
                    <p style={{ fontSize: "14px", color: "#475569", margin: "0 0 14px", lineHeight: 1.4 }}>
                      {dashboardData.next_action.details}
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        if (dashboardData.next_action?.type === "GET_HELP") {
                          setIsWizardOpen(true);
                        } else {
                          setActiveTab("CARE");
                        }
                      }}
                      style={{
                        minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                        padding: "10px 20px",
                        backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        fontWeight: 700,
                        fontSize: "14px",
                        cursor: "pointer",
                      }}
                    >
                      {dashboardData.next_action.type === "GET_HELP" ? "Start Doctor Consultation" : "View Care Actions"}
                    </button>
                  </div>
                )}

                {/* Active Appointments / Encounters */}
                <section aria-labelledby="today-appts-heading">
                  <h3 id="today-appts-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", marginBottom: "10px" }}>
                    Scheduled Consultations
                  </h3>
                  {dashboardData.active_appointments.length > 0 ? (
                    dashboardData.active_appointments.map((appt) => (
                      <div
                        key={appt.encounter_id}
                        style={{
                          backgroundColor: "#FFFFFF",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          border: "1px solid #CBD5E1",
                          padding: "14px",
                          marginBottom: "10px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          flexWrap: "wrap",
                          gap: "8px",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 800, fontSize: "15px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                            {appt.clinician_name}
                          </div>
                          <div style={{ fontSize: "13px", color: "#64748B" }}>
                            {appt.specialty} · {appt.modality}
                          </div>
                          <span
                            style={{
                              display: "inline-block",
                              marginTop: "4px",
                              fontSize: "11px",
                              fontWeight: 700,
                              backgroundColor: "#FEF3C7",
                              color: "#B45309",
                              padding: "2px 8px",
                              borderRadius: "4px",
                            }}
                          >
                            State: {appt.state}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTab("CARE")}
                          style={{
                            minHeight: "40px",
                            padding: "8px 16px",
                            backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                            color: "#FFFFFF",
                            border: "none",
                            borderRadius: LW_DESIGN_TOKENS.radius.md,
                            fontWeight: 700,
                            fontSize: "13px",
                            cursor: "pointer",
                          }}
                        >
                          Join Consultation
                        </button>
                      </div>
                    ))
                  ) : (
                    <div
                      style={{
                        backgroundColor: "#FFFFFF",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        border: "1px dashed #CBD5E1",
                        padding: "16px",
                        textAlign: "center",
                        color: "#64748B",
                        fontSize: "14px",
                      }}
                    >
                      No upcoming appointments today.
                    </div>
                  )}
                </section>

                {/* Today's Care Tasks */}
                <section aria-labelledby="today-tasks-heading">
                  <h3 id="today-tasks-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", marginBottom: "10px" }}>
                    Care Tasks & Reminders
                  </h3>
                  {dashboardData.due_tasks.length > 0 ? (
                    dashboardData.due_tasks.map((task) => (
                      <div
                        key={task.task_id}
                        style={{
                          backgroundColor: "#FFFFFF",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          border: "1px solid #E2E8F0",
                          padding: "12px 14px",
                          marginBottom: "8px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: "14px", color: "#1E293B" }}>{task.title}</div>
                          <div style={{ fontSize: "12px", color: "#64748B" }}>{task.description}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleResolveTask(task.task_id)}
                          style={{
                            minHeight: "36px",
                            padding: "6px 14px",
                            backgroundColor: "#F1F5F9",
                            color: "#0F172A",
                            border: "1px solid #CBD5E1",
                            borderRadius: LW_DESIGN_TOKENS.radius.md,
                            fontSize: "12px",
                            fontWeight: 700,
                            cursor: "pointer",
                          }}
                        >
                          ✓ Done
                        </button>
                      </div>
                    ))
                  ) : (
                    <div
                      style={{
                        backgroundColor: "#FFFFFF",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        border: "1px dashed #CBD5E1",
                        padding: "14px",
                        textAlign: "center",
                        color: "#64748B",
                        fontSize: "13px",
                      }}
                    >
                      All daily tasks completed!
                    </div>
                  )}
                </section>

                {/* Active Medications Due */}
                <section aria-labelledby="today-meds-heading">
                  <h3 id="today-meds-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", marginBottom: "10px" }}>
                    Medication Routine
                  </h3>
                  {dashboardData.active_medications.length > 0 ? (
                    dashboardData.active_medications.map((med) => (
                      <div
                        key={med.medication_id}
                        style={{
                          backgroundColor: "#FFFFFF",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
                          border: "1px solid #E2E8F0",
                          padding: "12px 14px",
                          marginBottom: "8px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          flexWrap: "wrap",
                          gap: "8px",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 800, fontSize: "14px", color: "#0F172A" }}>
                            {med.medication_name}
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748B" }}>
                            {med.dosage_instructions} ({med.clinical_indication})
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            type="button"
                            onClick={() => handleReportAdherence(med.medication_id, "TAKEN")}
                            style={{
                              minHeight: "34px",
                              padding: "4px 12px",
                              backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                              color: "#FFFFFF",
                              border: "none",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              fontSize: "12px",
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            Take Dose
                          </button>
                          <button
                            type="button"
                            onClick={() => handleReportAdherence(med.medication_id, "SKIPPED")}
                            style={{
                              minHeight: "34px",
                              padding: "4px 10px",
                              backgroundColor: "#F1F5F9",
                              color: "#64748B",
                              border: "1px solid #CBD5E1",
                              borderRadius: LW_DESIGN_TOKENS.radius.md,
                              fontSize: "12px",
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            Skip
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div
                      style={{
                        backgroundColor: "#FFFFFF",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        border: "1px dashed #CBD5E1",
                        padding: "14px",
                        textAlign: "center",
                        color: "#64748B",
                        fontSize: "13px",
                      }}
                    >
                      No active prescriptions on file.
                    </div>
                  )}
                </section>
              </>
            ) : (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.lg,
                  border: "1px solid #CBD5E1",
                  padding: "32px 20px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "40px", marginBottom: "12px" }}>🌿</div>
                <h2 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, marginBottom: "8px" }}>
                  Welcome to LoveWorld Care
                </h2>
                <p style={{ fontSize: "14px", color: "#64748B", marginBottom: "20px" }}>
                  Connect with licensed medical practitioners, track clinical care plans, and maintain health continuity.
                </p>
                <button
                  type="button"
                  onClick={() => setIsWizardOpen(true)}
                  style={{
                    minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                    padding: "10px 24px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    fontWeight: 700,
                    fontSize: "14px",
                    cursor: "pointer",
                  }}
                >
                  Start Medical Intake
                </button>
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: COMPANION CHAT (LWC-SCR-102, LWC-INT-001)                  */}
        {/* ================================================================= */}
        {activeTab === "COMPANION" && (
          <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 220px)" }}>
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                border: "1px solid #E2E8F0",
                padding: "12px 14px",
                marginBottom: "10px",
              }}
            >
              <div style={{ fontSize: "14px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                Health Intelligence Companion
              </div>
              <div style={{ fontSize: "12px", color: "#64748B" }}>
                Protocol-governed clinical navigation & red-flag screening. Does not replace physician diagnosis.
              </div>
            </div>

            {/* Chat Messages Stream */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                padding: "8px 0",
              }}
            >
              {chatMessages.length === 0 && (
                <div style={{ textAlign: "center", padding: "30px 16px", color: "#64748B" }}>
                  <div style={{ fontSize: "36px", marginBottom: "8px" }}>🩺</div>
                  <p style={{ fontWeight: 700, fontSize: "15px", color: "#1E293B", marginBottom: "4px" }}>
                    How can we support your health today?
                  </p>
                  <p style={{ fontSize: "13px", maxWidth: "340px", margin: "0 auto 16px" }}>
                    Describe your symptoms, ask about medication schedules, or navigate to doctor consultations.
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px" }}>
                    <button
                      type="button"
                      onClick={() => handleSendChatMessage("I have had a mild fever and headache for 2 days")}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "16px",
                        backgroundColor: "#FFFFFF",
                        border: "1px solid #CBD5E1",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      "Mild fever & headache"
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSendChatMessage("How do I take my prescribed blood pressure medicine?")}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "16px",
                        backgroundColor: "#FFFFFF",
                        border: "1px solid #CBD5E1",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      "Medication routine advice"
                    </button>
                  </div>
                </div>
              )}

              {chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    alignSelf: msg.sender === "USER" ? "flex-end" : "flex-start",
                    maxWidth: "85%",
                    backgroundColor: msg.sender === "USER" ? LW_DESIGN_TOKENS.colors.royalNavy : "#FFFFFF",
                    color: msg.sender === "USER" ? "#FFFFFF" : "#1E293B",
                    borderRadius: LW_DESIGN_TOKENS.radius.lg,
                    border: msg.emergency ? "2px solid #DC2626" : "1px solid #E2E8F0",
                    padding: "12px 16px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                  }}
                >
                  {msg.emergency && (
                    <div
                      style={{
                        backgroundColor: "#FEE2E2",
                        color: "#991B1B",
                        fontWeight: 800,
                        fontSize: "12px",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        marginBottom: "8px",
                        textTransform: "uppercase",
                      }}
                    >
                      🚨 Hard Stop Emergency Protocol Triggered
                    </div>
                  )}

                  <div style={{ fontSize: "14px", lineHeight: 1.5 }}>{msg.text}</div>

                  {/* Emergency Contacts if applicable */}
                  {msg.contacts && msg.contacts.length > 0 && (
                    <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid #FCA5A5" }}>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#991B1B", marginBottom: "4px" }}>
                        Verified Emergency Dispatch:
                      </div>
                      {msg.contacts.map((c, ci) => (
                        <div key={ci} style={{ fontSize: "13px", margin: "2px 0" }}>
                          <strong>{c.label}:</strong>{" "}
                          <a href={`tel:${c.phone}`} style={{ color: "#DC2626", fontWeight: 800 }}>
                            {c.phone}
                          </a>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Provenance Badge */}
                  {msg.provenance && (
                    <div
                      style={{
                        marginTop: "8px",
                        paddingTop: "6px",
                        borderTop: "1px solid #F1F5F9",
                        fontSize: "10px",
                        color: "#94A3B8",
                      }}
                    >
                      Protocol: {msg.provenance.protocol_id} · Source: {msg.provenance.source}
                    </div>
                  )}
                </div>
              ))}

              {isSendingChat && (
                <div style={{ alignSelf: "flex-start", padding: "8px 12px", color: "#64748B", fontSize: "13px" }}>
                  Companion analyzing protocol rules...
                </div>
              )}
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChatMessage();
              }}
              style={{ display: "flex", gap: "8px", marginTop: "10px" }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type symptoms or care query..."
                style={{
                  flex: 1,
                  minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                  padding: "10px 14px",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  border: "1px solid #CBD5E1",
                  fontSize: "14px",
                }}
              />
              <button
                type="submit"
                disabled={isSendingChat || !chatInput.trim()}
                style={{
                  minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                  padding: "0 18px",
                  backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontWeight: 700,
                  fontSize: "14px",
                  cursor: isSendingChat ? "not-allowed" : "pointer",
                }}
              >
                Send
              </button>
            </form>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: MY CARE & APPOINTMENTS (LWC-SCR-103..106)                   */}
        {/* ================================================================= */}
        {activeTab === "CARE" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Care Consultations & Plans
              </h2>
              <button
                type="button"
                onClick={() => {
                  setIsWizardOpen(true);
                  setWizardStep(1);
                  setChiefComplaint("");
                }}
                style={{
                  minHeight: "38px",
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
                + New Consultation
              </button>
            </div>

            {/* Active Care Plans */}
            <section aria-labelledby="care-plans-heading">
              <h3 id="care-plans-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", marginBottom: "8px" }}>
                Active Continuity Plans
              </h3>
              {carePlans.length > 0 ? (
                carePlans.map((plan) => (
                  <div
                    key={plan.plan_id}
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      padding: "14px",
                      marginBottom: "10px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 800, fontSize: "15px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                        {plan.programme_name}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          backgroundColor: "#DCFCE7",
                          color: "#166534",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {plan.status}
                      </span>
                    </div>
                    <div style={{ fontSize: "13px", color: "#475569", marginTop: "6px" }}>
                      {plan.monitoring_instructions}
                    </div>
                    {plan.goals && plan.goals.length > 0 && (
                      <div style={{ marginTop: "8px", fontSize: "12px", color: "#64748B" }}>
                        <strong>Goals:</strong> {plan.goals.join(", ")}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px dashed #CBD5E1",
                    padding: "16px",
                    textAlign: "center",
                    color: "#64748B",
                    fontSize: "13px",
                  }}
                >
                  No active continuity plans assigned.
                </div>
              )}
            </section>

            {/* Active Medications List */}
            <section aria-labelledby="active-meds-heading">
              <h3 id="active-meds-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", marginBottom: "8px" }}>
                Prescription Regimen
              </h3>
              {medications.length > 0 ? (
                medications.map((m) => (
                  <div
                    key={m.medication_id}
                    style={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #E2E8F0",
                      padding: "12px 14px",
                      marginBottom: "8px",
                    }}
                  >
                    <div style={{ fontWeight: 800, fontSize: "14px", color: "#0F172A" }}>
                      {m.medication_name}
                    </div>
                    <div style={{ fontSize: "13px", color: "#475569" }}>{m.dosage_instructions}</div>
                    <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                      Prescribed by {m.prescriber_clinician_name} · Indication: {m.clinical_indication}
                    </div>
                  </div>
                ))
              ) : (
                <div
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px dashed #CBD5E1",
                    padding: "16px",
                    textAlign: "center",
                    color: "#64748B",
                    fontSize: "13px",
                  }}
                >
                  No medications currently recorded.
                </div>
              )}
            </section>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 4: RECORDS & PROGRESS (LWC-SCR-107, 108)                       */}
        {/* ================================================================= */}
        {activeTab === "RECORDS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Health Timeline & Vitals
              </h2>
              <button
                type="button"
                onClick={() => setIsObservationModalOpen(true)}
                style={{
                  minHeight: "38px",
                  padding: "8px 14px",
                  backgroundColor: "#FFFFFF",
                  color: LW_DESIGN_TOKENS.colors.royalNavy,
                  border: `1px solid ${LW_DESIGN_TOKENS.colors.royalNavy}`,
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontWeight: 700,
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                + Log Vital
              </button>
            </div>

            {isLoadingRecords ? (
              <div style={{ textAlign: "center", padding: "30px", color: "#64748B" }}>
                Loading verified health records...
              </div>
            ) : recordsTimeline.length > 0 ? (
              recordsTimeline.map((rec: Record<string, unknown>, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    padding: "14px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 800,
                        backgroundColor: rec.type === "ENCOUNTER" ? "#DBEAFE" : "#FEF3C7",
                        color: rec.type === "ENCOUNTER" ? "#1E40AF" : "#92400E",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        textTransform: "uppercase",
                      }}
                    >
                      {String(rec.type)}
                    </span>
                    <span style={{ fontSize: "12px", color: "#94A3B8" }}>
                      {rec.date ? new Date(String(rec.date)).toLocaleDateString("en-NG") : ""}
                    </span>
                  </div>

                  {rec.type === "ENCOUNTER" && (
                    <>
                      <div style={{ fontWeight: 700, fontSize: "14px", color: "#0F172A" }}>
                        Clinical Encounter ({String(rec.modality || "VIDEO")})
                      </div>
                      {rec.chief_complaint && (
                        <div style={{ fontSize: "13px", color: "#475569", marginTop: "4px" }}>
                          <strong>Complaint:</strong> {String(rec.chief_complaint)}
                        </div>
                      )}
                      {rec.signed_note && (
                        <div
                          style={{
                            marginTop: "8px",
                            padding: "8px",
                            backgroundColor: "#F8FAFC",
                            borderRadius: "4px",
                            fontSize: "12px",
                            color: "#334155",
                          }}
                        >
                          <strong>Clinician Note:</strong> {String(rec.signed_note)}
                        </div>
                      )}
                      {rec.document_hash && (
                        <div style={{ marginTop: "8px" }}>
                          <SignedRecordSeal
                            signerName={String(rec.clinician_id || "Licensed Clinician")}
                            mdcnLicence="MDCN/R/44210"
                            signedAtIso={String(rec.date || "")}
                            documentSha256={String(rec.document_hash)}
                          />
                        </div>
                      )}
                    </>
                  )}

                  {rec.type === "OBSERVATION" && (
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "14px", color: "#0F172A" }}>
                        {String(rec.name)}: {String(rec.value)} {String(rec.unit || "")}
                      </div>
                      <div style={{ fontSize: "12px", color: "#64748B", marginTop: "2px" }}>
                        Source: {String(rec.source)} · Status: {String(rec.verification_status)}
                      </div>
                    </div>
                  )}

                  {rec.type === "PRESCRIPTION" && (
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "14px", color: "#0F172A" }}>
                        {String(rec.medication_name)}
                      </div>
                      <div style={{ fontSize: "13px", color: "#475569" }}>
                        {String(rec.dosage_instructions)}
                      </div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  border: "1px dashed #CBD5E1",
                  padding: "24px",
                  textAlign: "center",
                  color: "#64748B",
                  fontSize: "13px",
                }}
              >
                No historical clinical records recorded for this subject.
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 5: ACCOUNT & PROXIES (LWC-SCR-109..112)                       */}
        {/* ================================================================= */}
        {activeTab === "ACCOUNT" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
              Account & Relationship Management
            </h2>

            {/* Profile Overview Card */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                border: "1px solid #CBD5E1",
                padding: "16px",
              }}
            >
              <div style={{ fontWeight: 800, fontSize: "15px", color: "#0F172A" }}>Account Identity</div>
              <div style={{ fontSize: "13px", color: "#64748B", marginTop: "4px" }}>
                Primary User ID: <code>{accountUserId}</code>
              </div>
              <div style={{ fontSize: "13px", color: "#64748B", marginTop: "2px" }}>
                Contact Email: <strong>{accountEmail}</strong>
              </div>
              <div style={{ fontSize: "13px", color: "#64748B", marginTop: "2px" }}>
                Primary Jurisdiction: <strong>Nigeria (NG) · West Africa</strong>
              </div>
            </div>

            {/* Subjects / Dependents Management */}
            <section aria-labelledby="account-subjects-heading">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 id="account-subjects-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", margin: 0 }}>
                  Managed Subjects ({subjects.length})
                </h3>
                <button
                  type="button"
                  onClick={() => setIsAddSubjectModalOpen(true)}
                  style={{
                    padding: "6px 12px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  + Add Subject
                </button>
              </div>

              {subjects.map((s) => (
                <div
                  key={s.patient_id}
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #E2E8F0",
                    padding: "12px 14px",
                    marginBottom: "8px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: "14px", color: "#0F172A" }}>{s.full_name}</div>
                    <div style={{ fontSize: "12px", color: "#64748B" }}>
                      DOB: {new Date(s.date_of_birth_iso).toLocaleDateString()} · Gender: {s.gender}
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      backgroundColor: "#F1F5F9",
                      color: "#475569",
                      padding: "2px 8px",
                      borderRadius: "4px",
                    }}
                  >
                    {s.relationship_to_account}
                  </span>
                </div>
              ))}
            </section>

            {/* Passwordless Magic Link Authentication */}
            <section
              aria-labelledby="magic-link-heading"
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                border: "1px solid #CBD5E1",
                padding: "16px",
              }}
            >
              <h3 id="magic-link-heading" style={{ fontSize: "15px", fontWeight: 800, color: "#1E293B", margin: "0 0 8px" }}>
                Passwordless Sign-In Link
              </h3>
              <p style={{ fontSize: "13px", color: "#64748B", margin: "0 0 12px" }}>
                Sign in without passwords via a verified cryptographic magic link dispatched to your email.
              </p>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <input
                  type="email"
                  value={magicLinkEmail}
                  onChange={(e) => setMagicLinkEmail(e.target.value)}
                  style={{
                    flex: 1,
                    minHeight: "40px",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                />
                <button
                  type="button"
                  onClick={handleRequestMagicLink}
                  disabled={isSendingMagicLink}
                  style={{
                    minHeight: "40px",
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
                  {isSendingMagicLink ? "Sending..." : "Dispatch Link"}
                </button>
              </div>

              {magicLinkStatusMsg && (
                <div style={{ marginTop: "10px", fontSize: "13px", color: "#0369A1", fontWeight: 600 }}>
                  {magicLinkStatusMsg}
                </div>
              )}

              {magicLinkToken && (
                <button
                  type="button"
                  onClick={handleVerifyMagicLink}
                  style={{
                    marginTop: "10px",
                    width: "100%",
                    minHeight: "40px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    fontWeight: 700,
                    fontSize: "14px",
                    cursor: "pointer",
                  }}
                >
                  Confirm & Authenticate Session
                </button>
              )}
            </section>
          </div>
        )}
      </main>

      {/* ===================================================================== */}
      {/* MODAL: GUIDED INTAKE WIZARD (LWC-SCR-103)                             */}
      {/* ===================================================================== */}
      {isWizardOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="wizard-title"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
          }}
        >
          <div
            style={{
              backgroundColor: "#FFFFFF",
              borderRadius: LW_DESIGN_TOKENS.radius.lg,
              width: "100%",
              maxWidth: "540px",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 id="wizard-title" style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Consultation Intake (Step {wizardStep} of 3)
              </h2>
              <button
                type="button"
                onClick={() => setIsWizardOpen(false)}
                style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#64748B" }}
              >
                ✕
              </button>
            </div>

            {/* STEP 1: Red-Flag Emergency Triage */}
            {wizardStep === 1 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ fontSize: "14px", color: "#334155", fontWeight: 600 }}>
                  Emergency Safety Verification: Are you or the patient currently experiencing any of the following?
                </div>

                <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={hasChestPain}
                    onChange={(e) => setHasChestPain(e.target.checked)}
                    style={{ width: "18px", height: "18px" }}
                  />
                  <span>Severe, crushing, or radiating chest pain / pressure</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={hasBreathingDifficulty}
                    onChange={(e) => setHasBreathingDifficulty(e.target.checked)}
                    style={{ width: "18px", height: "18px" }}
                  />
                  <span>Severe shortness of breath or inability to breathe</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={hasUncontrolledBleeding}
                    onChange={(e) => setHasUncontrolledBleeding(e.target.checked)}
                    style={{ width: "18px", height: "18px" }}
                  />
                  <span>Uncontrolled bleeding or severe traumatic hemorrhage</span>
                </label>

                {hasEmergencyRedFlags ? (
                  <div
                    style={{
                      backgroundColor: "#FEE2E2",
                      border: "2px solid #DC2626",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      padding: "14px",
                      color: "#991B1B",
                    }}
                  >
                    <div style={{ fontWeight: 800, fontSize: "14px", marginBottom: "4px" }}>
                      🚨 CRITICAL MEDICAL EMERGENCY
                    </div>
                    <p style={{ fontSize: "13px", margin: "0 0 10px", lineHeight: 1.4 }}>
                      Teleconsultation is unsafe for these acute symptoms. Please immediately call 112 / 767 or proceed to the nearest hospital emergency room.
                    </p>
                    <a
                      href="tel:112"
                      style={{
                        display: "inline-block",
                        padding: "8px 16px",
                        backgroundColor: "#DC2626",
                        color: "#FFFFFF",
                        fontWeight: 800,
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        textDecoration: "none",
                      }}
                    >
                      Call 112 National Emergency
                    </a>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    style={{
                      marginTop: "12px",
                      minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                      backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 700,
                      fontSize: "14px",
                      cursor: "pointer",
                    }}
                  >
                    Confirm No Emergency & Continue →
                  </button>
                )}
              </div>
            )}

            {/* STEP 2: Symptoms & Primary Narrative */}
            {wizardStep === 2 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Preferred Language for Consultation:
                  </label>
                  <select
                    value={intakeLanguage}
                    onChange={(e) => setIntakeLanguage(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  >
                    <option value="en-NG">English (Nigeria)</option>
                    <option value="pcm-NG">Nigerian Pidgin</option>
                    <option value="yo-NG">Yorùbá</option>
                    <option value="ig-NG">Igbo</option>
                    <option value="ha-NG">Hausa</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Symptom Category:
                  </label>
                  <select
                    value={symptomCategory}
                    onChange={(e) => setSymptomCategory(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  >
                    <option value="FEVER_OR_MALARIA_LIKE">Fever, chills, body ache (Malaria-like)</option>
                    <option value="RESPIRATORY_COLD_COUGH">Cough, catarrh, sore throat</option>
                    <option value="GASTROINTESTINAL">Stomach ache, nausea, diarrhoea</option>
                    <option value="HYPERTENSION_CARDIO">Blood pressure review / Cardiovascular</option>
                    <option value="ROUTINE_CHECKUP">General checkup / Follow-up</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Duration of Symptoms (Days):
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={durationDays}
                    onChange={(e) => setDurationDays(Number(e.target.value))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Describe what you are feeling in your own words:
                  </label>
                  <textarea
                    rows={4}
                    value={chiefComplaint}
                    onChange={(e) => setChiefComplaint(e.target.value)}
                    placeholder="Enter your chief complaint, pain location, and symptoms..."
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  />
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(1)}
                    style={{
                      flex: 1,
                      minHeight: "44px",
                      backgroundColor: "#F1F5F9",
                      border: "1px solid #CBD5E1",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    disabled={!chiefComplaint.trim()}
                    style={{
                      flex: 2,
                      minHeight: "44px",
                      backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 700,
                      cursor: chiefComplaint.trim() ? "pointer" : "not-allowed",
                    }}
                  >
                    Continue to Booking →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Modality, Doctor Slot & Funding Selection */}
            {wizardStep === 3 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Consultation Modality:
                  </label>
                  <select
                    value={selectedModality}
                    onChange={(e) => setSelectedModality(e.target.value as ConsultationModality)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  >
                    <option value="VIDEO">Live Video Consultation (Recommended)</option>
                    <option value="AUDIO_FALLBACK">Encrypted Audio Call</option>
                    <option value="ASYNC_CLINICAL_MESSAGING">Asynchronous Secure Chat Review</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Select Staffed Doctor Roster Slot:
                  </label>
                  {availableSlots.length > 0 ? (
                    <select
                      value={selectedSlotId}
                      onChange={(e) => setSelectedSlotId(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        border: "1px solid #CBD5E1",
                        fontSize: "14px",
                      }}
                    >
                      {availableSlots.map((s) => (
                        <option key={s.slot_id} value={s.slot_id}>
                          {s.clinician_display_name} ({s.specialty}) · {new Date(s.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div style={{ fontSize: "13px", color: "#64748B", padding: "8px 0" }}>
                      Queueing into next available verified primary care doctor.
                    </div>
                  )}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Funding / Coverage Route:
                  </label>
                  <select
                    value={fundingRoute}
                    onChange={(e) => setFundingRoute(e.target.value as FundingRouteType)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  >
                    <option value="SPONSOR_DEFINED_SERVICES">SponsorCare Medicaid Pool (100% Covered)</option>
                    <option value="ESPEES_WALLET_DIRECT">Espees Wallet Direct</option>
                    <option value="SELF_PAY">Self-Pay (Paystack Debit Card / Bank Transfer)</option>
                  </select>
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    style={{
                      flex: 1,
                      minHeight: "44px",
                      backgroundColor: "#F1F5F9",
                      border: "1px solid #CBD5E1",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={handleCompleteBooking}
                    disabled={isSubmittingIntake}
                    style={{
                      flex: 2,
                      minHeight: "44px",
                      backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 800,
                      fontSize: "14px",
                      cursor: isSubmittingIntake ? "not-allowed" : "pointer",
                    }}
                  >
                    {isSubmittingIntake ? "Confirming Booking..." : "Submit Intake & Book Doctor"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL: ADD DEPENDENT / PATIENT SUBJECT (LWC-SCR-110)                 */}
      {/* ===================================================================== */}
      {isAddSubjectModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-subject-title"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
          }}
        >
          <form
            onSubmit={handleCreateSubject}
            style={{
              backgroundColor: "#FFFFFF",
              borderRadius: LW_DESIGN_TOKENS.radius.lg,
              width: "100%",
              maxWidth: "480px",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 id="add-subject-title" style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Register Dependent or Ward
              </h2>
              <button
                type="button"
                onClick={() => setIsAddSubjectModalOpen(false)}
                style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#64748B" }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Full Legal Name:
                </label>
                <input
                  type="text"
                  required
                  value={newSubjName}
                  onChange={(e) => setNewSubjName(e.target.value)}
                  placeholder="e.g. Samuel Adeleke"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Date of Birth:
                </label>
                <input
                  type="date"
                  required
                  value={newSubjDob}
                  onChange={(e) => setNewSubjDob(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Biological Sex:
                </label>
                <select
                  value={newSubjGender}
                  onChange={(e) => setNewSubjGender(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                >
                  <option value="FEMALE">Female</option>
                  <option value="MALE">Male</option>
                  <option value="INTERSEX">Intersex</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Relationship to You:
                </label>
                <select
                  value={newSubjRel}
                  onChange={(e) => setNewSubjRel(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                >
                  <option value="CHILD">Child / Minor Dependent</option>
                  <option value="SPOUSE">Spouse / Partner</option>
                  <option value="PARENT">Elder Parent</option>
                  <option value="DEPENDENT">Ward / Other Dependent</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isCreatingSubject || !newSubjName.trim() || !newSubjDob}
                style={{
                  marginTop: "8px",
                  minHeight: "44px",
                  backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontWeight: 700,
                  fontSize: "14px",
                  cursor: isCreatingSubject ? "not-allowed" : "pointer",
                }}
              >
                {isCreatingSubject ? "Registering..." : "Create Subject Profile"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL: LOG CLINICAL OBSERVATION / VITAL (LWC-SCR-108)                 */}
      {/* ===================================================================== */}
      {isObservationModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="obs-modal-title"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
          }}
        >
          <form
            onSubmit={handleSaveObservation}
            style={{
              backgroundColor: "#FFFFFF",
              borderRadius: LW_DESIGN_TOKENS.radius.lg,
              width: "100%",
              maxWidth: "460px",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 id="obs-modal-title" style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Record Health Vital
              </h2>
              <button
                type="button"
                onClick={() => setIsObservationModalOpen(false)}
                style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#64748B" }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Measurement Type:
                </label>
                <select
                  value={obsName}
                  onChange={(e) => {
                    setObsName(e.target.value);
                    if (e.target.value.includes("Pressure")) setObsUnit("mmHg");
                    else if (e.target.value.includes("Glucose")) setObsUnit("mg/dL");
                    else if (e.target.value.includes("Temperature")) setObsUnit("°C");
                    else if (e.target.value.includes("Weight")) setObsUnit("kg");
                  }}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "14px",
                  }}
                >
                  <option value="Blood Pressure">Blood Pressure (e.g. 120/80)</option>
                  <option value="Fasting Blood Glucose">Fasting Blood Glucose</option>
                  <option value="Body Temperature">Body Temperature</option>
                  <option value="Body Weight">Body Weight</option>
                  <option value="Heart Rate / Pulse">Heart Rate / Pulse</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Value:
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    required
                    value={obsValue}
                    onChange={(e) => setObsValue(e.target.value)}
                    placeholder="e.g. 120/80 or 98"
                    style={{
                      flex: 2,
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  />
                  <input
                    type="text"
                    value={obsUnit}
                    onChange={(e) => setObsUnit(e.target.value)}
                    placeholder="Unit"
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "14px",
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Context / Notes (Optional):
                </label>
                <textarea
                  rows={2}
                  value={obsNotes}
                  onChange={(e) => setObsNotes(e.target.value)}
                  placeholder="e.g. Measured before breakfast"
                  style={{
                    width: "100%",
                    padding: "8px",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    border: "1px solid #CBD5E1",
                    fontSize: "13px",
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={isSavingObs || !obsValue.trim()}
                style={{
                  marginTop: "8px",
                  minHeight: "44px",
                  backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontWeight: 700,
                  fontSize: "14px",
                  cursor: isSavingObs ? "not-allowed" : "pointer",
                }}
              >
                {isSavingObs ? "Saving..." : "Save to Clinical Record"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 4. Bottom Navigation Bar */}
      <MobileBottomNavBar
        activeTab={activeTab}
        onSelectTab={(id) => setActiveTab(id as PatientNavTab)}
        items={NAV_ITEMS}
      />
    </div>
  );
}
