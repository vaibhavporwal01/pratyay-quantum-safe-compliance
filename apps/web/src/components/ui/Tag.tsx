import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type TagTone = "neutral" | "stamp" | "pass" | "fail" | "refer" | "ink";

const tones: Record<TagTone, string> = {
  neutral: "bg-paper-2 border border-rule text-ink-2",
  stamp: "bg-stamp-bg text-stamp",
  pass: "bg-pass-bg text-pass",
  fail: "bg-fail-bg text-fail",
  refer: "bg-refer-bg text-refer",
  ink: "bg-ink text-paper",
};

export function Tag({
  tone = "neutral",
  children,
  className,
}: {
  tone?: TagTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-[2px] px-[7px] py-[3px] whitespace-nowrap type-label",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
