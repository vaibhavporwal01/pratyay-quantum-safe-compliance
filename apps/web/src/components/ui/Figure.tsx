import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Figure({
  label,
  value,
  note,
  className,
}: {
  label: string;
  value: ReactNode;
  note?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1 px-5 py-4", className)}>
      <p className="type-label text-muted">{label}</p>
      <p className="type-numeral-m whitespace-nowrap text-ink">{value}</p>
      {note ? <p className="type-caption text-ink-2">{note}</p> : null}
    </div>
  );
}

/** A row of figures in one white box, divided by hairlines (Officer overview). */
export function Figures({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        // Side by side from 640px; stacked below, divided by hairlines either way.
        "flex flex-col border border-rule bg-white sm:flex-row [&>*]:min-w-0 [&>*]:flex-1 [&>*:not(:last-child)]:border-b [&>*:not(:last-child)]:border-rule-2 sm:[&>*:not(:last-child)]:border-r sm:[&>*:not(:last-child)]:border-b-0",
        className,
      )}
    >
      {children}
    </div>
  );
}
