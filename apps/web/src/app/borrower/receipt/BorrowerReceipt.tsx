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
  const verification = loan.verification.data;
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
        subtitle="This receipt shows the recorded decision and the result of its cryptographic ledger verification."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <LoanReceipt d={d} verification={verification} className="self-center lg:self-start" />
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          <Card
            eyebrow="Decision ledger"
            title="Everything that decided your loan"
            tag={
              <Status
                status={verification?.status === "verified" ? "pass" : verification?.status === "failed" ? "fail" : "pending"}
                label={verification?.status === "verified" ? "Signature verified" : verification?.status === "failed" ? "Verification failed" : "Signature pending"}
              />
            }
          >
            <dl className="flex flex-col">
              {rows.map(([k, v]) => (
                <div key={k} className="flex flex-col gap-1 border-b border-rule-2 py-3 sm:flex-row sm:items-center sm:gap-4">
                  <dt className="type-small text-ink-2 sm:flex-1">{k}</dt>
                  <dd className="type-mono break-words text-ink sm:text-right">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>
          <Card eyebrow="Cryptographic verification" title="Check this receipt">
            <div className="flex flex-col gap-3 pt-3">
              <p className="type-small text-ink-2">
                {verification?.status === "verified"
                  ? "The ML-DSA-65 signature, SHA3-256 entry hash, previous-hash link, key identifier and application binding all passed server-side verification."
                  : verification?.status === "failed"
                    ? "Verification failed. At least one ledger integrity, signature or application-binding check did not pass."
                    : "No signed decision is available yet. Verification will run when a decision is recorded."}
              </p>
              {verification?.seq !== null && verification?.seq !== undefined ? (
                <p className="type-mono text-muted">Ledger entry #{verification.seq} · {verification.algorithm ?? "Unknown algorithm"} · Key {verification.key_id ?? "unavailable"}</p>
              ) : null}
              {verification?.checks && Object.keys(verification.checks).length ? (
                <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {Object.entries(verification.checks).map(([name, passed]) => (
                    <div key={name} className="flex items-center justify-between gap-3 border-b border-rule-2 py-1">
                      <dt className="type-caption text-muted">{name.replaceAll("_", " ")}</dt>
                      <dd className={`type-caption font-medium ${passed ? "text-ink" : "text-red-700"}`}>{passed ? "Passed" : "Failed"}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
