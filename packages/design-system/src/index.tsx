import React, { useState } from "react";
import { OFFLINE_EMERGENCY_CONTACTS_NG } from "./tokens";

export * from "./tokens";

/**
 * §1.4, §6.1, §8.5 & AT-11:
 * Zero-login, zero-payment, zero-AI Emergency Guidance Banner & Expandable Drawer.
 */
export function EmergencySafetyBanner() {
  const [expanded, setExpanded] = useState(false);

  return (
    <section
      aria-label="Urgent and Emergency Medical Guidance"
      style={{
        backgroundColor: "#FEF2F2",
        borderBottom: "2px solid #B91C1C",
        color: "#7F1D1D",
        padding: "12px 16px",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <div style={{ fontSize: "14px", lineHeight: 1.5 }}>
          <strong>Medical Emergency?</strong> LoveWorld Care does not dispatch ambulances or monitor
          unassigned queues 24/7. For chest pain, severe breathing difficulty, or uncontrolled
          bleeding, seek immediate in-person emergency care.
        </div>
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          style={{
            minHeight: "44px",
            padding: "8px 16px",
            backgroundColor: "#B91C1C",
            color: "#FFFFFF",
            fontWeight: 700,
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
          }}
        >
          {expanded ? "Hide Emergency Numbers" : "Get Urgent Help (Free / Offline)"}
        </button>
      </div>
      {expanded && (
        <div
          role="region"
          aria-label="Verified Emergency Contacts"
          style={{
            maxWidth: "1200px",
            margin: "12px auto 0",
            paddingTop: "12px",
            borderTop: "1px solid #FECACA",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "12px",
          }}
        >
          {OFFLINE_EMERGENCY_CONTACTS_NG.map((contact) => (
            <div
              key={contact.phone}
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #FCA5A5",
                borderRadius: "6px",
                padding: "12px",
              }}
            >
              <div style={{ fontSize: "12px", fontWeight: 600, color: "#991B1B" }}>
                {contact.region}
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, margin: "4px 0" }}>
                {contact.label}
              </div>
              <a
                href={`tel:${contact.phone}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  minHeight: "44px",
                  fontWeight: 800,
                  fontSize: "16px",
                  color: "#B91C1C",
                  textDecoration: "underline",
                }}
              >
                Call {contact.phone}
              </a>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * §21.6 & AT-13: Shared-Device Session Lock & Quick Wipe Bar.
 * Protects patients or clinicians using shared mobile devices.
 */
export function SharedDeviceSessionLockBar(props: {
  workspaceName: string;
  actorDisplayName: string;
  isLocked: boolean;
  onToggleLock: () => void;
}) {
  return (
    <header
      style={{
        backgroundColor: "#0B1F3A",
        color: "#FFFFFF",
        padding: "10px 16px",
        borderBottom: "3px solid #C89D3C",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <div>
          <span
            style={{
              backgroundColor: "#C89D3C",
              color: "#0B1F3A",
              fontWeight: 800,
              fontSize: "12px",
              padding: "3px 8px",
              borderRadius: "4px",
              marginRight: "10px",
              textTransform: "uppercase",
            }}
          >
            {props.workspaceName}
          </span>
          <span style={{ fontWeight: 600, fontSize: "15px" }}>
            LoveWorld Care — {props.actorDisplayName}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={props.onToggleLock}
            style={{
              minHeight: "44px",
              padding: "8px 14px",
              backgroundColor: props.isLocked ? "#0F766E" : "#1E293B",
              color: "#FFFFFF",
              border: "1px solid #94A3B8",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {props.isLocked
              ? "Unlock Session (Re-Authenticate MFA)"
              : "Shared Phone? Lock Session Immediately"}
          </button>
        </div>
      </div>
    </header>
  );
}

/**
 * FR-INT-03 & §8.2: Mandatory watermark separating AI draft output from clinician facts.
 */
export function AiDraftWatermarkBadge(props: { modelId: string; costKobo?: number }) {
  return (
    <div
      role="note"
      aria-label="AI Draft Watermark"
      style={{
        backgroundColor: "#FFFBEB",
        border: "2px dashed #D97706",
        color: "#92400E",
        padding: "10px 12px",
        borderRadius: "6px",
        fontSize: "13px",
        fontWeight: 700,
      }}
    >
      UNSIGNED / FOR CLINICIAN REVIEW ONLY — Generated by {props.modelId} (Model Made Clinical
      Decision: FALSE). Must be verified and signed by a licensed clinician.
      {typeof props.costKobo === "number" ? ` [Attributed AI Cost: ₦${(props.costKobo / 100).toFixed(2)}]` : ""}
    </div>
  );
}

/**
 * FR-CNS-02 & §13.4: Cryptographic Ed25519 + SHA-256 Signed Clinical Document Seal.
 */
export function SignedRecordSeal(props: {
  signerName: string;
  mdcnLicence: string;
  signedAtIso: string;
  documentSha256: string;
}) {
  return (
    <div
      style={{
        backgroundColor: "#F0FDFA",
        border: "1px solid #0F766E",
        color: "#115E59",
        padding: "12px",
        borderRadius: "6px",
        fontSize: "13px",
      }}
    >
      <div style={{ fontWeight: 800 }}>
        CLINICIAN SIGNED & IMMUTABLE RECORD (Ed25519 Verified)
      </div>
      <div>
        Signed by <strong>{props.signerName}</strong> ({props.mdcnLicence}) at {props.signedAtIso}
      </div>
      <div style={{ fontFamily: "monospace", fontSize: "12px", marginTop: "4px" }}>
        SHA-256: {props.documentSha256}
      </div>
    </div>
  );
}
