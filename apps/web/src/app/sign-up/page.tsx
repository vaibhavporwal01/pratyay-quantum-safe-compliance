import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { OTP_ENABLED } from "@/lib/api/auth";
import { AuthLayout, FormCard, FormHead } from "@/components/auth/AuthLayout";
import { AudienceSwitch } from "@/components/auth/AudienceSwitch";
import { SIGN_IN_LINES } from "@/components/auth/lines";
import { SignUpForm } from "./SignUpForm";

export const metadata: Metadata = { title: "Apply · Pratyay" };

export default function SignUpPage() {
  // Mobile OTP sign-up is off until the identity owner wires it (NEXT_PUBLIC_ENABLE_OTP).
  if (!OTP_ENABLED) redirect("/sign-in?as=borrower");
  return (
    <AuthLayout
      eyebrow="§ Borrowers"
      title="Apply in about ten minutes, from your phone or a laptop."
      intro="Borrowers sign in with a mobile number and a one-time code. You can save your application and come back to it."
      lines={SIGN_IN_LINES}
    >
      <FormCard>
        <FormHead eyebrow="§ 01 · Create your account" title="Apply to Lender A" />
        <AudienceSwitch current="borrower" />
        <SignUpForm />
      </FormCard>
    </AuthLayout>
  );
}
