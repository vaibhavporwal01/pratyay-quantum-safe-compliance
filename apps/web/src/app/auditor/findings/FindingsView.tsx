"use client";

import { Card, PageHead, Status } from "@/components/ui";
import { Empty } from "@/components/app/States";

/** Findings (86:11424). Raising a finding writes an audit_finding ledger record, so it waits for signing. */
export function FindingsView() {
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 03 · Findings"
        title="Raise what the records cannot explain."
        subtitle="A finding names the record, what is wrong and why it matters. It is signed into the ledger so it cannot be deleted quietly, and Lender A's checker must respond."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        {/* HOOK(Lokesh): findings log from the audit module. HOOK(Pulkit): ledger event audit_finding. */}
        <Card eyebrow="All findings" title="Findings log" className="min-w-0 flex-1">
          <div className="pt-3">
            <Empty title="No findings raised">
              Findings are written to the ledger as audit_finding records, signed with ML-DSA-65. Raising one is available when signing is enabled.
            </Empty>
          </div>
        </Card>
        <Card eyebrow="New finding" title="Before you raise one" className="min-w-0 lg:w-[480px] lg:shrink-0">
          <div className="flex flex-col gap-3 pt-3">
            <p className="type-small text-ink-2">Open the Verify tab and replay the decision. A replay that differs from the stored record is the evidence a finding needs.</p>
            <Status status="pending" label="Raising findings available when signing is enabled" />
          </div>
        </Card>
      </div>
    </div>
  );
}
