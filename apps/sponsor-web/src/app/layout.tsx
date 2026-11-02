import React from "react";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "LoveWorld Care — SponsorCare & Institutional Workspace",
  description:
    "Institutional entitlement contracts, restricted care pool settlement, and k-anonymity aggregate reporting (§10.5).",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "SponsorCare",
  },
};

export const viewport: Viewport = {
  themeColor: "#1E3A8A",
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
          backgroundColor: "#F8FAFC",
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
