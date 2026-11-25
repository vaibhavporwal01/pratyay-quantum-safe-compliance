import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { BorrowerReceipt } from "./BorrowerReceipt";

export const metadata: Metadata = { title: "Receipt · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Receipt"]} area="borrower">
      <BorrowerReceipt />
    </RoleShell>
  );
}
