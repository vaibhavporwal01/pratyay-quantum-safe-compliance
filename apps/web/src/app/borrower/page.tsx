import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { BorrowerHome } from "./BorrowerHome";

export const metadata: Metadata = { title: "Home · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["My loan"]} area="borrower">
      <BorrowerHome />
    </RoleShell>
  );
}
