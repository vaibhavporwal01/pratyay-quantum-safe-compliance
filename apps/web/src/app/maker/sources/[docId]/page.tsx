import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { DraftView } from "./DraftView";

export const metadata: Metadata = { title: "Draft from a circular · Pratyay" };

export default function DraftFromCircularPage() {
  return (
    <RoleShell breadcrumb={["Rules", "Draft from a circular"]} area="maker">
      <DraftView />
    </RoleShell>
  );
}
