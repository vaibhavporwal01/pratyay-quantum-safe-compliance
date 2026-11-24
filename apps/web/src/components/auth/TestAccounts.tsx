"use client";

import { Avatar } from "@/components/ui/Avatar";

export type TestAccount = { name: string; role: string; value: string };

/**
 * Test accounts are shown only when NEXT_PUBLIC_SHOW_TEST_ACCOUNTS is "true".
 * Leave it unset in production.
 */
export const SHOW_TEST_ACCOUNTS = process.env.NEXT_PUBLIC_SHOW_TEST_ACCOUNTS === "true";

export function TestAccounts({
  title,
  accounts,
  onUse,
}: {
  title: string;
  accounts: TestAccount[];
  onUse: (account: TestAccount) => void;
}) {
  return (
    <section
      aria-label={title}
      className="flex w-full flex-col gap-0.5 rounded-[2px] border border-dashed border-rule bg-paper-2 px-3.5 py-3"
    >
      <p className="type-label text-refer">{title}</p>
      <ul>
        {accounts.map((a) => (
          <li key={a.value} className="flex items-center gap-2.5 py-1.5">
            <Avatar name={a.name} />
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate type-small-medium text-ink">{a.name}</span>
              <span className="truncate type-caption text-muted">{a.role}</span>
            </span>
            <button
              type="button"
              onClick={() => onUse(a)}
              aria-label={`Use ${a.name}, ${a.role}`}
              className="shrink-0 type-small-medium text-stamp hover:underline"
            >
              Use
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
