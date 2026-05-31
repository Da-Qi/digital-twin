import type { Metadata } from "next";
import "./globals.css";
import OnboardingGuard from "@/components/OnboardingGuard";

export const metadata: Metadata = {
  title: "Digital Twin",
  description: "Your personal AI digital twin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen overflow-hidden">
        <OnboardingGuard>{children}</OnboardingGuard>
      </body>
    </html>
  );
}
