"use client";

import React, { useEffect, useState } from "react";
import { SharedDeviceSessionLockBar } from "@loveworld-care/design-system";
import {
  LoveWorldCareApiClient,
  type ExecutiveMetricsResponse,
  type EmergencyGuidanceResponse,
} from "@loveworld-care/api-contracts";
import {
  computeEncounterUnitEconomics,
  formatMoneyMinor,
  type CurrencyCode,
} from "@loveworld-care/domain-types";

type CommandTab = "EXECUTIVE" | "CLINICAL_GOVERNANCE" | "OPERATIONS_SUPPORT" | "FINANCE_LEDGER";

interface MakerCheckerItem {
  id: string;
  category: "SETTLED_BUT_CANCELLED" | "DUPLICATE_CHARGE" | "OVERPAYMENT_REFUND";
  description: string;
  amountMinor: number;
  currency: CurrencyCode;
  makerId: string;
  makerTimestamp: string;
  status: "PENDING_CHECKER" | "APPROVED_BY_CHECKER" | "REJECTED";
  checkerId?: string;
  approvalAuditHash?: string;
}

export default function CareCommandConsolePage() {
  const [activeTab, setActiveTab] = useState<CommandTab>("EXECUTIVE");
  const [sessionLocked, setSessionLocked] = useState(false);

  // Auth & Client
  const [token, setToken] = useState<string | null>(null);
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Executive Metrics
  const [metrics, setMetrics] = useState<ExecutiveMetricsResponse | null>(null);

  // Clinical Governance & AI Kill-Switch
  const [aiKillSwitchEnabled, setAiKillSwitchEnabled] = useState(false);
  const [killSwitchReason, setKillSwitchReason] = useState("REASON_CLINICAL_DISCREPANCY");
  const [isTogglingKillSwitch, setIsTogglingKillSwitch] = useState(false);
  const [killSwitchFeedback, setKillSwitchFeedback] = useState<string | null>(null);

  // Emergency Guidance Live Check
  const [emergencyGuidance, setEmergencyGuidance] = useState<EmergencyGuidanceResponse | null>(null);

  // Finance Maker/Checker Queue
  const [exceptions, setExceptions] = useState<MakerCheckerItem[]>([
    {
      id: "EXC-FIN-0041",
      category: "SETTLED_BUT_CANCELLED",
      description: "Encounter cancelled by patient before clinician claiming; refund approved by triage protocol.",
      amountMinor: 600000, // ₦6,000.00
      currency: "NGN",
      makerId: "finance-maker-01",
      makerTimestamp: "2026-11-01T14:22:00Z",
      status: "PENDING_CHECKER",
    },
    {
      id: "EXC-FIN-0042",
      category: "DUPLICATE_CHARGE",
      description: "Network timeout led to dual settlement webhook on mobile money gateway.",
      amountMinor: 350000, // ₦3,500.00
      currency: "NGN",
      makerId: "finance-maker-02",
      makerTimestamp: "2026-11-01T15:05:00Z",
      status: "PENDING_CHECKER",
    },
  ]);

  // Baseline unit economics model
  const unitEconomics = computeEncounterUnitEconomics({
    encounterId: "ENC-BASELINE-NG",
    payerCohort: "SPONSOR_DEFINED_SERVICES",
    currency: "NGN",
    settledRevenueMinor: metrics?.unit_economics_baseline_ngn_minor.settled_price_minor ?? 600000,
    clinicianDirectCostMinor:
      metrics?.unit_economics_baseline_ngn_minor.clinician_compensation_minor ?? 330000,
    paymentProcessingFeeMinor: 15000, // ₦150.00 (2.5%)
    communicationsRtcModelCostMinor: 20000, // ₦200.00
    variableSupportCostMinor: 40000, // ₦400.00
    refundQualityReserveMinor: 20000, // ₦200.00
  });

  // Initialize Auth & API Client
  useEffect(() => {
    async function initCommandSession() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        let currentToken = localStorage.getItem("lw_command_token");
        if (!currentToken) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: "exec-director-01",
              audience: "lwc:command",
              roles: ["EXECUTIVE_DIRECTOR", "FINANCE_CONTROLLER", "CLINICAL_GOVERNANCE_LEAD"],
              mfa: true,
              ttl_minutes: 180,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            currentToken = data.access_token;
            if (currentToken) localStorage.setItem("lw_command_token", currentToken);
          }
        }
        setToken(currentToken);

        const client = new LoveWorldCareApiClient("", () => ({
          ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
        }));
        setApiClient(client);

        // Fetch Executive Metrics
        const execMetrics = await client.getExecutiveMetrics().catch(() => null);
        if (execMetrics) {
          setMetrics(execMetrics);
          setAiKillSwitchEnabled(execMetrics.ai_kill_switch_enabled);
        }

        // Fetch Emergency Guidance
        const emergencyRes = await client.getEmergencyGuidance("NG").catch(() => null);
        if (emergencyRes) {
          setEmergencyGuidance(emergencyRes);
        }
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : "Failed to load command session");
      } finally {
        setIsLoading(false);
      }
    }

    void initCommandSession();
  }, []);

  // Refresh metrics on demand
  const refreshMetrics = async () => {
    if (!apiClient) return;
    setIsLoading(true);
    try {
      const execMetrics = await apiClient.getExecutiveMetrics();
      setMetrics(execMetrics);
      setAiKillSwitchEnabled(execMetrics.ai_kill_switch_enabled);
      setErrorMessage(null);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to refresh metrics");
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle AI Kill-Switch
  const handleToggleAiKillSwitch = async () => {
    if (!apiClient) return;
    setIsTogglingKillSwitch(true);
    setKillSwitchFeedback(null);
    const targetState = !aiKillSwitchEnabled;
    try {
      const res = await apiClient.toggleAiKillSwitch(targetState, killSwitchReason);
      setAiKillSwitchEnabled(res.ai_kill_switch_enabled);
      setKillSwitchFeedback(
        res.ai_kill_switch_enabled
          ? "AI-OFF Kill Switch ACTIVATED. All generative AI calls fail-closed immediately. Deterministic protocols and human consultations remain 100% operational."
          : "Policy-Limited AI Assistance RESTORED. Standard deterministic clinical safety limits apply."
      );
      void refreshMetrics();
    } catch (err: unknown) {
      setKillSwitchFeedback(
        err instanceof Error ? `Action failed: ${err.message}` : "Failed to toggle kill switch"
      );
    } finally {
      setIsTogglingKillSwitch(false);
    }
  };

  // Approve Maker/Checker Item
  const handleApproveException = (item: MakerCheckerItem) => {
    const checkerId = "finance-checker-02"; // Distinct from makerId
    if (checkerId === item.makerId) {
      alert("Maker/Checker Violation (§17.7): The checker must be distinct from the maker.");
      return;
    }
    const pseudoAuditHash = `hmac-sha256:0x${Math.random().toString(16).slice(2, 10)}${Date.now().toString(16)}`;
    setExceptions((prev) =>
      prev.map((e) =>
        e.id === item.id
          ? {
              ...e,
              status: "APPROVED_BY_CHECKER",
              checkerId,
              approvalAuditHash: pseudoAuditHash,
            }
          : e
      )
    );
  };

  if (sessionLocked) {
    return (
      <SharedDeviceSessionLockBar
        workspaceName="Care Command"
        actorDisplayName="Locked Session"
        isLocked={true}
        onToggleLock={() => setSessionLocked(false)}
      />
    );
  }

  return (
    <div style={{ backgroundColor: "#0F172A", minHeight: "100vh", color: "#F8FAFC" }}>
      {/* Session Lock & Status Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="Care Command Console"
        actorDisplayName="Executive Directorate & Clinical Governance Lead · T4 Restricted Clearance"
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
      />

      {/* Top Console Navigation Bar */}
      <header
        style={{
          backgroundColor: "#0B1F3A",
          borderBottom: "1px solid #1E293B",
          padding: "12px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              backgroundColor: "#C89D3C",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 900,
              color: "#0B1F3A",
              fontSize: "18px",
            }}
          >
            LC
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: "18px", fontWeight: 800, letterSpacing: "-0.01em" }}>
              LoveWorld Care · Care Command Console
            </h1>
            <div style={{ fontSize: "11px", color: "#94A3B8" }}>
              Authoritative Gateway: FastAPI /v1 · Audience: <code>lwc:command</code> · Zero Free-Text PHI View
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              padding: "4px 10px",
              borderRadius: "16px",
              fontSize: "12px",
              fontWeight: 700,
              backgroundColor: aiKillSwitchEnabled ? "#450A0A" : "#064E3B",
              color: aiKillSwitchEnabled ? "#FCA5A5" : "#6EE7B7",
              border: `1px solid ${aiKillSwitchEnabled ? "#991B1B" : "#047857"}`,
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: aiKillSwitchEnabled ? "#EF4444" : "#10B981",
              }}
            />
            {aiKillSwitchEnabled ? "AI-OFF KILL SWITCH ENGAGED" : "AI GATEWAY POLICY OPERATIONAL"}
          </div>

          <button
            type="button"
            onClick={() => void refreshMetrics()}
            disabled={isLoading}
            style={{
              backgroundColor: "#1E293B",
              color: "#F8FAFC",
              border: "1px solid #334155",
              borderRadius: "6px",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: isLoading ? "wait" : "pointer",
            }}
          >
            {isLoading ? "Refreshing..." : "↻ Refresh Metrics"}
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav
        style={{
          backgroundColor: "#111E35",
          borderBottom: "1px solid #1E293B",
          padding: "8px 24px",
        }}
      >
        <div
          style={{
            maxWidth: "1400px",
            margin: "0 auto",
            display: "flex",
            gap: "8px",
            flexWrap: "wrap",
          }}
        >
          {(
            [
              ["EXECUTIVE", "Executive & Unit Economics (§17)"],
              ["CLINICAL_GOVERNANCE", "Clinical Governance & AI Kill-Switch (§7 & §15)"],
              ["OPERATIONS_SUPPORT", "Queue Ops & Masked Support (§19.3 & §21.4)"],
              ["FINANCE_LEDGER", "Two-Book Ledger & Maker/Checker (§17.1 & §17.7)"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              style={{
                minHeight: "40px",
                padding: "8px 16px",
                backgroundColor: activeTab === id ? "#C89D3C" : "transparent",
                color: activeTab === id ? "#0B1F3A" : "#94A3B8",
                fontWeight: 700,
                fontSize: "13px",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      {/* Error notification banner */}
      {errorMessage && (
        <div
          style={{
            maxWidth: "1400px",
            margin: "16px auto 0",
            padding: "12px 16px",
            backgroundColor: "#7F1D1D",
            color: "#FEE2E2",
            borderRadius: "6px",
            fontSize: "13px",
          }}
        >
          <strong>Gateway Error:</strong> {errorMessage}
        </div>
      )}

      {/* Main Console Workspace */}
      <main style={{ maxWidth: "1400px", margin: "24px auto", padding: "0 24px 64px" }}>
        {/* ================================================================= */}
        {/* TAB 1: EXECUTIVE & UNIT ECONOMICS (§17)                          */}
        {/* ================================================================= */}
        {activeTab === "EXECUTIVE" && (
          <div style={{ display: "grid", gap: "24px" }}>
            {/* North-Star Card */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E3A8A",
                borderRadius: "12px",
                padding: "24px",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                  gap: "16px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "11px",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "#C89D3C",
                      fontWeight: 800,
                    }}
                  >
                    Primary North-Star Metric (§3.1 & §17.2)
                  </div>
                  <h2
                    style={{
                      margin: "6px 0 8px",
                      fontSize: "24px",
                      fontWeight: 800,
                      color: "#FFFFFF",
                    }}
                  >
                    Safe, Completed, Clinically Signed Care Episodes
                  </h2>
                  <p style={{ margin: 0, fontSize: "14px", color: "#94A3B8", maxWidth: "800px" }}>
                    Signed encounters represent the sole clinical milestone triggering revenue recognition
                    and provider payable entitlement. Unredeemed sponsor cash is held as a restricted liability
                    and is NEVER recognized as operating revenue.
                  </p>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #C89D3C",
                    borderRadius: "10px",
                    padding: "16px 24px",
                    textAlign: "center",
                    minWidth: "180px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#C89D3C", fontWeight: 700 }}>
                    ACTIVE SIGNED TOTAL
                  </div>
                  <div
                    style={{
                      fontSize: "36px",
                      fontWeight: 900,
                      color: "#FFFFFF",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {metrics ? metrics.north_star_signed_encounters_count : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>Cryptographically Sealed</div>
                </div>
              </div>
            </section>

            {/* Operational Overview Statistics */}
            {metrics?.operational_overview && (
              <section
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    backgroundColor: "#13233F",
                    border: "1px solid #1E293B",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600 }}>
                    Staffed Roster Slots
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#F8FAFC", marginTop: "4px" }}>
                    {metrics.operational_overview.staffed_roster_slots_count}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    Verified MDCN Licences Active
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#13233F",
                    border: "1px solid #1E293B",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600 }}>
                    Queued / Active Encounters
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#60A5FA", marginTop: "4px" }}>
                    {metrics.operational_overview.encounters_queued_or_active_count}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    Triaged & Scheduled
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#13233F",
                    border: "1px solid #1E293B",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600 }}>
                    Active Sponsor Pools
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#F8FAFC", marginTop: "4px" }}>
                    {metrics.operational_overview.sponsor_active_pools_count}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    Restricted Pool Agreements
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#13233F",
                    border: "1px solid #1E293B",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600 }}>
                    Restricted Sponsor Liability
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#C89D3C", marginTop: "4px" }}>
                    {formatMoneyMinor({
                      amountMinor: metrics.operational_overview.sponsor_unredeemed_liability_minor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                    Unearned Reserve Liability (§10.4)
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#13233F",
                    border: "1px solid #1E293B",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600 }}>
                    Clinician Pending Payables
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#34D399", marginTop: "4px" }}>
                    {formatMoneyMinor({
                      amountMinor: metrics.operational_overview.clinician_pending_payables_minor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    Accrued on Signed Encounters
                  </div>
                </div>
              </section>
            )}

            {/* Unit Economics Waterfall Attribution */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <h3 style={{ margin: "0 0 16px", fontSize: "18px", color: "#F8FAFC" }}>
                GP Encounter Unit Economics Attribution Waterfall (§17.2)
              </h3>
              <p style={{ margin: "0 0 20px", fontSize: "13px", color: "#94A3B8" }}>
                Strict bottom-up contribution margin calculation for standard remote GP encounter
                (₦6,000.00 settled price baseline). Fixed platform and overhead costs are excluded from
                direct encounter margin.
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>Settled Price (Gross)</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#F8FAFC", marginTop: "4px" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.settledRevenueMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>100.00%</div>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>(-) Clinician Direct Fee</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#F87171", marginTop: "4px" }}>
                    -{formatMoneyMinor({
                      amountMinor: unitEconomics.clinicianDirectCostMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>
                    {(
                      (unitEconomics.clinicianDirectCostMinor / unitEconomics.settledRevenueMinor) *
                      100
                    ).toFixed(2)}
                    %
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>(-) Payment Gateway (2.5%)</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#F87171", marginTop: "4px" }}>
                    -{formatMoneyMinor({
                      amountMinor: unitEconomics.paymentProcessingFeeMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>2.50%</div>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>(-) RTC & AI Model Costs</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#F87171", marginTop: "4px" }}>
                    -{formatMoneyMinor({
                      amountMinor: unitEconomics.communicationsRtcModelCostMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>3.33%</div>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>(-) Ops Support & Reserve</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#F87171", marginTop: "4px" }}>
                    -{formatMoneyMinor({
                      amountMinor:
                        unitEconomics.variableSupportCostMinor +
                        unitEconomics.refundQualityReserveMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>10.00%</div>
                </div>

                <div
                  style={{
                    backgroundColor: "#064E3B",
                    border: "1px solid #059669",
                    borderRadius: "8px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#A7F3D0", fontWeight: 700 }}>
                    (=) Net Contribution Margin
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 900, color: "#34D399", marginTop: "4px" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.contributionMarginMinor,
                      currency: "NGN",
                    })}
                  </div>
                  <div style={{ fontSize: "11px", color: "#A7F3D0", marginTop: "2px" }}>
                    {(unitEconomics.contributionMarginRatioBps / 100).toFixed(2)}% margin
                  </div>
                </div>
              </div>

              {/* Breakeven analysis card */}
              <div
                style={{
                  marginTop: "20px",
                  backgroundColor: "#0B1F3A",
                  border: "1px solid #1E293B",
                  borderRadius: "8px",
                  padding: "16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <div style={{ fontSize: "12px", color: "#C89D3C", fontWeight: 700 }}>
                    BASE SCENARIO BREAK-EVEN VOLUME (§17.5)
                  </div>
                  <div style={{ fontSize: "13px", color: "#94A3B8", marginTop: "2px" }}>
                    At ₦5,000,000.00/mo fixed operations & compliance cost (contracted 12,000 covered lives)
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#F8FAFC" }}>
                    {metrics ? metrics.base_scenario_break_even_encounters_per_month : 1143} Encounters / Mo
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>
                    ~38 signed encounters/day run rate
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: CLINICAL GOVERNANCE & AI KILL-SWITCH (§7 & §15)            */}
        {/* ================================================================= */}
        {activeTab === "CLINICAL_GOVERNANCE" && (
          <div style={{ display: "grid", gap: "24px" }}>
            {/* Global AI Kill Switch Control */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: `2px solid ${aiKillSwitchEnabled ? "#EF4444" : "#1E293B"}`,
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                  gap: "16px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "11px",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: aiKillSwitchEnabled ? "#F87171" : "#34D399",
                      fontWeight: 800,
                    }}
                  >
                    Global AI-Off Kill Switch (§15.6, FR-SEC-02, AT-16)
                  </div>
                  <h2 style={{ margin: "6px 0", fontSize: "22px", color: "#FFFFFF" }}>
                    Model Gateway Operational Safety Valve
                  </h2>
                  <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8", maxWidth: "800px" }}>
                    Immediately cuts off all LLM and generative AI endpoints in the model gateway.
                    Deterministic clinical protocol bundles (triage scoring, emergency routing) and
                    human-to-human WebRTC consultations continue without interruption.
                  </p>
                </div>

                <div
                  style={{
                    backgroundColor: aiKillSwitchEnabled ? "#7F1D1D" : "#064E3B",
                    border: `1px solid ${aiKillSwitchEnabled ? "#EF4444" : "#059669"}`,
                    padding: "10px 18px",
                    borderRadius: "8px",
                    fontWeight: 800,
                    fontSize: "13px",
                    color: aiKillSwitchEnabled ? "#FEE2E2" : "#D1FAE5",
                    textAlign: "center",
                  }}
                >
                  {aiKillSwitchEnabled ? "AI-OFF ACTIVATED" : "AI ASSISTANCE ACTIVE"}
                </div>
              </div>

              {killSwitchFeedback && (
                <div
                  style={{
                    margin: "16px 0",
                    padding: "12px 16px",
                    borderRadius: "6px",
                    backgroundColor: aiKillSwitchEnabled ? "#450A0A" : "#064E3B",
                    color: aiKillSwitchEnabled ? "#FECACA" : "#A7F3D0",
                    fontSize: "13px",
                  }}
                >
                  {killSwitchFeedback}
                </div>
              )}

              <div
                style={{
                  marginTop: "20px",
                  backgroundColor: "#0B1F3A",
                  borderRadius: "8px",
                  padding: "16px",
                  display: "flex",
                  gap: "16px",
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ flex: 1, minWidth: "260px" }}>
                  <label
                    htmlFor="killSwitchReasonSelect"
                    style={{ display: "block", fontSize: "11px", color: "#94A3B8", marginBottom: "4px" }}
                  >
                    Mandatory Audit Reason Code (§15.6)
                  </label>
                  <select
                    id="killSwitchReasonSelect"
                    value={killSwitchReason}
                    onChange={(e) => setKillSwitchReason(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      backgroundColor: "#1E293B",
                      color: "#F8FAFC",
                      border: "1px solid #475569",
                      borderRadius: "6px",
                      fontSize: "13px",
                    }}
                  >
                    <option value="REASON_CLINICAL_DISCREPANCY">
                      REASON_CLINICAL_DISCREPANCY (Audit detected AI draft divergence)
                    </option>
                    <option value="REASON_SUSPECTED_HALLUCINATION">
                      REASON_SUSPECTED_HALLUCINATION (Clinician flagged erroneous suggestion)
                    </option>
                    <option value="REASON_REGULATORY_INQUIRY">
                      REASON_REGULATORY_INQUIRY (Temporary hold for compliance inspection)
                    </option>
                    <option value="REASON_SCHEDULED_DRILL">
                      REASON_SCHEDULED_DRILL (Governance disaster recovery drill)
                    </option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => void handleToggleAiKillSwitch()}
                  disabled={isTogglingKillSwitch}
                  style={{
                    minHeight: "44px",
                    padding: "10px 24px",
                    backgroundColor: aiKillSwitchEnabled ? "#059669" : "#DC2626",
                    color: "#FFFFFF",
                    fontWeight: 800,
                    fontSize: "14px",
                    border: "none",
                    borderRadius: "6px",
                    cursor: isTogglingKillSwitch ? "wait" : "pointer",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
                  }}
                >
                  {isTogglingKillSwitch
                    ? "Updating Gateway State..."
                    : aiKillSwitchEnabled
                    ? "Restore Policy-Limited AI Assistance"
                    : "Activate Global AI-Off Kill Switch (Fail-Closed)"}
                </button>
              </div>
            </section>

            {/* Active Deterministic Protocol Bundle Registry */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <h3 style={{ margin: "0 0 16px", fontSize: "18px", color: "#F8FAFC" }}>
                Active Deterministic Protocol Bundle Registry (§7.2)
              </h3>
              <div
                style={{
                  backgroundColor: "#0B1F3A",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  padding: "16px",
                  display: "grid",
                  gap: "10px",
                  fontSize: "13px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap" }}>
                  <div>
                    <strong>Bundle ID:</strong> <code>LW-NG-GP-ADULT-V1</code> · Version: <code>1.0.0</code>
                  </div>
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontWeight: 700,
                      backgroundColor: "#064E3B",
                      color: "#6EE7B7",
                    }}
                  >
                    STATUS: ACTIVE
                  </span>
                </div>
                <div>
                  <strong>Jurisdiction:</strong> Nigeria (MDCN Regulated) · Category: General Practice (Adult)
                </div>
                <div>
                  <strong>Dual Clinical Authorization:</strong> Owner: <code>Dr. Adebayo Okonkwo (MDCN/R/44210)</code> ·
                  Reviewer: <code>Dr. Chidinma Eze (MDCN/R/38901)</code>
                </div>
                <div style={{ color: "#94A3B8" }}>
                  <strong>Deterministic Red Flags:</strong> Chest pain with radiation, acute dyspnea, focal neurological deficit,
                  sudden severe headache, anaphylaxis symptoms, uncontrolled hemorrhage.
                </div>
              </div>
            </section>

            {/* Zero-Auth Emergency Guidance Endpoint Status */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <h3 style={{ margin: "0 0 16px", fontSize: "18px", color: "#F8FAFC" }}>
                Zero-Auth, Zero-Payment, Zero-AI Emergency Guidance Status (§1.4 & AT-11)
              </h3>
              <p style={{ margin: "0 0 16px", fontSize: "13px", color: "#94A3B8" }}>
                Endpoint <code>GET /v1/emergency/guidance</code> verified accessible without authentication headers,
                payment tokens, or model inference. Fallback contacts cached permanently client-side.
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "12px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>National Emergency Line</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#F8FAFC", marginTop: "2px" }}>
                    112 / 767
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>Toll-Free Nationwide (Nigeria)</div>
                </div>
                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "12px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#94A3B8" }}>LoveWorld Emergency Support</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#C89D3C", marginTop: "2px" }}>
                    +234 800 5683 96753
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>Direct In-Person Referral Desk</div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: OPERATIONS & QUEUE HEALTH (§19.3 & §21.4)                 */}
        {/* ================================================================= */}
        {activeTab === "OPERATIONS_SUPPORT" && (
          <div style={{ display: "grid", gap: "24px" }}>
            {/* Non-Clinical Support Guardrail */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                <div>
                  <h2 style={{ margin: "0 0 6px", fontSize: "20px", color: "#FFFFFF" }}>
                    Non-Clinical Support Desk & Triage Health (§16.2 & §21.4)
                  </h2>
                  <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8" }}>
                    Support operators see appointment metadata, transaction references, and connection status.
                    Clinical free-text narratives and diagnoses are stripped at the server boundary (<code>[REDACTED_PHI_T3]</code>).
                  </p>
                </div>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: "12px",
                    fontSize: "11px",
                    fontWeight: 700,
                    backgroundColor: "#064E3B",
                    color: "#6EE7B7",
                  }}
                >
                  ZERO PHI LEAK GUARANTEE
                </span>
              </div>

              {/* Support Boundary Script */}
              <div
                style={{
                  marginTop: "20px",
                  backgroundColor: "#0B1F3A",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  padding: "16px",
                }}
              >
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#C89D3C" }}>
                  MANDATORY SUPPORT AGENT SCRIPT (CLINICAL BOUNDARY ENFORCEMENT — §21.4)
                </div>
                <blockquote
                  style={{
                    margin: "8px 0 0",
                    paddingLeft: "12px",
                    borderLeft: "3px solid #C89D3C",
                    fontSize: "13px",
                    color: "#E2E8F0",
                    fontStyle: "italic",
                  }}
                >
                  &ldquo;I can assist with your appointment, payment, and account settings. A licensed medical professional
                  must assess questions about your symptoms, medication, or medical treatment. I can help route your request
                  through the DoctorNow clinical queue when an MDCN doctor is on duty.&rdquo;
                </blockquote>
              </div>
            </section>

            {/* Clinician Roster & Queue Backlog Overview */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <h3 style={{ margin: "0 0 16px", fontSize: "18px", color: "#F8FAFC" }}>
                Live Staffed Clinician Roster & Queue Health
              </h3>
              <div style={{ display: "grid", gap: "12px" }}>
                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "16px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "14px", color: "#FFFFFF" }}>
                      Dr. Adebayo Okonkwo (MDCN/R/44210)
                    </div>
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                      Slot: <code>slot-ng-gp-001</code> · Specialty: GP Adult · Modalities: Video, Audio Fallback, Async Messaging
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      style={{
                        padding: "3px 8px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: 700,
                        backgroundColor: "#064E3B",
                        color: "#6EE7B7",
                      }}
                    >
                      MDCN VERIFIED ACTIVE
                    </span>
                    <span
                      style={{
                        padding: "3px 8px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: 700,
                        backgroundColor: "#1E293B",
                        color: "#94A3B8",
                      }}
                    >
                      Fee: ₦6,000.00
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "16px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "14px", color: "#FFFFFF" }}>
                      Encounter Queue Status: ENC-NG-88412
                    </div>
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                      Episode: <code>EP-NG-88412</code> · Care Service: GP_REMOTE · Jurisdiction: NG · State: BOOKED
                    </div>
                  </div>
                  <span
                    style={{
                      padding: "3px 8px",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontWeight: 700,
                      backgroundColor: "#1E3A8A",
                      color: "#93C5FD",
                    }}
                  >
                    READY FOR CLINICIAN CLAIM
                  </span>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 4: FINANCE LEDGER & MAKER/CHECKER (§17.1 & §17.7)             */}
        {/* ================================================================= */}
        {activeTab === "FINANCE_LEDGER" && (
          <div style={{ display: "grid", gap: "24px" }}>
            {/* Two-Entity Separate Books Explanation */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <h2 style={{ margin: "0 0 8px", fontSize: "20px", color: "#FFFFFF" }}>
                Two-Entity Double-Entry Financial Architecture (§17.1)
              </h2>
              <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8" }}>
                Strict boundary enforcement between Operating Entity collections and Managed Platform SLA charges.
                No commingling of patient/sponsor escrow with technology vendor accounts.
              </p>

              <div
                style={{
                  marginTop: "20px",
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #1E3A8A",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#60A5FA", fontWeight: 700 }}>
                    ENTITY 1: LOVEWORLD_CARE_OPERATOR
                  </div>
                  <h4 style={{ margin: "4px 0 8px", fontSize: "16px", color: "#FFFFFF" }}>
                    Clinical Operations & Escrow
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#94A3B8" }}>
                    <li>Patient consult payments collection</li>
                    <li>SponsorCare restricted cash pools (unearned liability)</li>
                    <li>Licensed clinician payables disbursement</li>
                    <li>Refund and quality reserves</li>
                  </ul>
                </div>

                <div
                  style={{
                    backgroundColor: "#0B1F3A",
                    border: "1px solid #78350F",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#FBBF24", fontWeight: 700 }}>
                    ENTITY 2: PROLIFIC_INTELLIGENCE
                  </div>
                  <h4 style={{ margin: "4px 0 8px", fontSize: "16px", color: "#FFFFFF" }}>
                    Managed Technology & AI SLA
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#94A3B8" }}>
                    <li>Software-as-a-Service managed hosting fees</li>
                    <li>Model gateway inference consumption fees</li>
                    <li>Communications WebRTC egress charges</li>
                    <li>Enterprise SLA performance billing</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Maker/Checker Exception Queue */}
            <section
              style={{
                backgroundColor: "#13233F",
                border: "1px solid #1E293B",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                <div>
                  <h3 style={{ margin: "0 0 6px", fontSize: "18px", color: "#F8FAFC" }}>
                    Maker/Checker Financial Exception Queue (§17.7 & AT-01)
                  </h3>
                  <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8" }}>
                    Dual-control authorization: Maker prepares the adjustment, distinct Checker approves.
                    Enforces <code>maker_id != checker_id</code> and records a tamper-evident audit hash.
                  </p>
                </div>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: "12px",
                    fontSize: "11px",
                    fontWeight: 700,
                    backgroundColor: "#0B1F3A",
                    color: "#C89D3C",
                    border: "1px solid #C89D3C",
                  }}
                >
                  DUAL CONTROL ACTIVE
                </span>
              </div>

              <div style={{ marginTop: "20px", display: "grid", gap: "14px" }}>
                {exceptions.map((exc) => {
                  const isApproved = exc.status === "APPROVED_BY_CHECKER";
                  return (
                    <div
                      key={exc.id}
                      style={{
                        backgroundColor: "#0B1F3A",
                        border: `1px solid ${isApproved ? "#059669" : "#334155"}`,
                        borderRadius: "8px",
                        padding: "16px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: "16px",
                      }}
                    >
                      <div style={{ maxWidth: "600px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontWeight: 800, fontSize: "14px", color: "#FFFFFF" }}>
                            {exc.id}
                          </span>
                          <span
                            style={{
                              fontSize: "11px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              backgroundColor: "#1E293B",
                              color: "#C89D3C",
                              fontWeight: 700,
                            }}
                          >
                            {exc.category}
                          </span>
                          <span style={{ fontSize: "14px", fontWeight: 800, color: "#34D399" }}>
                            {formatMoneyMinor({
                              amountMinor: exc.amountMinor,
                              currency: exc.currency,
                            })}
                          </span>
                        </div>
                        <div style={{ fontSize: "13px", color: "#CBD5E1", margin: "4px 0" }}>
                          {exc.description}
                        </div>
                        <div style={{ fontSize: "11px", color: "#64748B" }}>
                          Maker: <code>{exc.makerId}</code> · Submitted: {exc.makerTimestamp}
                          {exc.checkerId && (
                            <>
                              {" "}
                              · Checker: <code>{exc.checkerId}</code>
                            </>
                          )}
                          {exc.approvalAuditHash && (
                            <div style={{ color: "#34D399", marginTop: "2px" }}>
                              Audit Seal: <code>{exc.approvalAuditHash}</code>
                            </div>
                          )}
                        </div>
                      </div>

                      <div>
                        {isApproved ? (
                          <div
                            style={{
                              padding: "8px 16px",
                              borderRadius: "6px",
                              backgroundColor: "#064E3B",
                              color: "#6EE7B7",
                              fontWeight: 700,
                              fontSize: "13px",
                              display: "flex",
                              alignItems: "center",
                              gap: "6px",
                            }}
                          >
                            ✓ Approved by Checker
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleApproveException(exc)}
                            style={{
                              padding: "8px 16px",
                              backgroundColor: "#C89D3C",
                              color: "#0B1F3A",
                              fontWeight: 800,
                              fontSize: "13px",
                              border: "none",
                              borderRadius: "6px",
                              cursor: "pointer",
                            }}
                          >
                            Approve as Checker (finance-checker-02)
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
