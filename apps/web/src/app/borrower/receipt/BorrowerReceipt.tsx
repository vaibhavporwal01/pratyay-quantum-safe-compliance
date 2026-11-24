"use client";

import { LoanReceipt } from "@/components/app/LoanParts";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, PageHead, Status } from "@/components/ui";
import { dateTime, money, resultSummary } from "@/lib/api/loans";
import { useMyLoan } from "../useMyLoan";

export function BorrowerReceipt() {
  const loan = useMyLoan();
  if (loan.error) return <ErrorState message={loan.error} onRetry={loan.reload} />;
  if (loan.none) return <Empty title="No receipt yet" action={<Button href="/borrower/apply">Apply for a loan</Button>}>A receipt appears once a decision is made.</Empty>;
  if (!loan.detail.data) return <Loading />;
  const d = loan.detail.data;
  const a = d.application;
  const dec = d.decision;
  const ev = d.final_evaluation ?? d.evaluation;
  const rows: [string, string][] = [
    ["Your application, as submitted", a.ref],
    ["Rules used", ev ? ev.rules_used.map((r) => `${r.code} v${r.version}`).join(" · ") : "Not run"],
    ["Result of each rule", ev ? resultSummary(ev.results) : "Not run"],
    ["Amount decided", dec?.approved_paise ? money(dec.approved_paise) : dec?.outcome === "rejected" ? "Declined" : "Not decided yet"],
    ["Who prepared and who decided", dec ? `${dec.officer_name ?? ""} · ${dec.checker_name ?? "waiting"}` : "Not yet"],
    ["Time", dec?.decided_at ? `${dateTime(dec.decided_at)} IST` : "Not decided yet"],
  ];
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 04 · Receipt · ${a.ref}`}
        title={dec?.decided_at ? "Your decision, and everything behind it." : "Your receipt, so far."}
        subtitle="Keep this receipt. Once Lender A signs it, anyone can check it on the public Verify page without trusting us."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <LoanReceipt d={d} className="self-center lg:self-start" />
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          <Card eyebrow="What will be signed" title="Everything that decided your loan" tag={<Status status="pending" label="Signature pending" />}>
            <dl className="flex flex-col">
              {rows.map(([k, v]) => (
                <div key={k} className="flex flex-col gap-1 border-b border-rule-2 py-3 sm:flex-row sm:items-center sm:gap-4">
                  <dt className="type-small text-ink-2 sm:flex-1">{k}</dt>
                  <dd className="type-mono break-words text-ink sm:text-right">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>
          {/* HOOK(Pulkit): Verify the receipt once decisions are signed with ML-DSA-65. */}
          <Card eyebrow="Check it" title="Verify this receipt">
            <p className="pt-3 type-small text-ink-2">Verification available when signing is enabled. The check will recompute the record hash and Lender A&apos;s signature.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
