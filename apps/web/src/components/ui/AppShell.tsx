"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "./icons";
import { Masthead, type MastheadUser } from "./Masthead";
import { NavTab, type NavTabItem } from "./NavTab";

/**
 * Masthead, double rule, numbered section tabs with search, then the page.
 * Below 768px the masthead is the logo and a menu button; the menu holds the tabs, the user and
 * `menuExtra`. The tab row stays and scrolls sideways.
 */
export function AppShell({
  breadcrumb,
  user,
  tabs,
  activeHref,
  idleSeconds = 900,
  searchPlaceholder = "Search by ID, name or rule",
  searchAction,
  mastheadExtra,
  children,
}: {
  breadcrumb: string[];
  user?: MastheadUser;
  tabs: readonly NavTabItem[];
  activeHref: string;
  idleSeconds?: number;
  searchPlaceholder?: string;
  /** Where the search form submits (GET, param "q"). Omit to hide search. */
  searchAction?: string;
  /** Shown in the masthead on wide screens and in the menu on narrow ones. */
  mastheadExtra?: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-full flex-col bg-paper">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-10 focus:bg-white focus:px-3 focus:py-2 focus:type-body-medium"
      >
        Skip to content
      </a>
      <Masthead
        breadcrumb={breadcrumb}
        user={user}
        idleSeconds={idleSeconds}
        tag={mastheadExtra}
        menuOpen={open}
        onMenu={() => setOpen((o) => !o)}
      />
      {open ? (
        <div id="app-menu" className="flex flex-col gap-4 border-t border-rule bg-paper-2 px-5 pt-3 pb-5 md:hidden">
          {tabs.length ? (
            <nav aria-label="Sections, menu" className="flex flex-col">
              {tabs.map((t) => (
                <Link
                  key={t.href}
                  href={t.href}
                  onClick={() => setOpen(false)}
                  aria-current={t.href === activeHref ? "page" : undefined}
                  className={cn(
                    "flex h-11 items-center gap-2 border-b border-rule-2",
                    t.href === activeHref ? "text-ink" : "text-ink-2",
                  )}
                >
                  <span className={cn("type-mono", t.href === activeHref ? "text-stamp" : "text-muted")}>{t.number}</span>
                  <span className="type-body-medium">{t.label}</span>
                </Link>
              ))}
            </nav>
          ) : null}
          {user ? (
            <p className="flex flex-col">
              <span className="type-small-medium text-ink">{user.name}</span>
              <span className="type-caption text-muted">{user.role}</span>
            </p>
          ) : null}
          {mastheadExtra}
        </div>
      ) : null}
      <div aria-hidden className="h-1 border-y border-ink" />
      <div className="flex items-center gap-8 border-b border-rule px-5 sm:px-10">
        <nav aria-label="Sections" className="-mb-px flex min-w-0 flex-1 items-center gap-6 overflow-x-auto sm:gap-8">
          {tabs.map((t) => (
            <NavTab key={t.href} {...t} active={t.href === activeHref} />
          ))}
        </nav>
        {searchAction ? (
          <form role="search" action={searchAction} className="hidden shrink-0 lg:block">
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
      <main id="main" className="min-w-0 flex-1 px-5 pt-9 pb-16 sm:px-10">
        {children}
      </main>
    </div>
  );
}
