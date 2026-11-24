"use client";

import { useRouter } from "next/navigation";
import { ROLES, type Role } from "@/lib/api/auth";
import { DEV_ROLE_COOKIE, ROLE_LABEL, roleHome } from "@/lib/roles";

export const devRolesEnabled = process.env.NEXT_PUBLIC_APP_ENV === "development";

/**
 * Development only, until sign-in lands: pick which seeded Lender A user you are.
 * Sets the cookie the API reads, then opens that role's home page.
 */
export function DevRoleSwitcher({ current }: { current?: Role }) {
  const router = useRouter();
  if (!devRolesEnabled) return null;
  return (
    <label className="flex items-center gap-2">
      <span className="type-label whitespace-nowrap text-muted">Act as</span>
      <select
        value={current ?? ""}
        onChange={(e) => {
          const role = e.target.value as Role;
          document.cookie = `${DEV_ROLE_COOKIE}=${role}; path=/; max-age=2592000; samesite=lax`;
          router.push(roleHome(role));
          router.refresh();
        }}
        className="h-9 rounded-[2px] border border-rule bg-white px-2 type-small text-ink focus:border-stamp focus:outline-none"
      >
        {current ? null : <option value="">Pick a role</option>}
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {ROLE_LABEL[r]}
          </option>
        ))}
      </select>
    </label>
  );
}
