import { useId, type ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/cn";

type FieldProps = Omit<ComponentPropsWithoutRef<"input">, "children"> & {
  /** Visible label, numbered like a paper form, e.g. "1 · Work email". */
  label: string;
  hint?: string;
  /** Error message. When set the field is marked invalid and the hint is replaced. */
  error?: string;
  /** Show the focus style without focus. Only for the style guide. */
  showFocus?: boolean;
  className?: string;
};

export function Field({ label, hint, error, showFocus, id, className, ...input }: FieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const messageId = `${inputId}-message`;
  const message = error ?? hint;

  return (
    <div className={cn("flex w-full flex-col gap-1.5", className)}>
      <label htmlFor={inputId} className="type-label text-ink-2">
        {label}
      </label>
      <div
        data-focus={showFocus || undefined}
        className={cn(
          "flex h-11 w-full items-center rounded-[2px] border bg-white px-3",
          // Figma: 1px rule at rest, 1.5px stamp on focus, 1.5px fail on error.
          // The extra half pixel is an inset shadow so the box never shifts.
          error
            ? "border-fail shadow-[inset_0_0_0_0.5px_var(--fail)]"
            : "border-rule focus-within:border-stamp focus-within:shadow-[inset_0_0_0_0.5px_var(--stamp)] data-[focus]:border-stamp data-[focus]:shadow-[inset_0_0_0_0.5px_var(--stamp)]",
        )}
      >
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? messageId : undefined}
          className="min-w-0 flex-1 bg-transparent text-ink type-body outline-none placeholder:text-muted"
          {...input}
        />
      </div>
      {message ? (
        <p id={messageId} className={cn("type-caption", error ? "text-fail" : "text-muted")}>
          {message}
        </p>
      ) : null}
    </div>
  );
}
