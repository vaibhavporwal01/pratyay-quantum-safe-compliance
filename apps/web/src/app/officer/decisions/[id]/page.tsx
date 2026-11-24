import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { DecisionView } from "./DecisionView";

export const metadata: Metadata = { title: "Decision · Pratyay" };

export default function DecisionPage() {
  return (
    <RoleShell breadcrumb={["Decisions", "Application"]} area="officer">
      <DecisionView />
    </RoleShell>
  );
}
