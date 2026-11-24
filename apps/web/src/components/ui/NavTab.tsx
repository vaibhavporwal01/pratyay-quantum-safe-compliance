import Link from "next/link";
import { cn } from "@/lib/cn";

export type NavTabItem = { href: string; number: string; label: string };

export function NavTab({ href, number, label, active = false }: NavTabItem & { active?: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-12 shrink-0 items-center gap-2 whitespace-nowrap",
        active ? "border-b-2 border-ink" : "hover:text-ink",
      )}
    >
      <span className={cn("type-mono", active ? "text-stamp" : "text-muted")}>{number}</span>
      <span className={cn("type-body-medium", active ? "text-ink" : "text-ink-2")}>{label}</span>
    </Link>
  );
}
