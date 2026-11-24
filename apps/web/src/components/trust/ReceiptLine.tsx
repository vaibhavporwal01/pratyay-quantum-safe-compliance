import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type ReceiptTone = "default" | "muted" | "pass" | "fail" | "total";

const valueTone: Record<ReceiptTone, string> = {
  default: "type-mono text-ink",
  muted: "type-mono text-muted",
  pass: "type-mono text-pass",
  fail: "type-mono text-fail",
  total: "type-mono-medium text-ink",
};

export type ReceiptLineData = { label: string; value: ReactNode; tone?: ReceiptTone };

/** Label, dotted leader, value. "total" adds an ink rule above. */
export function ReceiptLine({ label, value, tone = "default", className }: ReceiptLineData & { className?: string }) {
  const total = tone === "total";
  return (
    <div className={cn("flex items-center gap-2", total && "border-t border-ink pt-2", className)}>
      <dt className={cn("shrink-0 whitespace-nowrap", total ? "type-small-medium text-ink" : "type-small text-ink-2")}>
        {label}
      </dt>
      <span aria-hidden className="leader" />
      <dd className={cn("shrink-0 whitespace-nowrap", valueTone[tone])}>{value}</dd>
    </div>
  );
}
