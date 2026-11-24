import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { CheckerOverview } from "./CheckerOverview";

export const metadata: Metadata = { title: "Overview · Pratyay" };

export default function CheckerPage() {
  return (
    <RoleShell breadcrumb={["Overview"]} area="checker">
      <CheckerOverview />
    </RoleShell>
  );
}
