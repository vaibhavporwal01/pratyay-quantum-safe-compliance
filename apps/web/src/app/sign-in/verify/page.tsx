import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { OTP_ENABLED } from "@/lib/api/auth";
import { AuthLayout, FormCard } from "@/components/auth/AuthLayout";
import { VERIFY_LINES } from "@/components/auth/lines";
import { VerifyForm } from "./VerifyForm";

export const metadata: Metadata = { title: "Verify it is you · Pratyay" };

export default function VerifyPage() {
  // The authenticator step is off until the identity owner wires it (NEXT_PUBLIC_ENABLE_OTP).
  if (!OTP_ENABLED) redirect("/sign-in");
  return (
    <AuthLayout
      eyebrow="§ Second step"
      title="A second step, every time."
      intro="Staff accounts need a code from an authenticator app. A stolen password alone opens nothing."
      lines={VERIFY_LINES}
    >
      <FormCard>
        <VerifyForm />
      </FormCard>
    </AuthLayout>
  );
}
