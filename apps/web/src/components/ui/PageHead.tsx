import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function PageHead({
  eyebrow,
  title,
  subtitle,
  actions,
  className,
}: {
  /** e.g. "§ 01 · Overview · Monday 9 Nov 2026" */
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  /** Buttons, right aligned to the baseline of the block. */
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-end gap-10 border-b-2 border-ink pb-5", className)}>
      <div className="flex min-w-0 flex-1 flex-col gap-2.5">
        {eyebrow ? <p className="type-label text-muted">{eyebrow}</p> : null}
        <h1 className="type-title-xl text-ink">{title}</h1>
        {subtitle ? <p className="type-body-l text-ink-2">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-3">{actions}</div> : null}
    </div>
  );
}
