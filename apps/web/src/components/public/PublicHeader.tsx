"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Logo } from "@/components/ui/Logo";
import { OTP_ENABLED } from "@/lib/api/auth";

// With mobile OTP off, borrowers apply after signing in with email.
const APPLY_HREF = OTP_ENABLED ? "/sign-up" : "/sign-in?as=borrower";

const LINKS = [
  { href: "#how", label: "How it decides" },
  { href: "#example", label: "Worked example" },
  { href: "#trust", label: "Trust layer" },
  { href: "#roles", label: "Who uses it" },
  { href: "#team", label: "Team" },
];

/**
 * Landing strip and masthead (Dec v1 75:10781 to 75:10794). From 1024px the
 * section links show inline; below that they move into a menu (tablet and
 * phone frames 23:126 and 23:591).
 */
export function PublicHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header>
      <div className="flex items-center bg-ink px-5 py-[9px] md:px-10">
        <p className="type-label text-paper">
          Academic prototype
          <span className="hidden md:inline"> · B.Tech CSE minor project · Gautam Buddha University</span>
        </p>
      </div>
      <div className="flex h-[64px] items-center gap-9 px-5 md:h-[76px] md:px-10">
        <Link href="/" aria-label="Pratyay home" className="shrink-0">
          <Logo />
        </Link>
        <nav aria-label="Sections" className="hidden items-center gap-9 lg:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="type-body-medium whitespace-nowrap text-ink-2 hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
        <span className="min-w-px flex-1" />
        <div className="hidden items-center gap-3 sm:flex">
          <Button href="/sign-in" variant="secondary">
            Sign in
          </Button>
          <Button href={APPLY_HREF} icon={<Icon name="arrow-right" />}>
            Apply
          </Button>
        </div>
        <button
          type="button"
          className="-mr-2 flex size-10 items-center justify-center text-ink lg:hidden"
          aria-expanded={open}
          aria-controls="public-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <Icon name={open ? "x" : "menu-2"} size={24} />
        </button>
      </div>
      <div aria-hidden className="h-1 border-y border-ink" />
      {open ? (
        <nav id="public-menu" aria-label="Sections" className="border-b border-rule bg-paper-2 px-5 py-2 md:px-10 lg:hidden">
          <ul className="flex flex-col">
            {LINKS.map((l) => (
              <li key={l.href} className="border-b border-rule-2 last:border-b-0">
                <a
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block py-3 type-body-medium text-ink-2 hover:text-ink"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
          <div className="flex flex-col gap-3 py-3 sm:hidden">
            <Button href="/sign-in" variant="secondary" size="l" className="w-full">
              Sign in
            </Button>
            <Button href={APPLY_HREF} size="l" className="w-full" icon={<Icon name="arrow-right" />}>
              Apply
            </Button>
          </div>
        </nav>
      ) : null}
    </header>
  );
}
