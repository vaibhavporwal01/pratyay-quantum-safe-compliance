import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
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
  menuOpen,
  onMenu,
}: {
  /** e.g. ["Lender A", "Overview"], shown as "LENDER A / OVERVIEW". */
  breadcrumb: string[];
  user?: MastheadUser;
  /** Seconds until idle sign-out. Omit to hide the timer (public pages). */
  idleSeconds?: number;
  /** Optional tag before the timer, hidden on most December screens. */
  tag?: ReactNode;
  /** Narrow screens: show a menu button instead of the breadcrumb, timer, tag and user. */
  onMenu?: () => void;
  menuOpen?: boolean;
}) {
  // With a menu, the wide-screen items hide below 768px.
  const wide = onMenu ? "hidden md:flex" : "flex";
  return (
    <header className="flex h-16 items-center gap-5 bg-paper-2 px-5 sm:px-10">
      <Logo />
      <span aria-hidden className={cn("h-6 w-px shrink-0 bg-rule", onMenu && "hidden md:block")} />
      <nav aria-label="Breadcrumb" className={cn("min-w-0 overflow-hidden", onMenu && "hidden md:block")}>
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
      {tag ? <div className={cn(wide, "shrink-0 items-center")}>{tag}</div> : null}
      {idleSeconds !== undefined ? (
        <div className={cn(wide, "shrink-0 items-center")}>
          <IdleTimer idleSeconds={idleSeconds} />
        </div>
      ) : null}
      {user ? (
        <div className={cn(wide, "shrink-0 items-center gap-5")}>
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
        </div>
      ) : null}
      {onMenu ? (
        <button
          type="button"
          onClick={onMenu}
          aria-expanded={menuOpen ?? false}
          aria-controls="app-menu"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="flex size-10 shrink-0 items-center justify-center text-ink md:hidden"
        >
          <Icon name={menuOpen ? "x" : "menu-2"} size={22} />
        </button>
      ) : null}
    </header>
  );
}
