import React from "react";

export const metadata = {
  title: "LoveWorld Care — Care Command (Directorate, Clinical Governance, Ops & Finance)",
  description:
    "Role-segregated operational, clinical governance, finance maker/checker, and executive unit-economics command console.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          backgroundColor: "#F8FAFC",
          color: "#0F172A",
        }}
      >
        {children}
      </body>
    </html>
  );
}
