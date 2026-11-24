import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { BorrowerApply } from "./BorrowerApply";

export const metadata: Metadata = { title: "Apply · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Apply"]} area="borrower">
      <BorrowerApply />
    </RoleShell>
  );
}
