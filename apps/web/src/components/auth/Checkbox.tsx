import type { ComponentPropsWithoutRef } from "react";
import { Icon } from "@/components/ui/icons";

export function Checkbox({ label, ...input }: { label: string } & Omit<ComponentPropsWithoutRef<"input">, "type">) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 type-small text-ink-2">
      <span className="relative flex size-4 shrink-0">
        <input
          type="checkbox"
          className="peer size-4 cursor-pointer appearance-none rounded-[2px] border border-rule bg-white checked:border-stamp checked:bg-stamp"
          {...input}
        />
        <Icon
          name="check"
          size={12}
          className="pointer-events-none absolute top-0.5 left-0.5 hidden text-white peer-checked:block"
        />
      </span>
      {label}
    </label>
  );
}
