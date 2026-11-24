import type { Metadata } from "next";
import { Suspense } from "react";
import { RoleShell } from "@/components/app/RoleShell";
import { Loading } from "@/components/app/States";
import { BuilderView } from "./BuilderView";

export const metadata: Metadata = { title: "Rule builder · Pratyay" };

export default function BuilderPage() {
  return (
    <RoleShell breadcrumb={["Rules", "Rule builder"]} area="maker">
      <Suspense fallback={<Loading />}>
        <BuilderView />
      </Suspense>
    </RoleShell>
  );
}
