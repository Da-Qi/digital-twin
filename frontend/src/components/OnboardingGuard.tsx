"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export default function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (pathname === "/onboarding") {
      setChecking(false);
      return;
    }

    const check = async () => {
      try {
        const res = await fetch(
          `${
            process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
          }/questionnaire/status`
        );
        const data = await res.json();
        if (!data.completed) {
          router.replace("/onboarding");
        } else {
          setChecking(false);
        }
      } catch {
        router.replace("/onboarding");
      }
    };
    check();
  }, [router, pathname]);

  if (checking) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#fff",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "24px", marginBottom: "12px" }}>⚡</div>
          <p style={{ fontSize: "14px", color: "#999" }}>Initializing digital twin...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
