"use client";

import { useRouter } from "next/navigation";
import { ApplicationForm } from "@/components/app/LoanParts";
import { Button, PageHead } from "@/components/ui";

export function NewApplication() {
  const router = useRouter();
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · New application"
        title="New application"
        subtitle="Key in what the borrower told you. The rules run as you type; nothing is saved until you submit."
        actions={
          <Button variant="secondary" href="/officer/applications">
            Cancel
          </Button>
        }
      />
      <ApplicationForm asOfficer onSubmitted={(d) => router.push(`/officer/decisions/${d.application.id}`)} />
    </div>
  );
}
