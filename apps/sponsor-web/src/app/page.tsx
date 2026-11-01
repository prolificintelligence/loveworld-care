"use client";

import React, { useState } from "react";
import { SharedDeviceSessionLockBar } from "@loveworld-care/design-system";
import { formatMoneyMinor } from "@loveworld-care/domain-types";

export default function SponsorCareWorkspacePage() {
  const [sessionLocked, setSessionLocked] = useState(false);
  const [simulateSmallCohort, setSimulateSmallCohort] = useState(false);

  const cohortCount = simulateSmallCohort ? 3 : 24;
  const kSuppressed = cohortCount < 5;

  if (sessionLocked) {
    return (
      <SharedDeviceSessionLockBar
        workspaceName="SponsorCare Portal"
        actorDisplayName="Locked Session"
        isLocked={true}
        onToggleLock={() => setSessionLocked(false)}
      />
    );
  }

  return (
    <div>
      <SharedDeviceSessionLockBar
        workspaceName="SponsorCare & Institutional Workspace"
        actorDisplayName="LoveWorld Medicaid Sponsor Admin · Aggregate Reporting Only (§10.5)"
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
      />

      <main style={{ maxWidth: "1200px", margin: "24px auto", padding: "0 16px 64px" }}>
        <section
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #CBD5E1",
            borderRadius: "10px",
            padding: "20px",
            marginBottom: "24px",
          }}
        >
          <h1 style={{ marginTop: 0, color: "#0B1F3A" }}>
            Agreement <code>AGR-LW-MEDICAID-NG-2026</code> — Atomic Pool Balances (§10.4)
          </h1>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            <strong>Accounting & Legal Boundary (§10.1 & §10.4):</strong> This is a defined-service
            entitlement pool, not an unlicensed health insurance or unlimited HMO scheme. Uncollected
            pledges cannot be reserved; only settled cash or Espees credits are available for
            reservation.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "16px",
              marginTop: "16px",
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
                Uncollected Pledge (Not Spendable)
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#64748B" }}>
                {formatMoneyMinor({ amountMinor: 500000000, currency: "NGN" })}
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
                Funded Cash Received (Restricted Pool)
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0B1F3A" }}>
                {formatMoneyMinor({ amountMinor: 1200000000, currency: "NGN" })}
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
              <div style={{ fontSize: "12px", color: "#92400E" }}>Active Reserved Entitlements</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#B45309" }}>
                {formatMoneyMinor({ amountMinor: 1800000, currency: "NGN" })} (3 Active Bookings)
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
                Redeemed (Clinician-Signed Encounters)
              </div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0F766E" }}>
                {formatMoneyMinor({ amountMinor: 14400000, currency: "NGN" })} (24 Signed Episodes)
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
            Privacy-Safe Aggregate Utilisation Report (k &gt;= 5 Suppression — §10.5 & AT-14)
          </h2>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            Sponsors NEVER receive patient names, diagnoses, intake statements, or clinical notes
            (AT-06). When a queried cohort has fewer than 5 beneficiaries (<code>k &lt; 5</code>),
            headcounts are automatically suppressed to prevent re-identification risk (AT-14).
          </p>

          <label style={{ display: "flex", alignItems: "center", minHeight: "44px", gap: "8px", fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={simulateSmallCohort}
              onChange={(e) => setSimulateSmallCohort(e.target.checked)}
            />
            Test Small-Cohort Filter (k = 3 beneficiaries &lt; 5 minimum threshold — AT-14)
          </label>

          <div
            style={{
              marginTop: "12px",
              padding: "14px",
              borderRadius: "8px",
              backgroundColor: kSuppressed ? "#FEF2F2" : "#F8FAFC",
              border: `1px solid ${kSuppressed ? "#B91C1C" : "#CBD5E1"}`,
              fontSize: "14px",
            }}
          >
            <div>
              <strong>Beneficiaries Served Count:</strong>{" "}
              {kSuppressed
                ? "SUPPRESSED_SMALL_COHORT_K_LT_5 (Privacy Protection Active)"
                : `${cohortCount} Beneficiaries`}
            </div>
            <div style={{ marginTop: "6px" }}>
              <strong>Clinical Narrative / Diagnoses Disclosed:</strong>{" "}
              <code>NONE (Strictly Forbidden by Server Policy AT-06)</code>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
