"use client";

import { decisionFigures, LoanReceipt, ParagraphQuote } from "@/components/app/LoanParts";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Figure, Figures, PageHead, Status, Tag, type StatusKind } from "@/components/ui";
import { dateTime, money, resultSummary, type Detail } from "@/lib/api/loans";
import { useMyLoan } from "./useMyLoan";

function title(d: Detail): string {
  const first = d.application.borrower_name.split(/\s+/)[0];
  const amount = d.decision?.approved_paise;
  switch (d.application.status) {
    case "approved":
    case "approved_modified":
      return `Namaste, ${first}. Your loan is approved at ${money(amount)}.`;
    case "rejected":
      return `Namaste, ${first}. We could not approve this loan.`;
    case "recommended":
      return `Namaste, ${first}. Your application is with a checker.`;
    default:
      return `Namaste, ${first}. Your application is with a loan officer.`;
  }
}

export function BorrowerHome() {
  const loan = useMyLoan();
  if (loan.error) return <ErrorState message={loan.error} onRetry={loan.reload} />;
  if (loan.none)
    return (
      <div className="flex flex-col gap-7">
        <PageHead eyebrow="§ 01 · My loan" title="Namaste. You have no application yet." subtitle="Apply in a few minutes. You see every rule that decides your loan, with its paragraph." />
        <Empty title="No application" action={<Button href="/borrower/apply">Apply for a loan</Button>}>
          Your application, its key facts and the decision appear here.
        </Empty>
      </div>
    );
  if (!loan.detail.data) return <Loading />;
  const d = loan.detail.data;
  const a = d.application;
  const modified = d.decision?.approved_paise != null && d.decision.approved_paise !== a.amount_paise;
  const decided = Boolean(d.decision?.decided_at);
  const kfs = (d.final_evaluation ?? d.evaluation)?.kfs;
  const mf02 = d.evaluation?.results.find((r) => r.code === "MF-02");
  const mf02At = d.final_evaluation?.results.find((r) => r.code === "MF-02");
  const steps: { title: string; note: string; status: StatusKind; label?: string }[] = [
    { title: "Submitted", note: `${dateTime(a.created_at)} · ${a.submitted_by_name === a.borrower_name ? "by you" : `with ${a.submitted_by_name ?? "an officer"}`}`, status: "pass", label: "Done" },
    { title: "Rules checked", note: d.evaluation ? resultSummary(d.evaluation.results) : "Not yet", status: d.evaluation ? "pass" : "pending", label: d.evaluation ? "Done" : undefined },
    { title: "Recommended by a loan officer", note: d.decision ? `${dateTime(d.decision.recommended_at)} · ${d.decision.officer_name ?? ""}` : "Waiting", status: d.decision ? "pass" : "pending", label: d.decision ? "Done" : undefined },
    {
      title: "Decided by a second person",
      note: decided ? `${dateTime(d.decision!.decided_at)} · ${d.decision!.checker_name ?? ""}` : "Waiting",
      status: !decided ? "pending" : a.status === "rejected" ? "fail" : "pass",
      label: !decided ? undefined : a.status === "rejected" ? "Declined" : "Approved",
    },
    { title: "Signed by Lender A", note: "Verification available when signing is enabled.", status: "pending", label: "Signature pending" },
  ];
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 01 · My loan · ${a.ref}`}
        title={title(d)}
        subtitle={
          modified
            ? `You asked for ${money(a.amount_paise)}. The lower amount comes from one rule, shown below with its paragraph.`
            : a.status === "rejected"
              ? d.decision?.checker_note ?? "The reason is below, with its paragraph."
              : `You asked for ${money(a.amount_paise)} for ${a.tenor_months} months.`
        }
        actions={kfs ? <Button href={`/borrower/key-facts?app=${a.id}`}>Read key facts</Button> : undefined}
      />
      <Figures>
        {[...decisionFigures(d), ...(kfs ? [{ label: "APR", value: `${kfs.apr_percent}%`, note: "fees included" }] : [])].map((f) => (
          <Figure key={f.label} label={f.label} value={f.value} note={f.note} />
        ))}
      </Figures>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          <Card eyebrow={`Application ${a.ref}`} title="Where your application is" tag={<Tag tone="stamp">{`${steps.filter((s) => s.status !== "pending").length} of ${steps.length} done`}</Tag>}>
            <ol className="flex flex-col">
              {steps.map((s) => (
                <li key={s.title} className="flex items-center gap-3 border-b border-rule-2 py-3.5">
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <p className="type-body-medium text-ink">{s.title}</p>
                    <p className="type-caption text-muted">{s.note}</p>
                  </div>
                  <Status status={s.status} label={s.label} />
                </li>
              ))}
            </ol>
          </Card>
          {mf02 && (modified || mf02.status === "fail") ? (
            <Card eyebrow={`MF-02 · ${mf02.anchor}`} title={modified ? `Why ${money(d.decision!.approved_paise)} and not ${money(a.amount_paise)}` : "Why the amount does not fit"} tag={<Tag tone="ink">Rule applied</Tag>}>
              <div className="flex flex-col gap-3 pt-3">
                <p className="type-body text-ink">
                  {`At ${money(a.amount_paise)} your repayments on all loans would be ${mf02.values.repayments} a month, ${mf02.values.ratio_percent}% of household income. The limit is ${mf02.values.limit_percent}%.`}
                  {mf02At ? ` At ${money(d.decision!.approved_paise)} they are ${mf02At.values.repayments}, or ${mf02At.values.ratio_percent}%.` : ""}
                </p>
                <p className="type-small text-ink-2">Income you expect the loan to produce is not counted, because the Directions exclude it.</p>
                <ParagraphQuote r={mf02} />
              </div>
            </Card>
          ) : null}
        </div>
        <div className="flex min-w-0 flex-col gap-7 lg:w-[440px] lg:shrink-0">
          <LoanReceipt d={d} className="self-center" />
          {/* HOOK(Pulkit): the public Verify link works once decisions are signed. */}
          <Card eyebrow="Check it yourself" title="Your receipt is not signed yet">
            <p className="pt-3 type-small text-ink-2">
              {`Lender A will sign this record so anyone can check it on the public Verify page using ${a.ref}. Verification available when signing is enabled.`}
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
