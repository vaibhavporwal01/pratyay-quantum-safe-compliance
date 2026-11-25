"use client";

import { useSearchParams } from "next/navigation";
import { FormHead } from "@/components/auth/AuthLayout";
import { AudienceSwitch } from "@/components/auth/AudienceSwitch";
import { SignInForm } from "./SignInForm";

/** Staff or Borrower tab (?as=borrower) and the page to return to (?next=). */
export function SignInCard() {
  const params = useSearchParams();
  const audience = params.get("as") === "borrower" ? "borrower" : "staff";
  return (
    <>
      <FormHead eyebrow="§ 01 · Sign in" title="Sign in to Lender A" />
      <AudienceSwitch current={audience} />
      <SignInForm key={audience} audience={audience} next={params.get("next")} />
    </>
  );
}
