"use client";

import { AprSheet, KfsTable, kfsRows } from "@/components/app/LoanParts";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, PageHead, Status } from "@/components/ui";
import { currentKfs } from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useMyLoan } from "../useMyLoan";

export function BorrowerKeyFacts() {
  const loan = useMyLoan();
  if (loan.error) return <ErrorState message={loan.error} onRetry={loan.reload} />;
  if (loan.none) return <Empty title="No key facts yet" action={<Button href="/borrower/apply">Apply for a loan</Button>}>Key facts appear once you apply.</Empty>;
  if (!loan.detail.data) return <Loading />;
  const d = loan.detail.data;
  const kfs = currentKfs(d);
  const mf04 = (d.final_evaluation ?? d.evaluation)?.results.find((r) => r.code === "MF-04");
  if (!kfs) return <Empty title="No key facts yet">The amount, tenor or rate is missing, so the statement cannot be computed.</Empty>;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 03 · Key facts${kfs.valid_until ? ` · valid until ${formatDate(kfs.valid_until)}` : ""}`}
        title="Read the key facts, then accept."
        subtitle={`This statement shows every charge and the yearly cost of your loan.${kfs.validity_working_days ? ` It is valid for ${kfs.validity_working_days} working days.` : ""} Charges not listed here cannot be added later without your consent.`}
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <Card eyebrow={`Key facts statement · ${d.application.ref}`} title={`${d.application.product_name} from Lender A`} tag={<Status status="pending" label="Signature pending" />} className="min-w-0 flex-1">
          <KfsTable rows={[...kfsRows(kfs), ...(mf04?.status === "pass" ? [["Paying early", "no charge", mf04.anchor] as [string, string, string]] : [])]} />
          <p className="pt-3 type-caption text-muted">{kfs.notes.join(" ")}</p>
        </Card>
        <div className="flex min-w-0 flex-col gap-7 lg:w-[420px] lg:shrink-0">
          {/* HOOK(Vishnukant): OTP acceptance arrives with borrower sign-in. */}
          <Card eyebrow="Step 2 of 2" title="Accept with a one-time code">
            <div className="flex flex-col gap-3 pt-3">
              <p className="type-small text-ink-2">Accepting by a code sent to your phone arrives with sign-in. Until then an officer records your acceptance.</p>
              <Button disabled>Accept key facts</Button>
            </div>
          </Card>
          <Card eyebrow="APR computation" title={`How ${kfs.apr_percent}% is worked out`}>
            <div className="pt-3">
              <AprSheet kfs={kfs} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
