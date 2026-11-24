import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Status, type StatusKind } from "./Status";

/**
 * ID, rule, source, dotted leader, value, verdict.
 * On phones the leader is dropped and the verdict sits above the value.
 */
export function LedgerRow({
  id,
  title,
  source,
  value,
  status,
  className,
}: {
  /** Rule ID or a short symbol like "E_max". Empty keeps the column. */
  id?: string;
  title: ReactNode;
  source?: ReactNode;
  value: ReactNode;
  /** Omit for working lines that have no verdict. */
  status?: StatusKind;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3 border-b border-rule-2 py-3 sm:gap-4", className)}>
      <p className="w-14 shrink-0 type-mono-medium text-ink">{id}</p>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-initial sm:shrink">
        <p className="type-body-medium text-ink">{title}</p>
        {source ? <p className="type-caption text-muted">{source}</p> : null}
      </div>
      <span aria-hidden className="leader hidden sm:block" />
      <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center sm:gap-4">
        <p className="order-2 type-mono whitespace-nowrap text-ink sm:order-1">{value}</p>
        {status ? <Status status={status} className="order-1 sm:order-2" /> : null}
      </div>
    </div>
  );
}
