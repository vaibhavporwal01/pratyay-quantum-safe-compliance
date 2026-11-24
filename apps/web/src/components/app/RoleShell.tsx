"use client";

import { usePathname } from "next/navigation";
import { createContext, Suspense, useContext, type ReactNode } from "react";
import { AppShell } from "@/components/ui";
import type { Me } from "@/lib/api/rules";
import { activeTab, navForRole, ROLE_LABEL } from "@/lib/roles";
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

type ShellProps = { breadcrumb: string[]; children: ReactNode };

/**
 * AppShell for signed-in pages: loads the current user, builds the tabs for their role, and
 * (in development) offers the role switcher. The path and user are only known at request time,
 * so the prerendered page is the bare shell and the rest streams in.
 */
export function RoleShell({ breadcrumb, children }: ShellProps) {
  return (
    <Suspense
      fallback={
        <AppShell breadcrumb={["Lender A", ...breadcrumb]} tabs={[]} activeHref="">
          <Loading />
        </AppShell>
      }
    >
      <SignedInShell breadcrumb={breadcrumb}>{children}</SignedInShell>
    </Suspense>
  );
}

function SignedInShell({ breadcrumb, children }: ShellProps) {
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
      ) : me.data ? (
        <MeContext.Provider value={me.data}>{children}</MeContext.Provider>
      ) : (
        <Loading />
      )}
    </AppShell>
  );
}
