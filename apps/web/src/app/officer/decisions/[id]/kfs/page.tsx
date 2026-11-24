import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { KfsView } from "./KfsView";

export const metadata: Metadata = { title: "Key Facts Statement · Pratyay" };

export default function KfsPage() {
  return (
    <RoleShell breadcrumb={["Decisions", "Key facts"]} area="officer">
      <KfsView />
    </RoleShell>
  );
}
