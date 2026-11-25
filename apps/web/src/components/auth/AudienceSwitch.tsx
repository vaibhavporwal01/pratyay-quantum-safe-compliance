import Link from "next/link";
import { OTP_ENABLED } from "@/lib/api/auth";
import { cn } from "@/lib/cn";

/** Staff / Borrower switch at the top of the sign-in and sign-up cards. */
export function AudienceSwitch({ current }: { current: "staff" | "borrower" }) {
  const items = [
    { key: "staff", label: "Staff", href: "/sign-in" },
    { key: "borrower", label: "Borrower", href: OTP_ENABLED ? "/sign-up" : "/sign-in?as=borrower" },
  ] as const;
  return (
    <nav aria-label="Who is signing in" className="flex w-full rounded-[4px] border border-rule bg-paper-2 p-[3px]">
      {items.map((i) => {
        const active = i.key === current;
        return (
          <Link
            key={i.key}
            href={i.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex min-w-0 flex-1 items-center justify-center rounded-[3px] border px-3.5 py-[7px] type-small-medium",
              active ? "border-rule bg-white text-ink" : "border-transparent text-muted hover:text-ink",
            )}
          >
            {i.label}
          </Link>
        );
      })}
    </nav>
  );
}
