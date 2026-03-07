import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobScraper — AI-Powered Job Dashboard",
  description:
    "Real-time job board for Data Engineers, AI Engineers, ML Engineers and more. Powered by NVIDIA NIM.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen text-slate-100 antialiased" style={{ background: "#060b18" }}>
        {children}
      </body>
    </html>
  );
}
