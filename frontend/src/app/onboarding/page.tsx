"use client";

import { useRouter } from "next/navigation";
import { QuestionnaireWizard } from "@/components/questionnaire/QuestionnaireWizard";

export default function OnboardingPage() {
  const router = useRouter();

  const handleComplete = () => {
    router.push("/chat");
  };

  return <QuestionnaireWizard onComplete={handleComplete} />;
}
