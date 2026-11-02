import React from "react";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "LoveWorld Care — Clinician Workspace (DoctorNow · ClinicConnect · SpecialistBridge)",
  description:
    "Verified medical practitioner workspace for atomic case claiming, LiveKit WebRTC consultations, and Ed25519 clinical signing.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "LW Clinician",
  },
};

export const viewport: Viewport = {
  themeColor: "#0F766E",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          backgroundColor: "#F1F5F9",
          color: "#0F172A",
          minHeight: "100vh",
          WebkitFontSmoothing: "antialiased",
        }}
      >
        {children}
      </body>
    </html>
  );
}
