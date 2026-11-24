"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { OrDivider } from "@/components/auth/OrDivider";
import { SHOW_TEST_ACCOUNTS, TestAccounts, type TestAccount } from "@/components/auth/TestAccounts";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/icons";
import { homeFor, requestOtp, verifyOtp } from "@/lib/api/auth";
import { checkCode, checkMobile, normaliseMobile } from "@/lib/validation";

const BORROWER_ACCOUNTS: TestAccount[] = [{ name: "Rekha K.", role: "Borrower", value: "98765 00417" }];

type Sent = { otpId: string; resendAt: number };
type Errors = { mobile?: string; code?: string; form?: string };

function useSecondsUntil(target: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (target === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [target]);
  return target === null ? 0 : Math.max(0, Math.ceil((target - now) / 1000));
}

export function SignUpForm() {
  const router = useRouter();
  const [mobile, setMobile] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const resendIn = useSecondsUntil(sent?.resendAt ?? null);

  async function sendCode() {
    const problem = checkMobile(mobile);
    setErrors({ mobile: problem ?? undefined });
    if (problem) {
      document.getElementById("sign-up-mobile")?.focus();
      return false;
    }
    setBusy(true);
    const res = await requestOtp({ mobile: normaliseMobile(mobile)! });
    setBusy(false);
    if (!res.ok) {
      setErrors({ form: res.error.message });
      return false;
    }
    setSent({ otpId: res.data.otp_id, resendAt: Date.now() + res.data.resend_after_seconds * 1000 });
    setCode("");
    return true;
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!sent) {
      if (await sendCode()) window.setTimeout(() => document.getElementById("sign-up-code")?.focus(), 0);
      return;
    }
    const problem = checkCode(code);
    setErrors({ code: problem ?? undefined });
    if (problem) {
      document.getElementById("sign-up-code")?.focus();
      return;
    }
    setBusy(true);
    const res = await verifyOtp({ otp_id: sent.otpId, code });
    if (!res.ok) {
      setBusy(false);
      setErrors({ code: res.error.message });
      document.getElementById("sign-up-code")?.focus();
      return;
    }
    router.push(homeFor(res.data.user.role));
  }

  function fillAccount(a: TestAccount) {
    setMobile(a.value);
    setSent(null);
    setErrors({});
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
      <Field
        id="sign-up-mobile"
        label="1 · Mobile number"
        type="tel"
        inputMode="tel"
        autoComplete="tel-national"
        placeholder="98765 43210"
        value={mobile}
        onChange={(e) => {
          setMobile(e.target.value);
          // A new number needs a new code.
          if (sent) setSent(null);
        }}
        error={errors.mobile}
      />
      {sent ? (
        <>
          <Field
            id="sign-up-code"
            label="2 · One-time code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            hint="Sent by SMS to the number above."
            error={errors.code}
          />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => void sendCode()}
              disabled={resendIn > 0 || busy}
              className="type-small-medium text-stamp hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"
            >
              {resendIn > 0 ? `Resend code in 0:${String(resendIn).padStart(2, "0")}` : "Resend code"}
            </button>
          </div>
        </>
      ) : null}
      {errors.form ? (
        <p role="alert" className="type-small text-fail">
          {errors.form}
        </p>
      ) : null}
      <Button type="submit" size="l" className="w-full" disabled={busy} icon={<Icon name="arrow-right" />}>
        {sent ? (busy ? "Verifying" : "Verify and continue") : busy ? "Sending code" : "Send code"}
      </Button>
      <OrDivider />
      <Button href="/sign-in" variant="secondary" size="l" className="w-full" icon={<Icon name="arrow-right" />}>
        Staff? Sign in with email
      </Button>
      {SHOW_TEST_ACCOUNTS ? (
        <TestAccounts title="Quick sign-in · test account" accounts={BORROWER_ACCOUNTS} onUse={fillAccount} />
      ) : null}
    </form>
  );
}
