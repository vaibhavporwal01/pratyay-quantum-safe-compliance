"use client";

import { usePathname } from "next/navigation";
import { createContext, Suspense, useContext, type ReactNode } from "react";
import { AppShell } from "@/components/ui";
import type { Me } from "@/lib/api/rules";
import { activeTab, areaAudience, canAccess, navForRole, ROLE_LABEL, type PageArea } from "@/lib/roles";
import { useApi } from "@/lib/useApi";
import { DevRoleSwitcher } from "./DevRoleSwitcher";
import { ErrorState, Loading } from "./States";

const MeContext = createContext<Me | null>(null);

/** The signed-in user. Only inside RoleShell, after it has loaded. */
export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMe outside RoleShell");
  return me;
}

type ShellProps = {
  breadcrumb: string[];
  /** Which roles may see the page (lib/roles PAGE_ROLES); others get the 403 state. */
  area?: PageArea;
  children: ReactNode;
};

/**
 * AppShell for signed-in pages: loads the current user, builds the tabs for their role, and
 * (in development) offers the role switcher. The path and user are only known at request time,
 * so the prerendered page is the bare shell and the rest streams in.
 */
export function RoleShell({ breadcrumb, area, children }: ShellProps) {
  return (
    <Suspense
      fallback={
        <AppShell breadcrumb={["Lender A", ...breadcrumb]} tabs={[]} activeHref="">
          <Loading />
        </AppShell>
      }
    >
      <SignedInShell breadcrumb={breadcrumb} area={area}>
        {children}
      </SignedInShell>
    </Suspense>
  );
}

function SignedInShell({ breadcrumb, area, children }: ShellProps) {
  const pathname = usePathname();
  const me = useApi<Me>("/me");
  const tabs = navForRole(me.data?.role);
  return (
    <AppShell
      breadcrumb={["Lender A", ...breadcrumb]}
      user={me.data ? { name: me.data.name, role: ROLE_LABEL[me.data.role] } : undefined}
      tabs={tabs}
      activeHref={activeTab(tabs, pathname)}
      mastheadExtra={<DevRoleSwitcher current={me.data?.role} />}
    >
      {me.error ? (
        <ErrorState title="Not signed in" message={me.error} onRetry={me.reload} />
      ) : me.data && !canAccess(me.data.role, area) ? (
        <Forbidden role={me.data.role} area={area!} />
      ) : me.data ? (
        <MeContext.Provider value={me.data}>{children}</MeContext.Provider>
      ) : (
        <Loading />
      )}
    </AppShell>
  );
}

/** The 403 state, inside the shell so the masthead (and its role switcher) stays usable. */
export function Forbidden({ role, area }: { role: Me["role"]; area: PageArea }) {
  return (
    <ErrorState
      title="Not available for your role"
      message={`This page is for ${areaAudience(area)}. You are signed in as ${ROLE_LABEL[role].toLowerCase()}.`}
    />
  );
}
