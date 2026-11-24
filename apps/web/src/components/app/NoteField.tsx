import { useId } from "react";

/** A multi-line note, styled like Field. */
export function NoteField({
  label,
  value,
  onChange,
  hint,
  error,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
  error?: string;
}) {
  const id = useId();
  return (
    <div className="flex w-full flex-col gap-1.5">
      <label htmlFor={id} className="type-label text-ink-2">
        {label}
      </label>
      <textarea
        id={id}
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? true : undefined}
        className={`w-full rounded-[2px] border bg-white px-3 py-2.5 type-body text-ink outline-none ${error ? "border-fail" : "border-rule focus:border-stamp"}`}
      />
      {error || hint ? <p className={`type-caption ${error ? "text-fail" : "text-muted"}`}>{error ?? hint}</p> : null}
    </div>
  );
}
