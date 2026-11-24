import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { ReviewQueue } from "./ReviewQueue";

export const metadata: Metadata = { title: "Review queue · Pratyay" };

export default function ReviewQueuePage() {
  return (
    <RoleShell breadcrumb={["Review queue"]}>
      <ReviewQueue />
    </RoleShell>
  );
}
