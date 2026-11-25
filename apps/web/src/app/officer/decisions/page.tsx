import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { ApplicationsView } from "../applications/ApplicationsView";

export const metadata: Metadata = { title: "Decisions · Pratyay" };

export default function DecisionsPage() {
  return (
    <RoleShell breadcrumb={["Decisions"]} area="officer">
      <ApplicationsView mode="decisions" />
    </RoleShell>
  );
}
