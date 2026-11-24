import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import { IdleTimer } from "./IdleTimer";
import { Icon } from "./icons";
import { Logo } from "./Logo";

export type MastheadUser = { name: string; role: string };

export function Masthead({
  breadcrumb,
  user,
  idleSeconds,
  tag,
}: {
  /** e.g. ["Lender A", "Overview"], shown as "LENDER A / OVERVIEW". */
  breadcrumb: string[];
  user?: MastheadUser;
  /** Seconds until idle sign-out. Omit to hide the timer (public pages). */
  idleSeconds?: number;
  /** Optional tag before the timer, hidden on most December screens. */
  tag?: ReactNode;
}) {
  return (
    <header className="flex h-16 items-center gap-5 bg-paper-2 px-10">
      <Logo />
      <span aria-hidden className="h-6 w-px shrink-0 bg-rule" />
      <nav aria-label="Breadcrumb" className="min-w-0">
        <ol className="flex type-label whitespace-nowrap text-muted">
          {breadcrumb.map((part, i) => (
            <li key={`${i}-${part}`} aria-current={i === breadcrumb.length - 1 ? "page" : undefined}>
              {i > 0 ? <span aria-hidden>&nbsp;/&nbsp;</span> : null}
              {part}
            </li>
          ))}
        </ol>
      </nav>
      <span className="min-w-px flex-1" />
      {tag}
      {idleSeconds !== undefined ? <IdleTimer idleSeconds={idleSeconds} /> : null}
      {user ? (
        <>
          <button type="button" aria-label="Notifications" className="shrink-0 text-ink-2 hover:text-ink">
            <Icon name="bell" size={20} />
          </button>
          <button
            type="button"
            aria-label={`Account menu for ${user.name}`}
            className="flex shrink-0 items-center gap-2.5 text-left"
          >
            <Avatar name={user.name} />
            <span className="flex flex-col whitespace-nowrap">
              <span className="type-small-medium text-ink">{user.name}</span>
              <span className="type-caption text-muted">{user.role}</span>
            </span>
            <Icon name="chevron-down" size={16} className="text-muted" />
          </button>
        </>
      ) : null}
    </header>
  );
}
