import type { Metadata } from "next";
import { AuthLayout, FormCard, FormHead } from "@/components/auth/AuthLayout";
import { AudienceSwitch } from "@/components/auth/AudienceSwitch";
import { SIGN_IN_LINES } from "@/components/auth/lines";
import { SignInForm } from "./SignInForm";

export const metadata: Metadata = { title: "Sign in · Pratyay" };


export default function SignInPage() {
  return (
    <AuthLayout
      eyebrow="§ Sign in"
      title="One sign-in per role. Every action goes on the record."
      intro="Officers, compliance staff and auditors sign in with email, password and an authenticator code. Borrowers use their mobile number and a one-time code."
      lines={SIGN_IN_LINES}
    >
      <FormCard>
        <FormHead eyebrow="§ 01 · Sign in" title="Sign in to Lender A" />
        <AudienceSwitch current="staff" />
        <SignInForm />
      </FormCard>
    </AuthLayout>
  );
}
