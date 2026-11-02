import React from "react";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "LoveWorld Care — Patient Portal (DoctorNow & Health Navigator)",
  description:
    "Clinically governed remote healthcare access. Licensed Nigerian doctors make all clinical decisions. DoctorNow on-demand and scheduled consultations.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "LoveWorld Care",
  },
};

export const viewport: Viewport = {
  themeColor: "#0B1F3A",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
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
