"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Checkbox } from "@/components/auth/Checkbox";
import { OrDivider } from "@/components/auth/OrDivider";
import { SHOW_TEST_ACCOUNTS, TestAccounts, type TestAccount } from "@/components/auth/TestAccounts";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/icons";
import { homeFor, OTP_ENABLED, safeNext, signIn } from "@/lib/api/auth";
import { checkEmail, checkPassword } from "@/lib/validation";

const STAFF_ACCOUNTS: TestAccount[] = [
  { name: "Anita Sharma", role: "Credit officer", value: "anita.sharma@lender-a.in" },
  { name: "Neha Verma", role: "Compliance maker", value: "neha.verma@lender-a.in" },
  { name: "Rahul Mehta", role: "Compliance checker", value: "rahul.mehta@lender-a.in" },
  { name: "Priya Nair", role: "Auditor, read-only", value: "priya.nair@lender-a.in" },
];

type Errors = { email?: string; password?: string; form?: string };

export function SignInForm({
  audience = "staff",
  next: returnTo,
}: {
  audience?: "staff" | "borrower";
  /** Where to go after sign-in (from ?next=); ignored unless it is a path on this site. */
  next?: string | null;
}) {
  const borrower = audience === "borrower";
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const [resetHelp, setResetHelp] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault();

  const normalizedEmail = email.trim().toLowerCase();

  const next: Errors = {
    email: checkEmail(normalizedEmail) ?? undefined,
    password: checkPassword(password) ?? undefined,
  };

  setErrors(next);

  if (next.email || next.password) {
    document
      .getElementById(next.email ? "sign-in-email" : "sign-in-password")
      ?.focus();
    return;
  }

  setBusy(true);
  setErrors({});

  try {
    const res = await signIn({
      email: normalizedEmail,
      password,
    });

    if (!res.ok) {
      setErrors({ form: res.error.message });
      return;
    }

    router.replace(
      safeNext(returnTo) ?? homeFor(res.data.user.role)
    );
    router.refresh();
  } catch (error) {
  console.error("SIGN-IN TEST ERROR:", error);
  setErrors({
    form: "Unable to sign in. Please check your connection and try again.",
  });
} finally {
    setBusy(false);
  }
}

  function fillAccount(a: TestAccount) {
    setEmail(a.value);
    setErrors({});
    document.getElementById("sign-in-password")?.focus();
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
      <Field
        id="sign-in-email"
        label={borrower ? "1 · Email" : "1 · Work email"}
        type="email"
        autoComplete="username"
        placeholder={borrower ? "name@example.in" : "name@lender.in"}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={errors.email}
      />
      <Field
        id="sign-in-password"
        label="2 · Password"
        type={showPassword ? "text" : "password"}
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        hint="At least 12 characters."
        error={errors.password}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Checkbox label="Show password" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)} />
        <button
          type="button"
          aria-expanded={resetHelp}
          aria-controls="reset-help"
          onClick={() => setResetHelp((v) => !v)}
          className="type-small-medium text-stamp hover:underline"
        >
          Forgot password?
        </button>
      </div>
      {resetHelp ? (
        <p id="reset-help" className="-mt-2 type-caption text-ink-2">
          Ask your organisation&apos;s admin to reset it.
        </p>
      ) : null}
      {errors.form ? (
        <p role="alert" className="type-small text-fail">
          {errors.form}
        </p>
      ) : null}
      <Button type="submit" size="l" className="w-full" disabled={busy} icon={<Icon name="arrow-right" />}>
        {busy ? "Signing in" : "Continue"}
      </Button>
      {borrower ? null : (
        <>
          <OrDivider />
          {OTP_ENABLED ? (
            <Button href="/sign-up" variant="secondary" size="l" className="w-full" icon={<Icon name="phone" />}>
              Borrower? Use your mobile number
            </Button>
          ) : (
            <Button href="/sign-in?as=borrower" variant="secondary" size="l" className="w-full" icon={<Icon name="user" />}>
              Borrower? Sign in with your email
            </Button>
          )}
        </>
      )}
      {SHOW_TEST_ACCOUNTS && !borrower ? (
        <TestAccounts title="Quick sign-in · test accounts" accounts={STAFF_ACCOUNTS} onUse={fillAccount} />
      ) : null}
    </form>
  );
}
