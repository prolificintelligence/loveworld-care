"use client";

import React, { useState } from "react";
import { SharedDeviceSessionLockBar } from "@loveworld-care/design-system";
import { computeEncounterUnitEconomics, formatMoneyMinor } from "@loveworld-care/domain-types";

type CommandTab = "EXECUTIVE" | "CLINICAL_GOVERNANCE" | "OPERATIONS_SUPPORT" | "FINANCE_LEDGER";

export default function CareCommandConsolePage() {
  const [activeTab, setActiveTab] = useState<CommandTab>("EXECUTIVE");
  const [sessionLocked, setSessionLocked] = useState(false);
  const [aiKillSwitchEnabled, setAiKillSwitchEnabled] = useState(false);
  const [checkerApproved, setCheckerApproved] = useState(false);

  const unitEconomics = computeEncounterUnitEconomics({
    encounterId: "ENC-BASELINE-NG",
    payerCohort: "SPONSOR_DEFINED_SERVICES",
    currency: "NGN",
    settledRevenueMinor: 600000, // ₦6,000.00
    clinicianDirectCostMinor: 330000, // ₦3,300.00
    paymentProcessingFeeMinor: 15000, // ₦150.00
    communicationsRtcModelCostMinor: 20000, // ₦200.00
    variableSupportCostMinor: 40000, // ₦400.00
    refundQualityReserveMinor: 20000, // ₦200.00
  });

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
    <div>
      <SharedDeviceSessionLockBar
        workspaceName="Care Command Console"
        actorDisplayName="Authorised Operator · Zero Free-Text PHI View (§12.3 & §16.2)"
        isLocked={false}
        onToggleLock={() => setSessionLocked(true)}
      />

      <nav
        style={{
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #CBD5E1",
          padding: "10px 16px",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
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
                minHeight: "44px",
                padding: "8px 16px",
                backgroundColor: activeTab === id ? "#0B1F3A" : "#F1F5F9",
                color: activeTab === id ? "#FFFFFF" : "#0F172A",
                fontWeight: 700,
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      <main style={{ maxWidth: "1200px", margin: "24px auto", padding: "0 16px 64px" }}>
        {activeTab === "EXECUTIVE" && (
          <div style={{ display: "grid", gap: "20px" }}>
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                North-Star & Unit Economics Attribution (§3.1 & §17.2)
              </h2>
              <p style={{ fontSize: "13px", color: "#475569" }}>
                North-Star Metric: <strong>Safe, completed, clinically signed care episodes</strong>{" "}
                with positive contribution margin. Unredeemed sponsor cash is held as a restricted
                liability and NEVER counted as earned operating revenue.
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
                    Settled GP Encounter Revenue
                  </div>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#0B1F3A" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.settledRevenueMinor,
                      currency: "NGN",
                    })}
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
                    Clinician Direct Compensation
                  </div>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#334155" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.clinicianDirectCostMinor,
                      currency: "NGN",
                    })}
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
                    Contribution Margin Before Fixed Costs
                  </div>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#0F766E" }}>
                    {formatMoneyMinor({
                      amountMinor: unitEconomics.contributionMarginMinor,
                      currency: "NGN",
                    })}{" "}
                    ({(unitEconomics.contributionMarginRatioBps / 100).toFixed(2)}%)
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
                  <div style={{ fontSize: "12px", color: "#92400E" }}>
                    Base Break-Even Volume (§17.5)
                  </div>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#0B1F3A" }}>
                    1,143 Signed Encounters / Mo
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {activeTab === "CLINICAL_GOVERNANCE" && (
          <div style={{ display: "grid", gap: "20px" }}>
            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
                Global AI-Off Kill Switch & Model Router Policy (§15.6 & AT-16)
              </h2>
              <p style={{ fontSize: "14px" }}>
                Current AI Gateway State:{" "}
                <strong style={{ color: aiKillSwitchEnabled ? "#B91C1C" : "#0F766E" }}>
                  {aiKillSwitchEnabled
                    ? "AI-OFF MODE ACTIVE (All Generative Models Disabled — Deterministic & Human Care 100% Operational)"
                    : "POLICY-LIMITED AI ASSISTANCE ENABLED (T3 Clinical Restricted to Approved Endpoints)"}
                </strong>
              </p>
              <button
                type="button"
                onClick={() => setAiKillSwitchEnabled((v) => !v)}
                style={{
                  minHeight: "44px",
                  padding: "10px 18px",
                  backgroundColor: aiKillSwitchEnabled ? "#0F766E" : "#B91C1C",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                {aiKillSwitchEnabled
                  ? "Restore Policy-Limited AI Assistance"
                  : "Trigger Global AI-Off Kill Switch Immediately (FR-SEC-02)"}
              </button>
            </section>

            <section
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <h3 style={{ marginTop: 0 }}>
                Active Deterministic Protocol Bundle Registry (§7.2)
              </h3>
              <div
                style={{
                  backgroundColor: "#F8FAFC",
                  border: "1px solid #CBD5E1",
                  padding: "14px",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
              >
                <div>
                  <strong>Bundle ID:</strong> <code>LW-NG-GP-ADULT-V1</code> · Version:{" "}
                  <code>1.0.0</code> · Status: <strong>ACTIVE</strong>
                </div>
                <div style={{ marginTop: "4px" }}>
                  <strong>Dual Clinical Authorization:</strong> Owner:{" "}
                  <code>Dr. Adebayo Okonkwo (MDCN/R/44210)</code> · Reviewer:{" "}
                  <code>Dr. Chidinma Eze (MDCN/R/38901)</code>
                </div>
              </div>
            </section>
          </div>
        )}

        {activeTab === "OPERATIONS_SUPPORT" && (
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "10px",
              padding: "20px",
            }}
          >
            <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
              Non-Clinical Support Desk & Queue Health (PHI Masked — §16.2 & §21.4)
            </h2>
            <p style={{ fontSize: "13px", color: "#475569" }}>
              Support agents see booking, payment, and roster metadata only. Clinical narratives and
              diagnoses are masked at the server boundary (<code>[REDACTED_PHI_T3]</code>).
            </p>
            <div
              style={{
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                padding: "14px",
                borderRadius: "8px",
                fontSize: "13px",
              }}
            >
              <strong>Approved Support Script (Clinical Boundary — §21.4):</strong> &ldquo;I can
              assist with your appointment and account. A medical professional must assess questions
              about your symptoms or treatment. I can help route that request through the
              appropriate clinical channel when it is staffed.&rdquo;
            </div>
          </section>
        )}

        {activeTab === "FINANCE_LEDGER" && (
          <section
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "10px",
              padding: "20px",
            }}
          >
            <h2 style={{ marginTop: 0, color: "#0B1F3A" }}>
              Two-Entity Accounting Books & Maker/Checker Queue (§17.1 & §17.7)
            </h2>
            <p style={{ fontSize: "13px", color: "#475569" }}>
              Separate Books Enforced: <code>LOVEWORLD_CARE_OPERATOR</code> (Clinical care
              collections, restricted sponsor pools, clinician payables) vs.{" "}
              <code>PROLIFIC_INTELLIGENCE</code> (Managed platform & AI SLA charges).
            </p>
            <div
              style={{
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                padding: "14px",
                marginTop: "12px",
              }}
            >
              <div style={{ fontWeight: 700, fontSize: "14px" }}>
                Exception <code>EXC-FIN-0041</code> · Category: <code>SETTLED_BUT_CANCELLED</code> ·
                Amount: ₦6,000.00
              </div>
              <div style={{ fontSize: "13px", color: "#475569", margin: "6px 0" }}>
                Maker: <code>finance-maker-01</code> · Status:{" "}
                <strong>{checkerApproved ? "APPROVED_BY_DISTINCT_CHECKER" : "PENDING_CHECKER"}</strong>
              </div>
              <button
                type="button"
                disabled={checkerApproved}
                onClick={() => setCheckerApproved(true)}
                style={{
                  minHeight: "44px",
                  padding: "8px 16px",
                  backgroundColor: checkerApproved ? "#0F766E" : "#0B1F3A",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  border: "none",
                  borderRadius: "6px",
                  cursor: checkerApproved ? "default" : "pointer",
                }}
              >
                {checkerApproved
                  ? "Approved by Checker (finance-checker-02)"
                  : "Approve as Distinct Checker (finance-checker-02 != maker)"}
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
