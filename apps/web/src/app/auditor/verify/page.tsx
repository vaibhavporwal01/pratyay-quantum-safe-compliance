import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { VerifyView } from "./VerifyView";

export const metadata: Metadata = { title: "Verify · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Verify"]} area="auditor">
      <VerifyView />
    </RoleShell>
  );
}
