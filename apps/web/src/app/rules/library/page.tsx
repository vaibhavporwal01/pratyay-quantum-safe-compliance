import type { Metadata } from "next";
import { Suspense } from "react";
import { RoleShell } from "@/components/app/RoleShell";
import { Loading } from "@/components/app/States";
import { LibraryView } from "./LibraryView";

export const metadata: Metadata = { title: "Rule library · Pratyay" };

export default function LibraryPage() {
  return (
    <RoleShell breadcrumb={["Rules"]} area="reader">
      <Suspense fallback={<Loading />}>
        <LibraryView />
      </Suspense>
    </RoleShell>
  );
}
