import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { KeysView } from "./KeysView";

export const metadata: Metadata = { title: "Signing keys · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Signing keys"]} area="admin">
      <KeysView />
    </RoleShell>
  );
}
