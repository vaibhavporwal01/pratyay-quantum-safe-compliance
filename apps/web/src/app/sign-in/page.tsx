import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthLayout, FormCard } from "@/components/auth/AuthLayout";
import { SIGN_IN_LINES } from "@/components/auth/lines";
import { OTP_ENABLED } from "@/lib/api/auth";
import { SignInCard } from "./SignInCard";

export const metadata: Metadata = { title: "Sign in · Pratyay" };

export default function SignInPage() {
  return (
    <AuthLayout
      eyebrow="§ Sign in"
      title="One sign-in per role. Every action goes on the record."
      intro={
        OTP_ENABLED
          ? "Officers, compliance staff and auditors sign in with email, password and an authenticator code. Borrowers use their mobile number and a one-time code."
          : "Staff and borrowers sign in with their email and password. Five wrong attempts lock the account for 15 minutes."
      }
      lines={SIGN_IN_LINES}
    >
      <FormCard>
        <Suspense>
          <SignInCard />
        </Suspense>
      </FormCard>
    </AuthLayout>
  );
}
