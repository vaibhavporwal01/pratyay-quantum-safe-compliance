import type { Metadata } from "next";
import { AuthLayout, FormCard } from "@/components/auth/AuthLayout";
import { VERIFY_LINES } from "@/components/auth/lines";
import { VerifyForm } from "./VerifyForm";

export const metadata: Metadata = { title: "Verify it is you · Pratyay" };

export default function VerifyPage() {
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
