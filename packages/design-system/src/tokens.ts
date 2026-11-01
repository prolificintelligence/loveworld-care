/**
 * LoveWorld Care — Clinical & Brand Design Tokens (§4 & §21.6)
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
    textPrimary: "#0F172A",
    textSecondary: "#334155",
  },
  touchTarget: {
    minHeightPx: 44,
    minWidthPx: 44,
  },
} as const;

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
    label: "National Emergency Response",
    phone: "112",
  },
  {
    region: "Lagos State",
    label: "LASEMA / LASAMBUS Emergency",
    phone: "767",
  },
  {
    region: "LoveWorld Medical Centre",
    label: "Facility Reception (In-Person Inquiry Only — Not Ambulance Dispatch)",
    phone: "+234-1-888-0000",
  },
];
