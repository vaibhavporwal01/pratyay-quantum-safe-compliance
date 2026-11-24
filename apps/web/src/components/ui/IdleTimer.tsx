"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons";

/** 872 -> "14:32". Negative values clamp to "00:00". */
export function formatRemaining(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

const ACTIVITY = ["pointerdown", "keydown", "scroll", "wheel", "touchstart"] as const;
const WARN_AT = 60;

/**
 * Counts down to an automatic sign-out and restarts on any activity.
 * On expiry it navigates to `signOutHref`; the sign-out itself is handled there.
 */
export function IdleTimer({
  idleSeconds = 900,
  signOutHref = "/sign-in",
}: {
  idleSeconds?: number;
  signOutHref?: string;
}) {
  const router = useRouter();
  const [remaining, setRemaining] = useState(idleSeconds);
  const deadline = useRef<number | null>(null);

  useEffect(() => {
    deadline.current = Date.now() + idleSeconds * 1000;
    const reset = () => {
      deadline.current = Date.now() + idleSeconds * 1000;
    };
    for (const e of ACTIVITY) window.addEventListener(e, reset, { passive: true });

    const tick = window.setInterval(() => {
      const left = Math.ceil(((deadline.current ?? 0) - Date.now()) / 1000);
      setRemaining(Math.max(0, left));
      if (left <= 0) {
        window.clearInterval(tick);
        router.push(signOutHref);
      }
    }, 1000);

    return () => {
      window.clearInterval(tick);
      for (const e of ACTIVITY) window.removeEventListener(e, reset);
    };
  }, [idleSeconds, signOutHref, router]);

  return (
    <span className="flex shrink-0 items-center gap-1.5 text-ink-2">
      <Icon name="clock-hour-4" size={16} />
      <span className="type-mono whitespace-nowrap" aria-hidden>
        Idle sign-out in {formatRemaining(remaining)}
      </span>
      <span className="sr-only" role="status" aria-live="polite">
        {remaining <= WARN_AT && remaining > 0
          ? `You will be signed out in ${remaining} seconds unless you continue working.`
          : ""}
      </span>
    </span>
  );
}
