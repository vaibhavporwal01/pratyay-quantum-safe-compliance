import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { UsersView } from "./UsersView";

export const metadata: Metadata = { title: "Users and roles · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Admin"]} area="admin">
      <UsersView />
    </RoleShell>
  );
}
