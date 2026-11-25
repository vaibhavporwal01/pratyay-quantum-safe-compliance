import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { NewApplication } from "./NewApplication";

export const metadata: Metadata = { title: "New application · Pratyay" };

export default function NewApplicationPage() {
  return (
    <RoleShell breadcrumb={["Applications", "New"]} area="officer">
      <NewApplication />
    </RoleShell>
  );
}
