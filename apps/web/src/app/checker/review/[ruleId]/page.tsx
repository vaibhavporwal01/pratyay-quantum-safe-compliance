import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { RuleReview } from "./RuleReview";

export const metadata: Metadata = { title: "Rule review · Pratyay" };

export default function RuleReviewPage() {
  return (
    <RoleShell breadcrumb={["Review queue", "Rule"]}>
      <RuleReview />
    </RoleShell>
  );
}
