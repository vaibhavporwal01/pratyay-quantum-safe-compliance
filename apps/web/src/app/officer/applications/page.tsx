import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { ApplicationsView } from "./ApplicationsView";

export const metadata: Metadata = { title: "Applications · Pratyay" };

export default function ApplicationsPage() {
  return (
    <RoleShell breadcrumb={["Applications"]} area="officer">
      <ApplicationsView mode="all" />
    </RoleShell>
  );
}
