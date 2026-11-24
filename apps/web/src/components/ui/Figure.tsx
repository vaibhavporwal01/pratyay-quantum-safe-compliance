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
        "flex border border-rule bg-white [&>*]:flex-1 [&>*]:min-w-0 [&>*:not(:last-child)]:border-r [&>*:not(:last-child)]:border-rule-2",
        className,
      )}
    >
      {children}
    </div>
  );
}
