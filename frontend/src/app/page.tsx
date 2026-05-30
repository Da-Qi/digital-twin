"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkOnboarding = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/questionnaire/status`
        );
        const data = await res.json();
        router.replace(data.completed ? "/chat" : "/onboarding");
      } catch {
        // If backend not reachable, go to onboarding
        router.replace("/onboarding");
      } finally {
        setChecking(false);
      }
    };
    checkOnboarding();
  }, [router]);

  return (
    <div className="h-screen flex items-center justify-center bg-white dark:bg-gray-900">
      <div className="text-center">
        <div className="animate-spin text-2xl mb-3">⚡</div>
        <p className="text-sm text-gray-400">Initializing digital twin...</p>
      </div>
    </div>
  );
}
