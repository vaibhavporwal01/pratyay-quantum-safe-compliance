"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useSyncExternalStore, type FormEvent } from "react";
import { FormHead } from "@/components/auth/AuthLayout";
import { CodeInput } from "@/components/auth/CodeInput";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/icons";
import { homeFor, MFA_CHALLENGE_KEY, verifyMfa } from "@/lib/api/auth";
import { checkCode, checkRecoveryCode } from "@/lib/validation";

type Challenge = { challenge_id: string; email: string };

const noop = () => () => {};

/** Seconds left in the current 30-second TOTP window. */
export function totpSecondsLeft(nowMs: number, step = 30): number {
  return step - (Math.floor(nowMs / 1000) % step);
}

function useTotpCountdown(): number | null {
  const [left, setLeft] = useState<number | null>(null);
  useEffect(() => {
    const tick = () => setLeft(totpSecondsLeft(Date.now()));
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, 1000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, []);
  return left;
}

export function VerifyForm() {
  const router = useRouter();
  // undefined on the server, null when nothing was handed over by the sign-in page.
  const raw = useSyncExternalStore(
    noop,
    () => sessionStorage.getItem(MFA_CHALLENGE_KEY),
    () => undefined,
  );
  const challenge = useMemo<Challenge | null | undefined>(() => {
    if (raw === undefined) return undefined;
    try {
      return raw ? (JSON.parse(raw) as Challenge) : null;
    } catch {
      return null;
    }
  }, [raw]);

  const [mode, setMode] = useState<"totp" | "recovery">("totp");
  const [code, setCode] = useState("");
  const [recovery, setRecovery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const secondsLeft = useTotpCountdown();

  if (challenge === null) {
    return (
      <>
        <FormHead eyebrow="§ 02 · Verify it is you" title="Start from sign in" />
        <p className="type-small text-ink-2">
          This step follows your email and password. Sign in again to get a new code request.
        </p>
        <Button href="/sign-in" size="l" className="w-full" icon={<Icon name="arrow-right" />}>
          Back to sign in
        </Button>
      </>
    );
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const value = mode === "totp" ? code : recovery.trim();
    const problem = mode === "totp" ? checkCode(value) : checkRecoveryCode(value);
    setError(problem);
    if (problem || !challenge) {
      document.getElementById(mode === "totp" ? "mfa-code" : "mfa-recovery")?.focus();
      return;
    }
    setBusy(true);
    const res = await verifyMfa({ challenge_id: challenge.challenge_id, method: mode, code: value });
    if (!res.ok) {
      setBusy(false);
      setError(res.error.message);
      setCode("");
      document.getElementById(mode === "totp" ? "mfa-code" : "mfa-recovery")?.focus();
      return;
    }
    sessionStorage.removeItem(MFA_CHALLENGE_KEY);
    router.push(homeFor(res.data.user.role));
  }

  function switchMode() {
    setMode((m) => (m === "totp" ? "recovery" : "totp"));
    setError(null);
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
      {mode === "totp" ? (
        <>
          <FormHead eyebrow="§ 02 · Verify it is you" title="Enter the 6-digit code">
            <p className="type-small text-ink-2">
              From the authenticator app linked to{" "}
              <span className="break-all">{challenge?.email ?? "your account"}</span>
            </p>
          </FormHead>
          <CodeInput
            id="mfa-code"
            label="6-digit code from your authenticator app"
            value={code}
            onChange={(v) => {
              setCode(v);
              if (error) setError(null);
            }}
            invalid={Boolean(error)}
            describedBy={error ? "mfa-error" : "mfa-timer"}
            disabled={busy}
          />
          {error ? (
            <p id="mfa-error" role="alert" className="-mt-2 type-caption text-fail">
              {error}
            </p>
          ) : null}
          <p id="mfa-timer" className="flex items-center gap-1.5 type-mono text-muted">
            <Icon name="clock-hour-4" size={14} />
            New code in 0:{String(secondsLeft ?? 30).padStart(2, "0")}
          </p>
        </>
      ) : (
        <>
          <FormHead eyebrow="§ 02 · Verify it is you" title="Enter a recovery code">
            <p className="type-small text-ink-2">Each recovery code works once.</p>
          </FormHead>
          <Field
            id="mfa-recovery"
            label="Recovery code"
            autoComplete="one-time-code"
            autoCapitalize="none"
            spellCheck={false}
            placeholder="ab12-cd34"
            value={recovery}
            onChange={(e) => setRecovery(e.target.value)}
            error={error ?? undefined}
          />
        </>
      )}
      <Button type="submit" size="l" className="w-full" disabled={busy} icon={<Icon name="arrow-right" />}>
        {busy ? "Verifying" : "Verify"}
      </Button>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-rule-2 pt-3 type-small-medium">
        <button type="button" onClick={switchMode} className="text-stamp hover:underline">
          {mode === "totp" ? "Use a recovery code" : "Use the authenticator app"}
        </button>
        <Link href="/sign-in" className="text-ink-2 hover:text-ink">
          Back to sign in
        </Link>
      </div>
    </form>
  );
}
