/**
 * LoveWorld Care — Clinical & Brand Design Tokens (§4 & §21.6, ADR-0006)
 * WCAG 2.2 AA contrast validated palette & offline emergency directory.
 */

export const LW_DESIGN_TOKENS = {
  colors: {
    royalNavy: "#0B1F3A",
    royalNavyLight: "#16335B",
    warmGold: "#C89D3C",
    warmGoldSoft: "#FDF8EC",
    clinicalEmerald: "#0F766E",
    clinicalEmeraldSoft: "#F0FDFA",
    emergencyCrimson: "#B91C1C",
    emergencyCrimsonSoft: "#FEF2F2",
    warningAmber: "#B45309",
    warningAmberSoft: "#FFFBEB",
    surfaceSlate: "#F8FAFC",
    surfaceCard: "#FFFFFF",
    borderSlate: "#E2E8F0",
    borderSubtle: "#CBD5E1",
    textPrimary: "#0F172A",
    textSecondary: "#334155",
    textMuted: "#64748B",
  },
  typography: {
    fontFamily:
      "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    sizes: {
      xs: "12px",
      sm: "14px",
      base: "16px",
      lg: "18px",
      xl: "20px",
      xxl: "24px",
      display: "30px",
    },
  },
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "12px",
    lg: "16px",
    xl: "24px",
    xxl: "32px",
  },
  radius: {
    sm: "4px",
    md: "8px",
    lg: "12px",
    full: "9999px",
  },
  touchTarget: {
    minHeightPx: 44,
    minWidthPx: 44,
  },
} as const;

export interface AppTheme {
  readonly id: "patient" | "clinician" | "command" | "sponsor";
  readonly name: string;
  readonly primaryColor: string;
  readonly primaryHover: string;
  readonly accentColor: string;
  readonly background: string;
  readonly cardBackground: string;
  readonly border: string;
  readonly textPrimary: string;
  readonly textSecondary: string;
  readonly isDark: boolean;
}

export const APP_THEMES: Record<"patient" | "clinician" | "command" | "sponsor", AppTheme> = {
  patient: {
    id: "patient",
    name: "Patient Portal (DoctorNow & Health Navigator)",
    primaryColor: "#0B1F3A",
    primaryHover: "#16335B",
    accentColor: "#C89D3C",
    background: "#F8FAFC",
    cardBackground: "#FFFFFF",
    border: "#E2E8F0",
    textPrimary: "#0F172A",
    textSecondary: "#334155",
    isDark: false,
  },
  clinician: {
    id: "clinician",
    name: "Clinician Workspace",
    primaryColor: "#0F766E",
    primaryHover: "#115E59",
    accentColor: "#C89D3C",
    background: "#F1F5F9",
    cardBackground: "#FFFFFF",
    border: "#CBD5E1",
    textPrimary: "#0F172A",
    textSecondary: "#334155",
    isDark: false,
  },
  command: {
    id: "command",
    name: "Care Command Console",
    primaryColor: "#0B1F3A",
    primaryHover: "#1E293B",
    accentColor: "#C89D3C",
    background: "#0F172A",
    cardBackground: "#1E293B",
    border: "#334155",
    textPrimary: "#F8FAFC",
    textSecondary: "#94A3B8",
    isDark: true,
  },
  sponsor: {
    id: "sponsor",
    name: "SponsorCare & Institutional Pools",
    primaryColor: "#1E3A8A",
    primaryHover: "#1E40AF",
    accentColor: "#C89D3C",
    background: "#F8FAFC",
    cardBackground: "#FFFFFF",
    border: "#E2E8F0",
    textPrimary: "#0F172A",
    textSecondary: "#334155",
    isDark: false,
  },
};

export interface OfflineEmergencyContact {
  readonly region: string;
  readonly label: string;
  readonly phone: string;
}

/**
 * §1.4 & AT-11: Embedded offline emergency contacts so urgent safety guidance
 * functions even if the network, API, payment gateway, or AI service is completely unreachable.
 */
export const OFFLINE_EMERGENCY_CONTACTS_NG: readonly OfflineEmergencyContact[] = [
  {
    region: "Nigeria (National Toll-Free)",
    label: "National Emergency Response (Toll-Free)",
    phone: "112",
  },
  {
    region: "Lagos State",
    label: "LASEMA / LASAMBUS Emergency Command",
    phone: "767",
  },
  {
    region: "LoveWorld Medical Centre",
    label: "Facility Reception (Physical Facility Inquiries Only — Not Ambulance Dispatch)",
    phone: "+234-1-888-0000",
  },
];
