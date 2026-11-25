import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { BorrowerKeyFacts } from "./BorrowerKeyFacts";

export const metadata: Metadata = { title: "Key facts · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Key facts"]} area="borrower">
      <BorrowerKeyFacts />
    </RoleShell>
  );
}
