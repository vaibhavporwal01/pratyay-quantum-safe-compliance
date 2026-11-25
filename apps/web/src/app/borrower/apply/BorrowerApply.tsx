"use client";

import { useRouter } from "next/navigation";
import { ApplicationForm } from "@/components/app/LoanParts";
import { Card, PageHead } from "@/components/ui";

export function BorrowerApply() {
  const router = useRouter();
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Apply"
        title="Tell us about your loan and your household."
        subtitle="List everyone who earns. Income the loan is expected to produce is not counted. The rules run as you type; nothing is saved until you submit."
      />
      <ApplicationForm
        asOfficer={false}
        onSubmitted={(d) => router.push(`/borrower?app=${d.application.id}`)}
        side={
          <Card eyebrow="Why we ask" title="Your data stays with this loan">
            <p className="pt-3 type-small text-ink-2">
              Income and repayments are used only to check that repayments stay within the RBI limit. Nothing is shared without your consent.
            </p>
          </Card>
        }
      />
    </div>
  );
}
