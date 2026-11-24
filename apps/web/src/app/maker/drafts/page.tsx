import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { DraftsView } from "./DraftsView";

export const metadata: Metadata = { title: "Drafts · Pratyay" };

export default function DraftsPage() {
  return (
    <RoleShell breadcrumb={["Rules", "Drafts"]}>
      <DraftsView />
    </RoleShell>
  );
}
