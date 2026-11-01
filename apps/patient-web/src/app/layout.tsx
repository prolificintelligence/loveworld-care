import React from "react";

export const metadata = {
  title: "LoveWorld Care — Patient Portal (DoctorNow & Health Navigator)",
  description:
    "Clinically governed remote healthcare access. Licensed doctors make all clinical decisions.",
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
