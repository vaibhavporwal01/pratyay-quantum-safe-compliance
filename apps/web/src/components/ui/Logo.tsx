import { cn } from "@/lib/cn";

export function Logo({ tone = "default", className }: { tone?: "default" | "inverse"; className?: string }) {
  const inverse = tone === "inverse";
  return (
    <span
      className={cn("inline-flex shrink-0 items-center gap-2.5", inverse && "bg-ink p-3", className)}
      aria-label="Pratyay"
      role="img"
    >
      <span
        aria-hidden
        className={cn(
          "flex size-[30px] shrink-0 items-center justify-center rounded-full border-[1.5px] type-title-s",
          inverse ? "border-paper text-paper" : "border-stamp text-stamp",
        )}
      >
        P
      </span>
      <span aria-hidden className={cn("type-title-m whitespace-nowrap", inverse ? "text-paper" : "text-ink")}>
        Pratyay
      </span>
    </span>
  );
}
