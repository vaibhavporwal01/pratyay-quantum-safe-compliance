import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { LedgerView } from "./LedgerView";

export const metadata: Metadata = { title: "Ledger · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Ledger"]} area="auditor">
      <LedgerView />
    </RoleShell>
  );
}
