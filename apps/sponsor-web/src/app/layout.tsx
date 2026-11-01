import React from "react";

export const metadata = {
  title: "LoveWorld Care — SponsorCare & Institutional Access Workspace",
  description:
    "Aggregate programme funding, Espees/Paystack/Flutterwave pool replenishment, and k>=5 privacy-safe utilisation reporting.",
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
