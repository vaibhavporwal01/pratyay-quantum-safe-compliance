import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Status, type StatusKind } from "./Status";

/** ID, rule, source, dotted leader, value, verdict. */
export function LedgerRow({
  id,
  title,
  source,
  value,
  status,
  className,
}: {
  id: string;
  title: ReactNode;
  source?: ReactNode;
  value: ReactNode;
  status: StatusKind;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-4 border-b border-rule-2 py-3", className)}>
      <p className="w-14 shrink-0 type-mono-medium text-ink">{id}</p>
      <div className="flex min-w-0 shrink flex-col gap-0.5">
        <p className="type-body-medium text-ink">{title}</p>
        {source ? <p className="type-caption text-muted">{source}</p> : null}
      </div>
      <span aria-hidden className="leader" />
      <p className="shrink-0 type-mono whitespace-nowrap text-ink">{value}</p>
      <Status status={status} />
    </div>
  );
}
