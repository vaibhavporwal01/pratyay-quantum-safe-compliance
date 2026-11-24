import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { FindingsView } from "./FindingsView";

export const metadata: Metadata = { title: "Findings · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Findings"]} area="auditor">
      <FindingsView />
    </RoleShell>
  );
}
