import type { ReactNode } from "react";
import { Icon } from "./icons";
import { Masthead, type MastheadUser } from "./Masthead";
import { NavTab, type NavTabItem } from "./NavTab";

/** Masthead, double rule, numbered section tabs with search, then the page. */
export function AppShell({
  breadcrumb,
  user,
  tabs,
  activeHref,
  idleSeconds = 900,
  searchPlaceholder = "Search by ID, name or rule",
  searchAction,
  children,
}: {
  breadcrumb: string[];
  user: MastheadUser;
  tabs: NavTabItem[];
  activeHref: string;
  idleSeconds?: number;
  searchPlaceholder?: string;
  /** Where the search form submits (GET, param "q"). Omit to hide search. */
  searchAction?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col bg-paper">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-10 focus:bg-white focus:px-3 focus:py-2 focus:type-body-medium"
      >
        Skip to content
      </a>
      <Masthead breadcrumb={breadcrumb} user={user} idleSeconds={idleSeconds} />
      <div aria-hidden className="h-1 border-y border-ink" />
      <div className="flex items-center gap-8 border-b border-rule px-10">
        <nav aria-label="Sections" className="flex items-center gap-8">
          {tabs.map((t) => (
            <NavTab key={t.href} {...t} active={t.href === activeHref} />
          ))}
        </nav>
        <span className="min-w-px flex-1" />
        {searchAction ? (
          <form role="search" action={searchAction} className="shrink-0">
            <label className="flex h-9 w-[300px] items-center gap-2 rounded-[2px] border border-rule bg-white px-3 text-muted focus-within:border-stamp">
              <Icon name="search" size={16} />
              <span className="sr-only">Search</span>
              <input
                type="search"
                name="q"
                placeholder={searchPlaceholder}
                className="min-w-0 flex-1 bg-transparent text-ink type-small outline-none placeholder:text-muted"
              />
            </label>
          </form>
        ) : null}
      </div>
      <main id="main" className="flex-1 px-10 pt-9 pb-16">
        {children}
      </main>
    </div>
  );
}
