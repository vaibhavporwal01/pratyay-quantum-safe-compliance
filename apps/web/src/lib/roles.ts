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
 * Who may open each area. Mirrors the API's require_role guards in apps/api/app/rules/router.py,
 * apps/api/app/loans/router.py and apps/api/app/admin/router.py, so a page never offers what the
 * API would refuse with 403.
 */
export const PAGE_ROLES = {
  maker: ["maker"],
  checker: ["checker"],
  reader: ["maker", "checker", "auditor", "admin"],
  borrower: ["borrower"],
  officer: ["officer"],
  auditor: ["auditor", "admin"],
  cryptolab: ["checker", "auditor", "admin"],
  admin: ["admin"],
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
const CRYPTO_LAB = { href: "/crypto-lab", label: "Crypto lab" };

const NAV: Record<Role, { href: string; label: string }[]> = {
  maker: [
    { href: "/maker/sources", label: "Sources" },
    { href: "/maker/drafts", label: "Drafts" },
    LIBRARY,
  ],
  checker: [
    { href: "/checker", label: "Overview" },
    { href: "/checker/review", label: "Review queue" },
    { href: "/checker/decisions", label: "Decisions to sign" },
    LIBRARY,
    CRYPTO_LAB,
  ],
  auditor: [
    { href: "/auditor", label: "Ledger" },
    { href: "/auditor/verify", label: "Verify" },
    { href: "/auditor/findings", label: "Findings" },
    CRYPTO_LAB,
    LIBRARY,
  ],
  admin: [
    { href: "/admin", label: "Users and roles" },
    { href: "/admin/keys", label: "Signing keys" },
    { href: "/auditor", label: "Ledger" },
    LIBRARY,
  ],
  officer: [
    { href: "/officer", label: "Overview" },
    { href: "/officer/applications", label: "Applications" },
    { href: "/officer/decisions", label: "Decisions" },
  ],
  borrower: [
    { href: "/borrower", label: "Home" },
    { href: "/borrower/apply", label: "Application" },
    { href: "/borrower/key-facts", label: "Key facts" },
    { href: "/borrower/receipt", label: "Receipt" },
  ],
};

/** Numbered section tabs for a role, as in the Dec v1 masthead. */
export function navForRole(role: Role | undefined): NavTabItem[] {
  return (role ? NAV[role] : []).map((t, i) => ({ ...t, number: String(i + 1).padStart(2, "0") }));
}

/** Where the role switcher sends each role: the first tab. */
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
