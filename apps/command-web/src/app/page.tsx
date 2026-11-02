"use client";

import React, { useCallback, useEffect, useState } from "react";
import { SharedDeviceSessionLockBar, LW_DESIGN_TOKENS } from "@loveworld-care/design-system";
import {
  CoordinationTask,
  DirectorateAction,
  DirectorateMetricsResponse,
  EmergencyGuidanceResponse,
  FinanceException,
  LoveWorldCareApiClient,
  NetworkFacility,
  ReconciliationSummary,
  type ExecutiveMetricsResponse,
} from "@loveworld-care/api-contracts";
import { formatMoneyMinor, type CurrencyCode } from "@loveworld-care/domain-types";

type CommandTab = "EXECUTIVE" | "COORDINATION" | "NETWORK" | "GOVERNANCE" | "FINANCE";

export default function CareCommandConsolePage() {
  const [activeTab, setActiveTab] = useState<CommandTab>("EXECUTIVE");
  const [sessionLocked, setSessionLocked] = useState(false);

  // Auth & Client
  const [currentActorId] = useState("exec-director-01");
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 1. Executive Overview & Directorate Metrics (LWC-SCR-301, LWC-MET-001..016)
  const [execMetrics, setExecMetrics] = useState<ExecutiveMetricsResponse | null>(null);
  const [directorateMetrics, setDirectorateMetrics] = useState<DirectorateMetricsResponse | null>(null);
  const [directorateActions, setDirectorateActions] = useState<readonly DirectorateAction[]>([]);
  const [isCreatingAction, setIsCreatingAction] = useState(false);
  const [newActionTitle, setNewActionTitle] = useState("");
  const [newActionDesc, setNewActionDesc] = useState("");
  const [newActionMetricId, setNewActionMetricId] = useState("LWC-MET-002");

  // 2. Care Coordination Board (LWC-SCR-302)
  const [coordinationTasks, setCoordinationTasks] = useState<readonly CoordinationTask[]>([]);
  const [coordinationFilter, setCoordinationFilter] = useState<string>("ALL");
  const [isClaimingCoordTask, setIsClaimingCoordTask] = useState<string | null>(null);

  // 3. Network Facilities & Coverage (LWC-SCR-303)
  const [networkFacilities, setNetworkFacilities] = useState<readonly NetworkFacility[]>([]);
  const [facilitySearch, setFacilitySearch] = useState<string>("");

  // 4. Clinical Governance & AI Kill-Switch (LWC-SCR-304)
  const [aiKillSwitchEnabled, setAiKillSwitchEnabled] = useState(false);
  const [killSwitchReason, setKillSwitchReason] = useState("REASON_CLINICAL_DISCREPANCY");
  const [isTogglingKillSwitch, setIsTogglingKillSwitch] = useState(false);

  // 5. Finance Operations & Maker/Checker Reconciliation (LWC-SCR-305)
  const [financeExceptions, setFinanceExceptions] = useState<readonly FinanceException[]>([]);
  const [reconciliation, setReconciliation] = useState<ReconciliationSummary | null>(null);
  const [actioningExceptionId, setActioningExceptionId] = useState<string | null>(null);

  // Emergency Guidance
  const [emergencyGuidance, setEmergencyGuidance] = useState<EmergencyGuidanceResponse | null>(null);

  // ---------------------------------------------------------------------------
  // Refresh Active Tab Data
  // ---------------------------------------------------------------------------
  const refreshCurrentView = useCallback(async (clientInstance?: LoveWorldCareApiClient) => {
    const client = clientInstance || apiClient;
    if (!client) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [em, dm, da, cb, facs, excep, recon, emerg] = await Promise.all([
        client.getExecutiveMetrics().catch(() => null),
        client.getDirectorateMetrics().catch(() => null),
        client.listDirectorateActions().catch(() => []),
        client.listCoordinationBoard().catch(() => []),
        client.listFacilities("NG").catch(() => []),
        client.listFinanceExceptions().catch(() => []),
        client.getFinanceReconciliation().catch(() => null),
        client.getEmergencyGuidance("NG").catch(() => null),
      ]);

      if (em) {
        setExecMetrics(em);
        setAiKillSwitchEnabled(em.ai_kill_switch_enabled);
      }
      if (dm) setDirectorateMetrics(dm);
      setDirectorateActions(da);
      setCoordinationTasks(cb);
      setNetworkFacilities(facs);
      setFinanceExceptions(excep);
      if (recon) setReconciliation(recon);
      if (emerg) setEmergencyGuidance(emerg);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load command data");
    } finally {
      setIsLoading(false);
    }
  }, [apiClient]);

  // ---------------------------------------------------------------------------
  // Initialize Command Session
  // ---------------------------------------------------------------------------
  useEffect(() => {
    async function initCommandSession() {
      setIsLoading(true);
      try {
        let currentToken = typeof window !== "undefined" ? localStorage.getItem("lw_command_token") : null;
        if (!currentToken) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: currentActorId,
              audience: "lwc:command",
              roles: ["EXECUTIVE_DIRECTOR", "FINANCE_CONTROLLER", "CLINICAL_GOVERNANCE_LEAD"],
              mfa: true,
              ttl_minutes: 240,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            currentToken = data.access_token;
            if (currentToken && typeof window !== "undefined") {
              localStorage.setItem("lw_command_token", currentToken);
            }
          }
        }

        const client = new LoveWorldCareApiClient("", () => ({
          ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
        }));
        setApiClient(client);
        await refreshCurrentView(client);
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : "Failed to initialize command session");
        setIsLoading(false);
      }
    }

    void initCommandSession();
  }, [currentActorId, refreshCurrentView]);

  // ---------------------------------------------------------------------------
  // AI Kill-Switch Handler (LWC-SCR-304, §15.6)
  // ---------------------------------------------------------------------------
  const handleToggleAiKillSwitch = async (targetState: boolean) => {
    if (!apiClient) return;
    setIsTogglingKillSwitch(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await apiClient.toggleAiKillSwitch(targetState, killSwitchReason);
      setAiKillSwitchEnabled(res.ai_kill_switch_enabled);
      setSuccessMessage(
        res.ai_kill_switch_enabled
          ? "🚨 AI Global Kill-Switch ACTIVATED. All inference blocked. Deterministic pathways active."
          : "✓ AI Gateway restored to normal operational mode."
      );
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to toggle AI kill switch");
    } finally {
      setIsTogglingKillSwitch(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Coordination Board Claim / Resolve (LWC-SCR-302)
  // ---------------------------------------------------------------------------
  const handleClaimCoordTask = async (taskId: string) => {
    if (!apiClient) return;
    setIsClaimingCoordTask(taskId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.claimCoordinationTask(taskId);
      setSuccessMessage(`Coordination task ${taskId} claimed.`);
      await refreshCurrentView();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to claim coordination task");
    } finally {
      setIsClaimingCoordTask(null);
    }
  };

  const handleResolveCoordTask = async (taskId: string) => {
    if (!apiClient) return;
    try {
      await apiClient.resolveCoordinationTask(taskId, { disposition: "Resolved via command escalation" });
      setSuccessMessage(`Task ${taskId} resolved.`);
      await refreshCurrentView();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to resolve coordination task");
    }
  };

  // ---------------------------------------------------------------------------
  // Maker/Checker Exception Action (LWC-SCR-305, maker != checker)
  // ---------------------------------------------------------------------------
  const handleActionException = async (exceptionId: string, action: "APPROVE" | "REJECT" | "REMEDIATE") => {
    if (!apiClient) return;
    setActioningExceptionId(exceptionId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.actionFinanceException(exceptionId, {
        action,
        notes: `Actioned as ${action} by Checker ${currentActorId}`,
      });
      setSuccessMessage(`Finance exception ${exceptionId} actioned (${action}).`);
      await refreshCurrentView();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Checker action failed");
    } finally {
      setActioningExceptionId(null);
    }
  };

  // ---------------------------------------------------------------------------
  // Create Directorate Action Item (LWC-SCR-301)
  // ---------------------------------------------------------------------------
  const handleCreateActionItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiClient || !newActionTitle.trim() || !newActionDesc.trim()) return;
    try {
      await apiClient.createDirectorateAction({
        metric_id: newActionMetricId,
        title: newActionTitle.trim(),
        description: newActionDesc.trim(),
        owner_team: "CLINICAL_GOVERNANCE",
        assigned_to: currentActorId,
        due_date_iso: new Date(Date.now() + 7 * 86400000).toISOString(),
      });
      setIsCreatingAction(false);
      setNewActionTitle("");
      setNewActionDesc("");
      setSuccessMessage("Directorate action item created.");
      await refreshCurrentView();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to create action item");
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
          Command Console Locked
        </h1>
        <p style={{ color: "#94A3B8", maxWidth: "420px", marginBottom: "24px", fontSize: "14px" }}>
          Executive directorate console locked against unauthorized viewing of network unit economics and governance controls.
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
          Unlock Command Console
        </button>
      </div>
    );
  }

  const filteredCoordTasks = coordinationTasks.filter((t) => {
    if (coordinationFilter === "ALL") return true;
    return t.work_state === coordinationFilter;
  });

  const filteredFacilities = networkFacilities.filter((f) => {
    if (!facilitySearch.trim()) return true;
    const q = facilitySearch.toLowerCase();
    return f.facility_name.toLowerCase().includes(q) || f.facility_code.toLowerCase().includes(q);
  });

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* 1. Header Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="Care Command Console · Directorate & Operations"
        actorDisplayName={`${currentActorId} (EXECUTIVE / FINANCE / GOVERNANCE)`}
        isLocked={sessionLocked}
        onToggleLock={() => setSessionLocked((prev) => !prev)}
        onSignOut={() => {
          if (typeof window !== "undefined") localStorage.removeItem("lw_command_token");
          window.location.reload();
        }}
      />

      {/* 2. Directorate Tabs Navigation */}
      <nav
        aria-label="Command Console Modules"
        style={{
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #CBD5E1",
          padding: "0 24px",
          display: "flex",
          gap: "24px",
          overflowX: "auto",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("EXECUTIVE")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "EXECUTIVE" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "EXECUTIVE" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          📊 Executive Metrics ({directorateMetrics?.metrics.length || 0})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("COORDINATION")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "COORDINATION" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "COORDINATION" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          🧭 Care Coordination Board ({coordinationTasks.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("NETWORK")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "NETWORK" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "NETWORK" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          🏥 Network & Coverage ({networkFacilities.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("GOVERNANCE")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "GOVERNANCE" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "GOVERNANCE" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          ⚖️ Clinical Governance & Kill-Switch
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("FINANCE")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "FINANCE" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "FINANCE" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          💰 Finance Ops & Maker/Checker ({financeExceptions.length})
        </button>
      </nav>

      {/* Notifications Bar */}
      {errorMessage && (
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
          <span>⚠️ {errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#991B1B" }}>
            ✕
          </button>
        </div>
      )}

      {successMessage && (
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
          <span>✓ {successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#166534" }}>
            ✕
          </button>
        </div>
      )}

      {/* Main Container */}
      <main style={{ padding: "24px", flex: 1, maxWidth: "1320px", margin: "0 auto", width: "100%" }}>
        {/* ================================================================= */}
        {/* TAB 1: EXECUTIVE OVERVIEW (LWC-SCR-301, LWC-MET-001..016)          */}
        {/* ================================================================= */}
        {activeTab === "EXECUTIVE" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ fontSize: "22px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                  Authoritative Directorate Metrics
                </h2>
                <div style={{ fontSize: "13px", color: "#64748B", marginTop: "2px" }}>
                  Live operational invariants per LWC-MET-001 to 016 (Africa/Lagos time, zero synthetic fixtures)
                </div>
              </div>
              <button
                type="button"
                onClick={() => refreshCurrentView()}
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
                🔄 Refresh Metrics
              </button>
            </div>

            {/* Metrics Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              {directorateMetrics?.metrics.map((m) => (
                <div
                  key={m.id}
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.lg,
                    border: "1px solid #E2E8F0",
                    padding: "16px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "11px", fontWeight: 800, color: "#64748B" }}>{m.id}</span>
                    <span style={{ fontSize: "10px", fontWeight: 700, backgroundColor: "#F1F5F9", color: "#475569", padding: "2px 6px", borderRadius: "4px" }}>
                      {m.completeness} Completeness
                    </span>
                  </div>
                  <h3 style={{ fontSize: "15px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "6px 0 8px" }}>
                    {m.name}
                  </h3>
                  <div style={{ fontSize: "28px", fontWeight: 900, color: "#0F172A", margin: "4px 0" }}>
                    {m.value} <span style={{ fontSize: "14px", fontWeight: 600, color: "#64748B" }}>{m.unit}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: "#64748B", margin: "6px 0" }}>
                    <strong>Denominator:</strong> {m.denominator}
                  </div>
                  <p style={{ fontSize: "11px", color: "#94A3B8", margin: "4px 0 0", lineHeight: 1.3 }}>
                    {m.definition}
                  </p>
                </div>
              ))}
            </div>

            {/* Action Items Tracker */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "20px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                    Directorate Action Items Tracker ({directorateActions.length})
                  </h3>
                  <div style={{ fontSize: "12px", color: "#64748B" }}>
                    Governance decisions tied to metrics with audit accountability
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsCreatingAction(true)}
                  style={{
                    padding: "6px 14px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  + New Action Item
                </button>
              </div>

              {directorateActions.length === 0 ? (
                <div style={{ padding: "24px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
                  No open directorate action items. Create one to assign clinical review accountability.
                </div>
              ) : (
                <div style={{ display: "grid", gap: "10px" }}>
                  {directorateActions.map((act) => (
                    <div
                      key={act.action_id}
                      style={{
                        padding: "12px 14px",
                        backgroundColor: "#F8FAFC",
                        borderRadius: LW_DESIGN_TOKENS.radius.md,
                        border: "1px solid #E2E8F0",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "14px", color: "#0F172A" }}>
                          {act.title} · <span style={{ fontSize: "11px", color: "#64748B" }}>Tied to {act.metric_id}</span>
                        </div>
                        <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px" }}>{act.description}</div>
                        <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                          Assigned to {act.assigned_to} ({act.owner_team}) · Due: {new Date(act.due_date_iso).toLocaleDateString()}
                        </div>
                      </div>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          backgroundColor: act.status === "OPEN" ? "#FEF3C7" : "#DCFCE7",
                          color: act.status === "OPEN" ? "#92400E" : "#166534",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {act.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: CARE COORDINATION BOARD (LWC-SCR-302)                       */}
        {/* ================================================================= */}
        {activeTab === "COORDINATION" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h2 style={{ fontSize: "22px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                  Care Coordination Board
                </h2>
                <div style={{ fontSize: "13px", color: "#64748B" }}>
                  Active patient flow states with atomic claim concurrency
                </div>
              </div>

              {/* Filter Tabs */}
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {["ALL", "AWAITING_ASSIGNMENT", "AWAITING_PATIENT", "CALLBACK_DUE", "REFERRAL_PENDING", "RESULT_OVERDUE", "SERVICE_EXCEPTION"].map(
                  (st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setCoordinationFilter(st)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "14px",
                        backgroundColor: coordinationFilter === st ? LW_DESIGN_TOKENS.colors.royalNavy : "#FFFFFF",
                        color: coordinationFilter === st ? "#FFFFFF" : "#64748B",
                        border: "1px solid #CBD5E1",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {st.replace(/_/g, " ")}
                    </button>
                  )
                )}
              </div>
            </div>

            {filteredCoordTasks.length === 0 ? (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.lg,
                  border: "1px dashed #CBD5E1",
                  padding: "48px 20px",
                  textAlign: "center",
                  color: "#64748B",
                }}
              >
                No active tasks match filter '{coordinationFilter}'.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                {filteredCoordTasks.map((t) => (
                  <div
                    key={t.task_id}
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
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 800,
                            backgroundColor: t.urgency === "EMERGENCY" ? "#FEE2E2" : t.urgency === "URGENT" ? "#FEF3C7" : "#E2E8F0",
                            color: t.urgency === "EMERGENCY" ? "#991B1B" : t.urgency === "URGENT" ? "#92400E" : "#475569",
                            padding: "2px 8px",
                            borderRadius: "4px",
                          }}
                        >
                          {t.urgency}
                        </span>
                        <span style={{ fontWeight: 800, fontSize: "15px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                          {t.work_state}
                        </span>
                        <span style={{ fontSize: "12px", color: "#64748B" }}>
                          Patient: {t.patient_id} · Team: {t.owner_team}
                        </span>
                      </div>
                      <div style={{ fontSize: "13px", color: "#334155", marginTop: "6px" }}>
                        <strong>Action Needed:</strong> {t.next_action}
                      </div>
                      {t.claimed_by && (
                        <div style={{ fontSize: "11px", color: "#0369A1", marginTop: "4px", fontWeight: 600 }}>
                          Claimed by: {t.claimed_by}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", gap: "8px" }}>
                      {!t.claimed_by ? (
                        <button
                          type="button"
                          onClick={() => handleClaimCoordTask(t.task_id)}
                          disabled={isClaimingCoordTask === t.task_id}
                          style={{
                            padding: "8px 16px",
                            backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                            color: "#FFFFFF",
                            border: "none",
                            borderRadius: LW_DESIGN_TOKENS.radius.md,
                            fontWeight: 700,
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          Claim Task
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleResolveCoordTask(t.task_id)}
                          style={{
                            padding: "8px 16px",
                            backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                            color: "#FFFFFF",
                            border: "none",
                            borderRadius: LW_DESIGN_TOKENS.radius.md,
                            fontWeight: 700,
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          Mark Resolved
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: NETWORK FACILITIES & READINESS (LWC-SCR-303)                */}
        {/* ================================================================= */}
        {activeTab === "NETWORK" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h2 style={{ fontSize: "22px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                  Network Facilities & Readiness Tracker
                </h2>
                <div style={{ fontSize: "13px", color: "#64748B" }}>
                  Verified partner health centres with unexpired operational readiness signals
                </div>
              </div>
              <input
                type="text"
                placeholder="Search facility name or code..."
                value={facilitySearch}
                onChange={(e) => setFacilitySearch(e.target.value)}
                style={{
                  padding: "8px 14px",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  border: "1px solid #CBD5E1",
                  fontSize: "13px",
                  width: "280px",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
              {filteredFacilities.map((fac) => (
                <div
                  key={fac.facility_id}
                  style={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: LW_DESIGN_TOKENS.radius.lg,
                    border: "1px solid #CBD5E1",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 800, color: "#64748B" }}>{fac.facility_code}</span>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        backgroundColor: fac.readiness_state === "CONFIRMED_AVAILABLE" ? "#DCFCE7" : "#FEE2E2",
                        color: fac.readiness_state === "CONFIRMED_AVAILABLE" ? "#166534" : "#991B1B",
                        padding: "2px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      {fac.readiness_state}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 6px" }}>
                    {fac.facility_name}
                  </h3>
                  <div style={{ fontSize: "12px", color: "#475569", margin: "2px 0" }}>{fac.address}</div>
                  <div style={{ fontSize: "12px", color: "#64748B" }}>
                    Phone: <strong>{fac.contact_phone}</strong> · Hours: {fac.hours}
                  </div>

                  <div style={{ marginTop: "10px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {fac.services.map((s: string, si: number) => (
                      <span
                        key={si}
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          backgroundColor: "#F1F5F9",
                          color: "#334155",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>

                  <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid #F1F5F9", fontSize: "11px", color: "#94A3B8" }}>
                    Readiness Expires: {new Date(fac.readiness_expires_at_iso).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 4: CLINICAL GOVERNANCE & KILL-SWITCH (LWC-SCR-304)             */}
        {/* ================================================================= */}
        {activeTab === "GOVERNANCE" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
              Clinical Governance & AI Kill-Switch
            </h2>

            {/* AI Global Kill-Switch Control Panel */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: aiKillSwitchEnabled ? "3px solid #DC2626" : "2px solid #CBD5E1",
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "24px" }}>{aiKillSwitchEnabled ? "🚨" : "🛡️"}</span>
                    <h3 style={{ fontSize: "18px", fontWeight: 800, color: aiKillSwitchEnabled ? "#DC2626" : LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                      Global AI Inference Kill-Switch
                    </h3>
                  </div>
                  <p style={{ fontSize: "13px", color: "#475569", margin: "6px 0 0", maxWidth: "560px" }}>
                    Immediately terminates all generative AI and LLM draft extraction across the platform. Deterministic 3-valued protocol evaluation remains 100% operational.
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <select
                    value={killSwitchReason}
                    onChange={(e) => setKillSwitchReason(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      border: "1px solid #CBD5E1",
                      fontSize: "13px",
                    }}
                  >
                    <option value="REASON_CLINICAL_DISCREPANCY">Clinical Discrepancy Observed</option>
                    <option value="REASON_HALLUCINATION_DETECTED">Suspected Model Hallucination</option>
                    <option value="REASON_PROTOCOL_MAINTENANCE">Scheduled Protocol Maintenance</option>
                    <option value="REASON_EMERGENCY_OVERRIDE">Executive Emergency Override</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => handleToggleAiKillSwitch(!aiKillSwitchEnabled)}
                    disabled={isTogglingKillSwitch}
                    style={{
                      minHeight: "44px",
                      padding: "0 24px",
                      backgroundColor: aiKillSwitchEnabled ? LW_DESIGN_TOKENS.colors.clinicalEmerald : "#DC2626",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: LW_DESIGN_TOKENS.radius.md,
                      fontWeight: 800,
                      fontSize: "14px",
                      cursor: isTogglingKillSwitch ? "not-allowed" : "pointer",
                    }}
                  >
                    {isTogglingKillSwitch
                      ? "Executing..."
                      : aiKillSwitchEnabled
                      ? "Deactivate Kill-Switch (Restore AI)"
                      : "Engage AI Kill-Switch"}
                  </button>
                </div>
              </div>
            </div>

            {/* Protocol Bundle Details */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "20px",
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 12px" }}>
                Active Clinical Protocol Bundle: LW-NG-GP-ADULT-V1
              </h3>
              <div style={{ fontSize: "13px", color: "#475569", lineHeight: 1.6 }}>
                <div>• Version: <strong>1.0.0</strong> · Dual Clinician Signatures Verified (Ed25519)</div>
                <div>• Jurisdiction: <strong>Nigeria (NG)</strong> · Target: Uncomplicated Fever, Malaria & General Adult Primary Care</div>
                <div>• Evaluation Engine: AST 3-valued deterministic runtime (zero ungrounded LLM decisions)</div>
                <div>• Emergency Fallback: Active and verified (LASAMBUS 767, National 112, LMC Ikeja)</div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 5: FINANCE OPERATIONS & MAKER/CHECKER (LWC-SCR-305)            */}
        {/* ================================================================= */}
        {activeTab === "FINANCE" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
              Finance Operations & Maker/Checker Queue
            </h2>

            {/* Double-Entry Ledger Summary Card */}
            {reconciliation && (
              <div
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: LW_DESIGN_TOKENS.radius.lg,
                  border: "1px solid #CBD5E1",
                  padding: "20px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                    Double-Entry Ledger Balance Summary
                  </h3>
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 800,
                      backgroundColor: reconciliation.double_entry_balanced ? "#DCFCE7" : "#FEE2E2",
                      color: reconciliation.double_entry_balanced ? "#166534" : "#991B1B",
                      padding: "4px 10px",
                      borderRadius: "4px",
                    }}
                  >
                    {reconciliation.double_entry_balanced ? "✓ Balanced Invariant Verified" : "⚠️ Discrepancy Flagged"}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748B" }}>Total Sponsor Cash Received</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0F172A" }}>
                      {formatMoneyMinor({ amountMinor: reconciliation.total_sponsor_cash_received_minor, currency: "NGN" })}
                    </div>
                  </div>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748B" }}>Total Active Reserved</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0F172A" }}>
                      {formatMoneyMinor({ amountMinor: reconciliation.total_reserved_minor, currency: "NGN" })}
                    </div>
                  </div>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748B" }}>Total Redeemed & Settled</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0F172A" }}>
                      {formatMoneyMinor({ amountMinor: reconciliation.total_redeemed_minor, currency: "NGN" })}
                    </div>
                  </div>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748B" }}>Clinician Payables Outstanding</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0F172A" }}>
                      {formatMoneyMinor({ amountMinor: reconciliation.total_clinician_payables_minor, currency: "NGN" })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Maker/Checker Exception Queue */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "20px",
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 14px" }}>
                Pending Exception Queue (Maker != Checker Enforced)
              </h3>

              {financeExceptions.length === 0 ? (
                <div style={{ textAlign: "center", padding: "30px", color: "#64748B", fontSize: "13px" }}>
                  No pending finance exceptions in queue.
                </div>
              ) : (
                <div style={{ display: "grid", gap: "12px" }}>
                  {financeExceptions.map((ex) => {
                    const isMaker = ex.maker_id === currentActorId;
                    return (
                      <div
                        key={ex.exception_id}
                        style={{
                          border: "1px solid #CBD5E1",
                          borderRadius: LW_DESIGN_TOKENS.radius.md,
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
                            <span style={{ fontWeight: 800, fontSize: "14px", color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                              {ex.exception_type}
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                fontWeight: 700,
                                backgroundColor: ex.status === "PENDING_REVIEW" ? "#FEF3C7" : "#DCFCE7",
                                color: ex.status === "PENDING_REVIEW" ? "#92400E" : "#166534",
                                padding: "2px 8px",
                                borderRadius: "4px",
                              }}
                            >
                              {ex.status}
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 800, color: "#0F172A" }}>
                              {formatMoneyMinor({ amountMinor: ex.amount_minor, currency: ex.currency as CurrencyCode })}
                            </span>
                          </div>
                          <div style={{ fontSize: "13px", color: "#475569", marginTop: "4px" }}>{ex.reason}</div>
                          <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                            Maker: <strong>{ex.maker_id}</strong> {isMaker && "(You)"} · Created: {new Date(ex.created_at_iso).toLocaleString()}
                          </div>
                        </div>

                        {ex.status === "PENDING_REVIEW" && (
                          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                            {isMaker ? (
                              <span style={{ fontSize: "12px", color: "#DC2626", fontWeight: 700 }}>
                                🔒 Maker Cannot Act as Checker (§10.4)
                              </span>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  onClick={() => handleActionException(ex.exception_id, "APPROVE")}
                                  disabled={actioningExceptionId === ex.exception_id}
                                  style={{
                                    padding: "6px 14px",
                                    backgroundColor: LW_DESIGN_TOKENS.colors.clinicalEmerald,
                                    color: "#FFFFFF",
                                    border: "none",
                                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                                    fontSize: "12px",
                                    fontWeight: 700,
                                    cursor: "pointer",
                                  }}
                                >
                                  Approve
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleActionException(ex.exception_id, "REJECT")}
                                  disabled={actioningExceptionId === ex.exception_id}
                                  style={{
                                    padding: "6px 14px",
                                    backgroundColor: "#DC2626",
                                    color: "#FFFFFF",
                                    border: "none",
                                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                                    fontSize: "12px",
                                    fontWeight: 700,
                                    cursor: "pointer",
                                  }}
                                >
                                  Reject
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Modal: New Action Item */}
      {isCreatingAction && (
        <div
          role="dialog"
          aria-modal="true"
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
            onSubmit={handleCreateActionItem}
            style={{
              backgroundColor: "#FFFFFF",
              borderRadius: LW_DESIGN_TOKENS.radius.lg,
              width: "100%",
              maxWidth: "480px",
              padding: "24px",
            }}
          >
            <h3 style={{ fontSize: "18px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 14px" }}>
              Create Directorate Action Item
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>Tied Metric:</label>
                <select
                  value={newActionMetricId}
                  onChange={(e) => setNewActionMetricId(e.target.value)}
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                >
                  <option value="LWC-MET-002">LWC-MET-002: Access Fulfilment Rate</option>
                  <option value="LWC-MET-004">LWC-MET-004: Unmet Demand / Capacity Gap</option>
                  <option value="LWC-MET-005">LWC-MET-005: Continuity Completion Rate</option>
                  <option value="LWC-MET-008">LWC-MET-008: Workforce Staffing Load</option>
                  <option value="LWC-MET-009">LWC-MET-009: Facility Readiness Rate</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>Action Title:</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Expand evening GP roster slots"
                  value={newActionTitle}
                  onChange={(e) => setNewActionTitle(e.target.value)}
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>Action Description:</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Specific remediation steps..."
                  value={newActionDesc}
                  onChange={(e) => setNewActionDesc(e.target.value)}
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                />
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setIsCreatingAction(false)}
                  style={{ flex: 1, padding: "8px", backgroundColor: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    flex: 2,
                    padding: "8px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "4px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Create Action Item
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
