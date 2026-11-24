import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/ui/Logo";

export type ContextLine = { label: string; value: string };

function ContextLedger({ lines }: { lines: ContextLine[] }) {
  return (
    <dl className="flex w-full flex-col border-t border-ink pt-2">
      {lines.map((l) => (
        <div key={l.label} className="flex items-center gap-3.5 border-b border-rule-2 py-3">
          <dt className="shrink-0 type-body-medium text-ink">{l.label}</dt>
          <span aria-hidden className="leader" />
          <dd className="shrink-0 type-mono text-ink-2">{l.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SmallPrint({ className }: { className?: string }) {
  return (
    <div className={`flex flex-col gap-1 type-caption text-muted ${className ?? ""}`}>
      <p>Academic prototype · Gautam Buddha University</p>
      <p>Not affiliated with RBI, NPCI, MFIN or any lender.</p>
    </div>
  );
}

/**
 * Sign in, verify and sign-up share this layout (Dec v1 frames 75:11033,
 * 75:11111, 82:11270). From 1280px: context panel on the left, form card on
 * the right. Below that (Figma "2 Web tablet and mobile", 24:581 and 24:679):
 * a logo bar, the card, then the ledger lines and small print.
 */
export function AuthLayout({
  eyebrow,
  title,
  intro,
  lines,
  children,
}: {
  eyebrow: string;
  title: string;
  intro: string;
  lines: ContextLine[];
  /** The form card. */
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-paper xl:flex-row">
      <aside className="hidden w-[640px] shrink-0 flex-col justify-between border-r border-rule bg-paper-2 px-16 pt-12 pb-10 xl:flex">
        <Link href="/" className="self-start">
          <Logo />
        </Link>
        <div className="flex flex-col gap-5">
          <p className="type-label text-muted">{eyebrow}</p>
          <p className="type-title-xl text-ink">{title}</p>
          <p className="type-body-l text-ink-2">{intro}</p>
          <ContextLedger lines={lines} />
        </div>
        <SmallPrint />
      </aside>

      <header className="flex h-16 shrink-0 items-center border-b border-ink bg-paper-2 px-5 md:px-10 xl:hidden">
        <Link href="/">
          <Logo />
        </Link>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-5 py-6 md:px-10 md:py-14 xl:px-20 xl:py-12">
        <div className="flex w-full max-w-[460px] flex-col gap-6 xl:max-w-[448px]">
          {children}
          <div className="flex flex-col gap-6 xl:hidden">
            <ContextLedger lines={lines} />
            <SmallPrint className="items-center text-center" />
          </div>
        </div>
      </main>
    </div>
  );
}

export function FormCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={`flex w-full flex-col gap-5 border border-rule bg-white px-5 py-6 sm:px-9 sm:py-8 ${className ?? ""}`}>
      {children}
    </div>
  );
}

export function FormHead({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <>
      <p className="type-label text-muted">{eyebrow}</p>
      <h1 className="type-title-l text-ink">{title}</h1>
      {children}
    </>
  );
}
