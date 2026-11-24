import { cn } from "@/lib/cn";

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? "") : "";
  return (first + last).toUpperCase();
}

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      role="img"
      aria-label={name}
      title={name}
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full bg-stamp-bg text-stamp type-mono-medium",
        className,
      )}
    >
      <span aria-hidden>{initials(name)}</span>
    </span>
  );
}
