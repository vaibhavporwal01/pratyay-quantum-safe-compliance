"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";

/**
 * Six boxes from the MFA frame, backed by one real input so paste, autofill
 * (autocomplete="one-time-code") and screen readers all work.
 */
export function CodeInput({
  id,
  label,
  value,
  onChange,
  length = 6,
  invalid = false,
  describedBy,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  length?: number;
  invalid?: boolean;
  describedBy?: string;
  disabled?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const active = Math.min(value.length, length - 1);

  return (
    <div className="relative flex w-full gap-2.5">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      {Array.from({ length }, (_, i) => {
        const isActive = focused && i === active && value.length < length;
        return (
          <span
            key={i}
            aria-hidden
            className={cn(
              "flex h-[60px] min-w-0 flex-1 items-center justify-center rounded-[2px] bg-white type-numeral-m text-ink",
              invalid
                ? "border-[1.5px] border-fail"
                : isActive
                  ? "border-[1.5px] border-stamp"
                  : "border border-rule",
            )}
          >
            {value[i] ?? (isActive ? <span className="h-[26px] w-[1.5px] animate-pulse bg-stamp" /> : null)}
          </span>
        );
      })}
      <input
        id={id}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, length))}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]*"
        maxLength={length}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        className="absolute inset-0 h-full w-full cursor-text opacity-0"
      />
    </div>
  );
}
