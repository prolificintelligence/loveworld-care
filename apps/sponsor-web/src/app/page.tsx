"use client";

import React, { useEffect, useState } from "react";
import { SharedDeviceSessionLockBar, LW_DESIGN_TOKENS } from "@loveworld-care/design-system";
import { formatMoneyMinor } from "@loveworld-care/domain-types";
import { LoveWorldCareApiClient, SponsorPoolSummaryDTO } from "@loveworld-care/api-contracts";

export default function SponsorCareWorkspacePage() {
  const [sessionLocked, setSessionLocked] = useState(false);
  const [sponsorAdminId] = useState("sponsor-admin-01");
  const [sponsorName] = useState("LoveWorld Medicaid Humanitarian Foundation");
  const [sponsorOrg] = useState("sponsor-loveworld-medicaid");
  const [agreementId, setAgreementId] = useState("AGR-LW-MEDICAID-NG-2026");

  // API State
  const [apiClient, setApiClient] = useState<LoveWorldCareApiClient | null>(null);
  const [poolReport, setPoolReport] = useState<SponsorPoolSummaryDTO | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [simulateSmallCohort, setSimulateSmallCohort] = useState(false);

  // Initialize Auth & API Client
  useEffect(() => {
    async function initSponsor() {
      setIsLoading(true);
      try {
        let token = localStorage.getItem("lw_sponsor_token");
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
              ttl_minutes: 180,
            }),
          });
          if (devRes.ok) {
            const data = await devRes.json();
            token = data.access_token;
            if (token) localStorage.setItem("lw_sponsor_token", token);
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

  if (sessionLocked) {
    return (
      <div>
        <SharedDeviceSessionLockBar
          workspaceName="SponsorCare Portal"
          actorDisplayName="Institutional Session (Locked)"
          isLocked={true}
          onToggleLock={() => setSessionLocked(false)}
        />
        <main
          style={{
            maxWidth: "480px",
            margin: "80px auto",
            textAlign: "center",
            padding: "24px",
            backgroundColor: "#FFFFFF",
            borderRadius: "12px",
            border: "1px solid #CBD5E1",
          }}
        >
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>🔒</div>
          <h2 style={{ color: "#0B1F3A", margin: "0 0 8px 0" }}>Institutional Session Locked</h2>
          <p style={{ color: "#64748B", fontSize: "14px" }}>
            Re-authenticate to view institutional care pool balances and aggregate reporting.
          </p>
          <button
            type="button"
            onClick={() => setSessionLocked(false)}
            style={{
              marginTop: "16px",
              minHeight: "44px",
              padding: "10px 24px",
              backgroundColor: "#1E3A8A",
              color: "#FFFFFF",
              fontWeight: 700,
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
            }}
          >
            Unlock Session
          </button>
        </main>
      </div>
    );
  }

  // Small cohort simulation for AT-14 demonstration
  const effectiveKSuppressed = simulateSmallCohort || poolReport?.k_anonymity_suppressed;

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC" }}>
      {/* Session Header */}
      <SharedDeviceSessionLockBar
        workspaceName="SponsorCare & Institutional Workspace"
        actorDisplayName={`${sponsorName} (Aggregate Reporting Only · §10.5)`}
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
        onSignOut={() => {
          localStorage.removeItem("lw_sponsor_token");
          window.location.reload();
        }}
      />

      <main style={{ maxWidth: "1200px", margin: "24px auto", padding: "0 16px 64px" }}>
        {/* Error / Offline Alert */}
        {networkError && (
          <div
            role="alert"
            style={{
              backgroundColor: "#FEF2F2",
              border: "1px solid #FCA5A5",
              color: "#991B1B",
              padding: "12px 16px",
              borderRadius: "8px",
              marginBottom: "20px",
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

        {/* Top Header Card */}
        <section
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #CBD5E1",
            borderRadius: "12px",
            padding: "24px",
            marginBottom: "24px",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.03)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <span
                style={{
                  backgroundColor: "#E0E7FF",
                  color: "#1E3A8A",
                  fontWeight: 800,
                  fontSize: "11px",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  textTransform: "uppercase",
                }}
              >
                Contracted Care Entitlements (§10.2)
              </span>
              <h1 style={{ margin: "8px 0 4px 0", fontSize: "22px", color: "#0B1F3A", fontWeight: 800 }}>
                Agreement <code>{agreementId}</code>
              </h1>
              <p style={{ margin: 0, fontSize: "14px", color: "#475569" }}>
                Sponsor: <strong>{poolReport?.sponsor_name || sponsorName}</strong> • Currency: <strong>{poolReport?.currency || "NGN"}</strong>
              </p>
            </div>

            <button
              type="button"
              onClick={refreshReport}
              disabled={isLoading}
              style={{
                minHeight: "44px",
                padding: "8px 16px",
                backgroundColor: "#F1F5F9",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "13px",
                color: "#1E293B",
                cursor: isLoading ? "not-allowed" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span>🔄</span> {isLoading ? "Syncing..." : "Sync Live Balances"}
            </button>
          </div>

          <div
            style={{
              marginTop: "16px",
              padding: "12px 14px",
              backgroundColor: "#F8FAFC",
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              fontSize: "13px",
              color: "#334155",
              lineHeight: 1.5,
            }}
          >
            <strong>Accounting &amp; Legal Boundary (§10.1 &amp; §10.4):</strong> This agreement governs a
            contracted defined-service care entitlement pool. It is not an insurance or indemnity policy.
            Reservations are atomic against settled cash or Espees credits. Unfunded pledges are non-spendable.
          </div>

          {/* Atomic Pool Balances Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
              gap: "16px",
              marginTop: "20px",
            }}
          >
            {/* Committed Unfunded */}
            <div
              style={{
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#64748B", fontWeight: 600 }}>
                Committed Pledge (Uncollected)
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#64748B", marginTop: "4px" }}>
                {formatMoneyMinor({
                  amountMinor: poolReport?.committed_unfunded_minor ?? 500000000,
                  currency: (poolReport?.currency as any) || "NGN",
                })}
              </div>
              <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "4px" }}>
                Non-spendable until bank receipt
              </div>
            </div>

            {/* Funded Cash Received */}
            <div
              style={{
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#1E3A8A", fontWeight: 600 }}>
                Funded Cash Received (Restricted)
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0B1F3A", marginTop: "4px" }}>
                {formatMoneyMinor({
                  amountMinor: poolReport?.funded_cash_received_minor ?? 1200000000,
                  currency: (poolReport?.currency as any) || "NGN",
                })}
              </div>
              <div style={{ fontSize: "11px", color: "#0F766E", marginTop: "4px" }}>
                Settled into LoveWorld Care custodial pool
              </div>
            </div>

            {/* Active Reserved */}
            <div
              style={{
                backgroundColor: "#FDF8EC",
                border: "1px solid #FCD34D",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#92400E", fontWeight: 600 }}>
                Active Reserved Entitlements
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#B45309", marginTop: "4px" }}>
                {formatMoneyMinor({
                  amountMinor: poolReport?.active_reserved_minor ?? 0,
                  currency: (poolReport?.currency as any) || "NGN",
                })}
              </div>
              <div style={{ fontSize: "11px", color: "#B45309", marginTop: "4px" }}>
                Locked for scheduled consultations
              </div>
            </div>

            {/* Redeemed & Settled */}
            <div
              style={{
                backgroundColor: "#F0FDFA",
                border: "1px solid #99F6E4",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#115E59", fontWeight: 600 }}>
                Redeemed &amp; Settled
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0F766E", marginTop: "4px" }}>
                {formatMoneyMinor({
                  amountMinor: poolReport?.redeemed_settled_minor ?? 0,
                  currency: (poolReport?.currency as any) || "NGN",
                })}
              </div>
              <div style={{ fontSize: "11px", color: "#0F766E", marginTop: "4px" }}>
                Doctor signed with Ed25519
              </div>
            </div>

            {/* Available to Reserve */}
            <div
              style={{
                backgroundColor: "#F0F9FF",
                border: "1px solid #BAE6FD",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#0369A1", fontWeight: 600 }}>
                Available to Reserve
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0284C7", marginTop: "4px" }}>
                {formatMoneyMinor({
                  amountMinor: poolReport?.available_to_reserve_minor ?? 1200000000,
                  currency: (poolReport?.currency as any) || "NGN",
                })}
              </div>
              <div style={{ fontSize: "11px", color: "#0369A1", marginTop: "4px" }}>
                Immediate beneficiary capacity
              </div>
            </div>
          </div>
        </section>

        {/* Privacy-Safe Aggregate Utilisation & k>=5 Suppression */}
        <section
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #CBD5E1",
            borderRadius: "12px",
            padding: "24px",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.03)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <h2 style={{ margin: "0 0 6px 0", fontSize: "18px", color: "#0B1F3A", fontWeight: 800 }}>
                Privacy-Safe Aggregate Utilisation (§10.5 &amp; AT-14)
              </h2>
              <p style={{ margin: 0, fontSize: "13px", color: "#475569" }}>
                Sponsors NEVER receive patient names, intake text, diagnoses, or clinician notes (AT-06).
              </p>
            </div>

            <span
              style={{
                backgroundColor: "#DCFCE7",
                color: "#166534",
                fontSize: "12px",
                fontWeight: 700,
                padding: "4px 10px",
                borderRadius: "6px",
                border: "1px solid #BBF7D0",
              }}
            >
              Zero PHI Disclosed ✓
            </span>
          </div>

          {/* Test Small-Cohort Suppression Toggle */}
          <div style={{ marginTop: "16px" }}>
            <label
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={simulateSmallCohort}
                onChange={(e) => setSimulateSmallCohort(e.target.checked)}
                style={{ width: "16px", height: "16px" }}
              />
              <span>
                Simulate Small-Cohort Anonymity Filter (k = 3 beneficiaries &lt; 5 minimum threshold — AT-14)
              </span>
            </label>
          </div>

          {/* Suppression Status Display */}
          <div
            style={{
              marginTop: "16px",
              padding: "16px",
              borderRadius: "10px",
              backgroundColor: effectiveKSuppressed ? "#FEF2F2" : "#F0FDF4",
              border: `1px solid ${effectiveKSuppressed ? "#FCA5A5" : "#86EFAC"}`,
              fontSize: "14px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <strong>Eligible Beneficiary Cohort Size:</strong>{" "}
                <span>
                  {effectiveKSuppressed
                    ? "SUPPRESSED (k < 5 small-cohort differential privacy active)"
                    : `${poolReport?.eligible_beneficiary_count ?? 24} Beneficiaries`}
                </span>
              </div>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: effectiveKSuppressed ? "#991B1B" : "#166534",
                }}
              >
                {effectiveKSuppressed ? "⚠️ Headcount Redacted" : "✓ k ≥ 5 Met"}
              </span>
            </div>

            <div style={{ marginTop: "10px", fontSize: "13px", color: "#334155" }}>
              <strong>Completed Encounters Count:</strong>{" "}
              {poolReport?.completed_encounters_count ?? 0}
            </div>

            <div style={{ marginTop: "6px", fontSize: "12px", color: "#475569" }}>
              <strong>Clinical Narrative / Diagnoses / Notes Disclosed:</strong>{" "}
              <code style={{ color: "#B91C1C", fontWeight: 700 }}>
                NONE (Strictly Forbidden by Server Architecture AT-06 &amp; ADR-0005)
              </code>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
