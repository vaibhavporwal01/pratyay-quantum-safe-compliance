import { cn } from "@/lib/cn";
import { Icon, type IconName } from "./icons";

export type StatusKind = "pass" | "fail" | "flagged" | "referred" | "contested" | "pending";

const spec: Record<StatusKind, { label: string; icon: IconName; box: string; text: string }> = {
  pass: { label: "Pass", icon: "check", box: "bg-pass-bg border-pass border-solid", text: "text-pass" },
  fail: { label: "Fail", icon: "x", box: "bg-fail-bg border-fail border-solid", text: "text-fail" },
  flagged: {
    label: "Flagged",
    icon: "alert-triangle",
    box: "bg-refer-bg border-refer border-solid",
    text: "text-refer",
  },
  referred: { label: "Referred", icon: "user", box: "bg-stamp-bg border-stamp border-solid", text: "text-stamp" },
  contested: {
    label: "Contested",
    icon: "gavel",
    box: "bg-refer-bg border-refer border-dashed",
    text: "text-refer",
  },
  pending: {
    label: "Pending",
    icon: "clock-hour-4",
    box: "bg-paper-2 border-muted border-dashed",
    text: "text-muted",
  },
};

export const STATUS_KINDS = Object.keys(spec) as StatusKind[];

export function Status({
  status,
  label,
  className,
}: {
  status: StatusKind;
  /** Override the visible text. Defaults to the status name. */
  label?: string;
  className?: string;
}) {
  const s = spec[status];
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5", s.text, className)}>
      <span className={cn("flex size-4 shrink-0 items-center justify-center rounded-[2px] border", s.box)}>
        <Icon name={s.icon} size={12} />
      </span>
      <span className="type-label whitespace-nowrap">{label ?? s.label}</span>
    </span>
  );
}
