import React, { useState } from "react";
import {
  APP_THEMES,
  AppTheme,
  LW_DESIGN_TOKENS,
  OFFLINE_EMERGENCY_CONTACTS_NG,
  OfflineEmergencyContact,
} from "./tokens";

export * from "./tokens";

/**
 * §1.4, §6.1, §8.5 & AT-11:
 * Zero-login, zero-payment, zero-AI Emergency Guidance Banner & Expandable Drawer.
 * High-contrast WCAG 2.2 AA crimson alert banner.
 */
export function EmergencySafetyBanner(props: { compact?: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section
      aria-label="Urgent and Emergency Medical Guidance"
      style={{
        backgroundColor: LW_DESIGN_TOKENS.colors.emergencyCrimsonSoft,
        borderBottom: `2px solid ${LW_DESIGN_TOKENS.colors.emergencyCrimson}`,
        color: "#7F1D1D",
        padding: props.compact ? "8px 16px" : "12px 16px",
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
        <div style={{ fontSize: "14px", lineHeight: 1.5, flex: "1 1 300px" }}>
          <strong style={{ color: LW_DESIGN_TOKENS.colors.emergencyCrimson }}>
            Emergency Notice:
          </strong>{" "}
          LoveWorld Care does NOT dispatch ambulances. For severe chest pain, breathing difficulty,
          or uncontrolled bleeding, call emergency services or go to the nearest emergency room immediately.
        </div>
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          style={{
            minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
            padding: "8px 16px",
            backgroundColor: LW_DESIGN_TOKENS.colors.emergencyCrimson,
            color: "#FFFFFF",
            fontWeight: 700,
            fontSize: "14px",
            borderRadius: LW_DESIGN_TOKENS.radius.md,
            border: "none",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          {expanded ? "Hide Emergency Contacts" : "Free Emergency Numbers (Offline)"}
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
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                padding: "12px",
              }}
            >
              <div style={{ fontSize: "12px", fontWeight: 600, color: "#991B1B" }}>
                {contact.region}
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, margin: "4px 0", color: "#1F2937" }}>
                {contact.label}
              </div>
              <a
                href={`tel:${contact.phone}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                  fontWeight: 800,
                  fontSize: "16px",
                  color: LW_DESIGN_TOKENS.colors.emergencyCrimson,
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
 * Protects patients or clinicians using shared mobile devices in waiting rooms or homes.
 */
export function SharedDeviceSessionLockBar(props: {
  workspaceName: string;
  actorDisplayName: string;
  isLocked: boolean;
  onToggleLock: () => void;
  onSignOut?: () => void;
}) {
  return (
    <header
      style={{
        backgroundColor: LW_DESIGN_TOKENS.colors.royalNavy,
        color: "#FFFFFF",
        padding: "8px 16px",
        borderBottom: `3px solid ${LW_DESIGN_TOKENS.colors.warmGold}`,
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
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span
            style={{
              backgroundColor: LW_DESIGN_TOKENS.colors.warmGold,
              color: LW_DESIGN_TOKENS.colors.royalNavy,
              fontWeight: 800,
              fontSize: "11px",
              padding: "3px 8px",
              borderRadius: "4px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            {props.workspaceName}
          </span>
          <span style={{ fontWeight: 600, fontSize: "14px" }}>
            {props.actorDisplayName}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            onClick={props.onToggleLock}
            style={{
              minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
              padding: "6px 14px",
              backgroundColor: props.isLocked
                ? LW_DESIGN_TOKENS.colors.clinicalEmerald
                : "#1E293B",
              color: "#FFFFFF",
              border: "1px solid #94A3B8",
              borderRadius: LW_DESIGN_TOKENS.radius.md,
              fontWeight: 600,
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            {props.isLocked
              ? "🔒 Unlock Session"
              : "🔒 Shared Phone? Lock"}
          </button>
          {props.onSignOut && (
            <button
              type="button"
              onClick={props.onSignOut}
              style={{
                minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                padding: "6px 12px",
                backgroundColor: "transparent",
                color: "#E2E8F0",
                border: "1px solid #475569",
                borderRadius: LW_DESIGN_TOKENS.radius.md,
                fontWeight: 600,
                fontSize: "13px",
                cursor: "pointer",
              }}
            >
              Sign Out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

/**
 * Mobile-First Bottom Navigation Bar (§21.6).
 * Target WCAG 2.2 AA 44x44px touch targets.
 */
export interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly icon: string;
  readonly badgeCount?: number;
}

export function MobileBottomNavBar(props: {
  activeTab: string;
  onSelectTab: (id: string) => void;
  items: readonly NavItem[];
}) {
  return (
    <nav
      aria-label="Bottom Primary Navigation"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: "#FFFFFF",
        borderTop: "1px solid #E2E8F0",
        boxShadow: "0 -4px 12px rgba(0, 0, 0, 0.05)",
        zIndex: 50,
      }}
    >
      <div
        style={{
          maxWidth: "600px",
          margin: "0 auto",
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          padding: "6px 8px env(safe-area-inset-bottom, 8px)",
        }}
      >
        {props.items.map((item) => {
          const isActive = props.activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => props.onSelectTab(item.id)}
              style={{
                flex: "1 1 0",
                minHeight: `${LW_DESIGN_TOKENS.touchTarget.minHeightPx}px`,
                minWidth: `${LW_DESIGN_TOKENS.touchTarget.minWidthPx}px`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "2px",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "4px 8px",
                color: isActive
                  ? LW_DESIGN_TOKENS.colors.royalNavy
                  : LW_DESIGN_TOKENS.colors.textMuted,
                fontWeight: isActive ? 700 : 500,
                fontSize: "12px",
                position: "relative",
              }}
            >
              <span style={{ fontSize: "20px", lineHeight: 1 }}>{item.icon}</span>
              <span>{item.label}</span>
              {item.badgeCount && item.badgeCount > 0 ? (
                <span
                  style={{
                    position: "absolute",
                    top: "2px",
                    right: "25%",
                    backgroundColor: LW_DESIGN_TOKENS.colors.emergencyCrimson,
                    color: "#FFFFFF",
                    fontSize: "10px",
                    fontWeight: 800,
                    borderRadius: "999px",
                    padding: "1px 5px",
                    lineHeight: 1.2,
                  }}
                >
                  {item.badgeCount}
                </span>
              ) : null}
              {isActive && (
                <span
                  style={{
                    position: "absolute",
                    bottom: "-2px",
                    width: "20px",
                    height: "3px",
                    backgroundColor: LW_DESIGN_TOKENS.colors.warmGold,
                    borderRadius: "2px",
                  }}
                />
              )}
            </button>
          );
        })}
      </div>
    </nav>
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
        borderRadius: LW_DESIGN_TOKENS.radius.md,
        fontSize: "13px",
        fontWeight: 700,
        lineHeight: 1.4,
      }}
    >
      ⚠️ <strong>UNSIGNED / FOR CLINICIAN REVIEW ONLY</strong> — Extracted by {props.modelId}.
      Model Made Clinical Decision: FALSE. Must be reviewed, modified, and signed with Ed25519
      by a verified clinician before issuance.
      {typeof props.costKobo === "number" ? ` [AI Cost: ₦${(props.costKobo / 100).toFixed(2)}]` : ""}
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
        border: `1px solid ${LW_DESIGN_TOKENS.colors.clinicalEmerald}`,
        color: "#115E59",
        padding: "14px",
        borderRadius: LW_DESIGN_TOKENS.radius.md,
        fontSize: "13px",
      }}
    >
      <div
        style={{
          fontWeight: 800,
          color: LW_DESIGN_TOKENS.colors.clinicalEmerald,
          display: "flex",
          alignItems: "center",
          gap: "6px",
          marginBottom: "4px",
        }}
      >
        <span>✓</span> CLINICIAN SIGNED & IMMUTABLE RECORD (Ed25519 Cryptographic Proof)
      </div>
      <div>
        Attending Doctor: <strong>{props.signerName}</strong> (Medical Licence: {props.mdcnLicence})
      </div>
      <div style={{ color: "#0F766E", marginTop: "2px" }}>Signed at: {props.signedAtIso}</div>
      <div
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: "11px",
          marginTop: "6px",
          padding: "4px 8px",
          backgroundColor: "#CCFBF1",
          borderRadius: "4px",
          wordBreak: "break-all",
        }}
      >
        SHA-256: {props.documentSha256}
      </div>
    </div>
  );
}
