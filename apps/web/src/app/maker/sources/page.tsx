import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { SourcesView } from "./SourcesView";

export const metadata: Metadata = { title: "Source documents · Pratyay" };

export default function SourcesPage() {
  return (
    <RoleShell breadcrumb={["Rules", "Sources"]} area="maker">
      <SourcesView />
    </RoleShell>
  );
}
