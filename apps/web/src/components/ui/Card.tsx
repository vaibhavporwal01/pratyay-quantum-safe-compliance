import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({
  eyebrow,
  title,
  tag,
  children,
  className,
  bodyClassName,
}: {
  eyebrow?: string;
  title: string;
  /** Usually a Tag, shown at the right of the head. */
  tag?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className={cn("flex flex-col border border-rule bg-white", className)}>
      <header className="flex items-center gap-3 border-b border-rule-2 px-5 py-3.5">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          {eyebrow ? <p className="type-label text-muted">{eyebrow}</p> : null}
          <h2 id={titleId} className="type-title-s text-ink">
            {title}
          </h2>
        </div>
        {tag}
      </header>
      {children !== undefined ? <div className={cn("px-5 pt-1 pb-4", bodyClassName)}>{children}</div> : null}
    </section>
  );
}
