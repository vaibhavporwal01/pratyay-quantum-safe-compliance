import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { OfficerOverview } from "./OfficerOverview";

export const metadata: Metadata = { title: "Overview · Pratyay" };

export default function OfficerPage() {
  return (
    <RoleShell breadcrumb={["Overview"]} area="officer">
      <OfficerOverview />
    </RoleShell>
  );
}
