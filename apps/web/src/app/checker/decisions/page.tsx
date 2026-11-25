import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { DecisionQueue } from "./DecisionQueue";

export const metadata: Metadata = { title: "Decisions to sign · Pratyay" };

export default function DecisionsToSignPage() {
  return (
    <RoleShell breadcrumb={["Decisions to sign"]} area="checker">
      <DecisionQueue />
    </RoleShell>
  );
}
