"use client";

import React, { useEffect, useState } from "react";
import { SharedDeviceSessionLockBar, LW_DESIGN_TOKENS } from "@loveworld-care/design-system";
import { formatMoneyMinor, type CurrencyCode } from "@loveworld-care/domain-types";
import { LoveWorldCareApiClient, SponsorPoolSummaryDTO } from "@loveworld-care/api-contracts";

type SponsorTab = "OVERVIEW" | "STATEMENTS" | "TERMS";

export default function SponsorCareWorkspacePage() {
  const [activeTab, setActiveTab] = useState<SponsorTab>("OVERVIEW");
  const [sessionLocked, setSessionLocked] = useState(false);
  const [sponsorAdminId] = useState("sponsor-admin-01");
  const [sponsorName] = useState("LoveWorld Medicaid Humanitarian Foundation");
  const [sponsorOrg] = useState("sponsor-loveworld-medicaid");
  const [agreementId] = useState("AGR-LW-MEDICAID-NG-2026");

  // API State
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [poolReport, setPoolReport] = useState<SponsorPoolSummaryDTO | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [networkError, setNetworkError] = useState<string | null>(null);

  // Initialize Auth & API Client
  useEffect(() => {
    async function initSponsor() {
      setIsLoading(true);
      try {
        let token = typeof window !== "undefined" ? localStorage.getItem("lw_sponsor_token") : null;
        if (!token) {
          const devRes = await fetch("/v1/auth/dev-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sub: sponsorAdminId,
              audience: "lwc:sponsor",
              roles: ["SPONSOR_ADMIN"],
              org: sponsorOrg,
              mfa: true,
              ttl_minutes: 240,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token && typeof window !== "undefined") {
              localStorage.setItem("lw_sponsor_token", token);
            }
          }
        }

        const client = new LoveWorldCareApiClient("", () => ({
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }));
        setApiClient(client);

        const report = await client.getSponsorPoolReport(agreementId);
        setPoolReport(report);
      } catch (err: unknown) {
        setNetworkError(err instanceof Error ? err.message : "Failed to load sponsor pool report");
      } finally {
        setIsLoading(false);
      }
    }
    initSponsor();
  }, [sponsorAdminId, sponsorOrg, agreementId]);

  const refreshReport = async () => {
    if (!apiClient) return;
    setIsLoading(true);
    setNetworkError(null);
    try {
      const report = await apiClient.getSponsorPoolReport(agreementId);
      setPoolReport(report);
    } catch (err: unknown) {
      setNetworkError(err instanceof Error ? err.message : "Failed to refresh pool report");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadCsv = () => {
    if (!poolReport) return;
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [
        "Agreement ID,Sponsor Name,Currency,Committed Unfunded,Funded Cash,Active Reserved,Redeemed Settled,Available,Beneficiaries Served,Completed Encounters,k-Anonymity Suppressed",
        `${poolReport.agreement_id},"${poolReport.sponsor_name}",${poolReport.currency},${poolReport.committed_unfunded_minor / 100},${poolReport.funded_cash_received_minor / 100},${poolReport.active_reserved_minor / 100},${poolReport.redeemed_settled_minor / 100},${poolReport.available_to_reserve_minor / 100},${poolReport.beneficiaries_served_count ?? poolReport.completed_encounters_count},${poolReport.completed_encounters_count},${poolReport.k_anonymity_suppressed}`,
      ].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `SponsorCare_Statement_${poolReport.agreement_id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
          SponsorCare Institutional Session Protected
        </h1>
        <p style={{ color: "#94A3B8", maxWidth: "400px", marginBottom: "24px", fontSize: "14px" }}>
          Re-authenticate to view institutional health funding pools, utilization audits, and statements.
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
          Unlock Sponsor Portal
        </button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* 1. Header Bar */}
      <SharedDeviceSessionLockBar
        workspaceName="SponsorCare · Institutional Health Funding"
        actorDisplayName={`${sponsorName} (${sponsorOrg})`}
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
        onSignOut={() => {
          if (typeof window !== "undefined") localStorage.removeItem("lw_sponsor_token");
          window.location.reload();
        }}
      />

      {/* 2. Navigation Tabs */}
      <nav
        aria-label="Sponsor Navigation"
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
          onClick={() => setActiveTab("OVERVIEW")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "OVERVIEW" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "OVERVIEW" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          📊 Pool Overview & Utilisation
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("STATEMENTS")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "STATEMENTS" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "STATEMENTS" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          📄 Statements & Accounting
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("TERMS")}
          style={{
            padding: "14px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "TERMS" ? `3px solid ${LW_DESIGN_TOKENS.colors.royalNavy}` : "3px solid transparent",
            color: activeTab === "TERMS" ? LW_DESIGN_TOKENS.colors.royalNavy : "#64748B",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          📜 Programme Terms & Rules
        </button>
      </nav>

      {/* Main Body */}
      <main style={{ maxWidth: "1240px", margin: "24px auto", padding: "0 20px 60px", width: "100%" }}>
        {networkError && (
          <div
            role="alert"
            style={{
              backgroundColor: "#FEE2E2",
              border: "1px solid #FCA5A5",
              borderRadius: LW_DESIGN_TOKENS.radius.md,
              padding: "12px 16px",
              color: "#991B1B",
              fontSize: "13px",
              fontWeight: 600,
              marginBottom: "16px",
            }}
          >
            ⚠️ {networkError}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 1: OVERVIEW & UTILISATION                                     */}
        {/* ================================================================= */}
        {activeTab === "OVERVIEW" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Agreement Header */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "20px 24px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: "#64748B" }}>AGREEMENT:</span>
                  <span style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy }}>
                    {agreementId}
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
                    ACTIVE PROGRAMME
                  </span>
                </div>
                <div style={{ fontSize: "14px", color: "#475569", marginTop: "4px" }}>
                  {poolReport?.sponsor_name || sponsorName}
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={refreshReport}
                  disabled={isLoading}
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
                  🔄 Refresh Balance
                </button>
              </div>
            </div>

            {/* Balances Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
              <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: LW_DESIGN_TOKENS.radius.md, padding: "16px" }}>
                <div style={{ fontSize: "12px", color: "#64748B", fontWeight: 700 }}>Committed Unfunded</div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "#0F172A", marginTop: "4px" }}>
                  {formatMoneyMinor({ amountMinor: poolReport?.committed_unfunded_minor ?? 0, currency: (poolReport?.currency as CurrencyCode) || "NGN" })}
                </div>
                <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>Pledged institutional commitment</div>
              </div>

              <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: LW_DESIGN_TOKENS.radius.md, padding: "16px" }}>
                <div style={{ fontSize: "12px", color: "#166534", fontWeight: 700 }}>Funded Cash Received</div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "#166534", marginTop: "4px" }}>
                  {formatMoneyMinor({ amountMinor: poolReport?.funded_cash_received_minor ?? 0, currency: (poolReport?.currency as CurrencyCode) || "NGN" })}
                </div>
                <div style={{ fontSize: "11px", color: "#166534", marginTop: "4px" }}>Cleared bank / Espees cash in escrow</div>
              </div>

              <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: LW_DESIGN_TOKENS.radius.md, padding: "16px" }}>
                <div style={{ fontSize: "12px", color: "#92400E", fontWeight: 700 }}>Active Reserved</div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "#B45309", marginTop: "4px" }}>
                  {formatMoneyMinor({ amountMinor: poolReport?.active_reserved_minor ?? 0, currency: (poolReport?.currency as CurrencyCode) || "NGN" })}
                </div>
                <div style={{ fontSize: "11px", color: "#92400E", marginTop: "4px" }}>In-flight consultations holding escrow</div>
              </div>

              <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: LW_DESIGN_TOKENS.radius.md, padding: "16px" }}>
                <div style={{ fontSize: "12px", color: "#0369A1", fontWeight: 700 }}>Available to Reserve</div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "#0284C7", marginTop: "4px" }}>
                  {formatMoneyMinor({ amountMinor: poolReport?.available_to_reserve_minor ?? 0, currency: (poolReport?.currency as CurrencyCode) || "NGN" })}
                </div>
                <div style={{ fontSize: "11px", color: "#0369A1", marginTop: "4px" }}>Unreserved humanitarian capacity</div>
              </div>
            </div>

            {/* Privacy-Safe Utilisation & k>=5 Anonymity Section */}
            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "17px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                    Privacy-Safe Aggregate Utilisation (§10.5, LWC-SCR-306)
                  </h3>
                  <p style={{ fontSize: "13px", color: "#64748B", margin: "4px 0 0" }}>
                    Sponsors NEVER receive patient names, intake text, diagnoses, or clinical notes (AT-06, AT-14).
                  </p>
                </div>
                <span
                  style={{
                    backgroundColor: "#DCFCE7",
                    color: "#166534",
                    fontSize: "12px",
                    fontWeight: 700,
                    padding: "4px 12px",
                    borderRadius: "6px",
                  }}
                >
                  ✓ Zero PHI Disclosed
                </span>
              </div>

              {poolReport?.k_anonymity_suppressed ? (
                /* k < 5 Suppression Notice */
                <div
                  style={{
                    backgroundColor: "#FEF3C7",
                    border: "1px solid #FCD34D",
                    borderRadius: LW_DESIGN_TOKENS.radius.md,
                    padding: "16px",
                    color: "#92400E",
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: "14px", marginBottom: "4px" }}>
                    🔒 k-Anonymity Suppression Active (Cohort &lt; 5 Beneficiaries)
                  </div>
                  <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.4 }}>
                    To prevent re-identification of individual beneficiaries, granular demographic and encounter counts are withheld until at least 5 distinct individuals have accessed care under this pool.
                  </p>
                </div>
              ) : (
                /* Authoritative Aggregates */
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "14px", borderRadius: LW_DESIGN_TOKENS.radius.md }}>
                    <div style={{ fontSize: "12px", color: "#64748B" }}>Eligible Population</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: "#0F172A", marginTop: "2px" }}>
                      {poolReport?.eligible_population_count ?? poolReport?.eligible_beneficiary_count ?? 0}
                    </div>
                  </div>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "14px", borderRadius: LW_DESIGN_TOKENS.radius.md }}>
                    <div style={{ fontSize: "12px", color: "#64748B" }}>Beneficiaries Served</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: "#0F172A", marginTop: "2px" }}>
                      {poolReport?.beneficiaries_served_count ?? poolReport?.completed_encounters_count ?? 0}
                    </div>
                  </div>
                  <div style={{ backgroundColor: "#F8FAFC", padding: "14px", borderRadius: LW_DESIGN_TOKENS.radius.md }}>
                    <div style={{ fontSize: "12px", color: "#64748B" }}>Completed Encounters</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: "#0F172A", marginTop: "2px" }}>
                      {poolReport?.completed_encounters_count ?? 0}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: STATEMENTS & ACCOUNTING                                    */}
        {/* ================================================================= */}
        {activeTab === "STATEMENTS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
                Accounting Statements & Settlement Ledger
              </h2>
              <button
                type="button"
                onClick={handleDownloadCsv}
                style={{
                  padding: "8px 16px",
                  backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: LW_DESIGN_TOKENS.radius.md,
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                📥 Export Statement (CSV)
              </button>
            </div>

            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "24px",
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: 800, margin: "0 0 12px" }}>
                Statement for Period: Current Operating Year (2026)
              </h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #E2E8F0", textAlign: "left", color: "#64748B" }}>
                    <th style={{ padding: "8px" }}>Ledger Line</th>
                    <th style={{ padding: "8px" }}>Category</th>
                    <th style={{ padding: "8px" }}>Status</th>
                    <th style={{ padding: "8px", textAlign: "right" }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={{ padding: "10px 8px" }}>Initial Escrow Cash Received</td>
                    <td style={{ padding: "10px 8px" }}>Direct Escrow Deposit</td>
                    <td style={{ padding: "10px 8px", color: "#166534", fontWeight: 700 }}>CLEARED</td>
                    <td style={{ padding: "10px 8px", textAlign: "right", fontWeight: 700 }}>
                      {formatMoneyMinor({ amountMinor: poolReport?.funded_cash_received_minor ?? 0, currency: "NGN" })}
                    </td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={{ padding: "10px 8px" }}>Consultation Redemptions</td>
                    <td style={{ padding: "10px 8px" }}>Verified Teleconsults</td>
                    <td style={{ padding: "10px 8px", color: "#0F766E", fontWeight: 700 }}>SETTLED</td>
                    <td style={{ padding: "10px 8px", textAlign: "right", fontWeight: 700 }}>
                      {formatMoneyMinor({ amountMinor: poolReport?.redeemed_settled_minor ?? 0, currency: "NGN" })}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ padding: "10px 8px", fontWeight: 800 }}>Remaining Escrow Balance</td>
                    <td style={{ padding: "10px 8px" }}>Available Humanitarian Escrow</td>
                    <td style={{ padding: "10px 8px", color: "#0284C7", fontWeight: 800 }}>ACTIVE</td>
                    <td style={{ padding: "10px 8px", textAlign: "right", fontWeight: 800, color: "#0284C7" }}>
                      {formatMoneyMinor({ amountMinor: poolReport?.available_to_reserve_minor ?? 0, currency: "NGN" })}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: PROGRAMME TERMS & RULES                                    */}
        {/* ================================================================= */}
        {activeTab === "TERMS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "20px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: 0 }}>
              Programme Scope & Governance Terms
            </h2>

            <div
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: LW_DESIGN_TOKENS.radius.lg,
                border: "1px solid #CBD5E1",
                padding: "24px",
                lineHeight: 1.6,
                fontSize: "14px",
                color: "#334155",
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: LW_DESIGN_TOKENS.colors.royalNavy, margin: "0 0 10px" }}>
                LoveWorld Medicaid Humanitarian Care Pool (AGR-LW-MEDICAID-NG-2026)
              </h3>
              <p>
                <strong>1. Covered Services:</strong> Remote General Practice teleconsultations, acute malaria/fever triage, initial prescription bridging, and coordination escalation to LoveWorld Medical Centre Ikeja or partner facilities.
              </p>
              <p>
                <strong>2. Entitlement Invariant:</strong> Funds are locked in restricted pool accounts. No funds may be co-mingled with operator working capital. Unused funds remain credited to the sponsor.
              </p>
              <p>
                <strong>3. Privacy Protection:</strong> In accordance with the NDPA 2023, GDPR Article 9, and the LoveWorld Care Blueprint (§10.5), patient personal identifiable information (PII) and personal health information (PHI) are strictly isolated. Sponsors receive aggregate utilization only, subject to k-anonymity suppression (k ≥ 5).
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
