import type { NavTabItem } from "@/components/ui";
import type { Role } from "./api/auth";

export const DEV_ROLE_COOKIE = "pratyay_dev_role";

export const ROLE_LABEL: Record<Role, string> = {
  borrower: "Borrower",
  officer: "Loan officer",
  maker: "Compliance maker",
  checker: "Compliance checker",
  auditor: "Auditor",
  admin: "Administrator",
};

/**
 * Who may open each area. Mirrors the API's require_role guards in
 * apps/api/app/rules/router.py (Maker, Checker, Reader), so a page never offers what the API
 * would refuse with 403.
 */
export const PAGE_ROLES = {
  maker: ["maker"],
  checker: ["checker"],
  reader: ["maker", "checker", "auditor", "admin"],
} as const satisfies Record<string, readonly Role[]>;

export type PageArea = keyof typeof PAGE_ROLES;

export function canAccess(role: Role | undefined, area: PageArea | undefined): boolean {
  if (!area) return true;
  return role !== undefined && (PAGE_ROLES[area] as readonly Role[]).includes(role);
}

/** "the compliance maker", "a compliance maker or compliance checker or ..." */
export function areaAudience(area: PageArea): string {
  const names = (PAGE_ROLES[area] as readonly Role[]).map((r) => ROLE_LABEL[r].toLowerCase());
  return names.length === 1 ? `the ${names[0]}` : `${names.slice(0, -1).join(", ")} or ${names.at(-1)}`;
}

const LIBRARY = { href: "/rules/library", label: "Rule library" };

const NAV: Record<Role, { href: string; label: string }[]> = {
  maker: [
    { href: "/maker/sources", label: "Sources" },
    { href: "/maker/drafts", label: "Drafts" },
    LIBRARY,
  ],
  checker: [
    { href: "/checker", label: "Overview" },
    { href: "/checker/review", label: "Review queue" },
    LIBRARY,
  ],
  auditor: [LIBRARY],
  admin: [LIBRARY],
  officer: [],
  borrower: [],
};

/** Numbered section tabs for a role, as in the Dec v1 masthead. */
export function navForRole(role: Role | undefined): NavTabItem[] {
  return (role ? NAV[role] : []).map((t, i) => ({ ...t, number: String(i + 1).padStart(2, "0") }));
}

/** Where the role switcher sends each role. Officer and borrower pages are not built yet. */
export function roleHome(role: Role): string {
  return NAV[role][0]?.href ?? "/rules/library";
}

/** The tab a path belongs to: the longest tab href that prefixes it. */
export function activeTab(tabs: NavTabItem[], pathname: string): string {
  const match = tabs
    .filter((t) => pathname === t.href || pathname.startsWith(`${t.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return match?.href ?? "";
}
