import React from "react";

export const metadata = {
  title: "LoveWorld Care — Clinician Workspace (DoctorNow · ClinicConnect · SpecialistBridge)",
  description: "Verified medical practitioner workspace for atomic case claiming, consultation, and Ed25519 clinical signing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          backgroundColor: "#F1F5F9",
          color: "#0F172A",
        }}
      >
        {children}
      </body>
    </html>
  );
}
