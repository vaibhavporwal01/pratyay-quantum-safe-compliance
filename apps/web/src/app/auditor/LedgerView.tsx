"use client";

import Link from "next/link";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Figure, Figures, PageHead, Status, Table, Tag, type Column } from "@/components/ui";
import {
  dateTime, EVENT_LABEL, finalLabel, money, rulesUsed, shortDateTime,
  type Counts, type DecisionRow, type DecisionVerification, type LoanEvent
} from "@/lib/api/loans";
import { useApi } from "@/lib/useApi";
import type { ChainVerification } from "@/lib/api/trust";

function DecisionSeal({ row }: { row: DecisionRow }) {
  const hasSequence = row.decision.ledger_seq !== null;
  const verification = useApi<DecisionVerification>(
    hasSequence ? `/loans/applications/${row.application.id}/verification` : null,
  );

  if (!hasSequence) return <Status status="pending" label="Not signed" />;
  if (verification.loading) return <Status status="pending" label={`Checking #${row.decision.ledger_seq}`} />;
  if (verification.error) return <Status status="pending" label="Check unavailable" />;
  if (verification.data?.status === "verified") {
    return <Status status="pass" label={`Verified · #${verification.data.seq}`} />;
  }
  if (verification.data?.status === "failed") {
    return <Status status="fail" label={`Failed · #${verification.data.seq}`} />;
  }
  return <Status status="pending" label="Signature pending" />;
}

const decisionColumns: Column<DecisionRow>[] = [
  { key: "ref", header: "Subject", width: 130, kind: "mono", render: (r) => r.application.ref },
  { key: "name", header: "Borrower", width: 120, kind: "primary", render: (r) => r.application.borrower_name },
  { key: "outcome", header: "Outcome", width: 190, render: (r) => finalLabel(r.application.status) },
  { key: "amount", header: "Amount", width: 90, kind: "mono", render: (r) => money(r.decision.approved_paise ?? r.decision.recommended_paise) },
  {
    key: "rules", header: "Rules used", width: 230, kind: "node",
    render: (r) => (
      <span className="flex flex-col gap-0.5">
        <span className="type-mono text-ink-2">{rulesUsed(r.rules)}</span>
        <span className="type-caption text-muted" title={r.rules.versions.join(", ")}>
          {`${r.rules.checked} checked at origination · ${r.rules.versions.join(", ")}`}
        </span>
      </span>
    ),
  },
  { key: "time", header: "Decided", width: 110, kind: "mono", render: (r) => shortDateTime(r.decision.decided_at!) },
  { key: "seal", header: "Signature verification", width: 190, kind: "node", render: (r) => <DecisionSeal row={r} /> },
  {
    key: "check", header: "", width: 70, kind: "node",
    render: (r) => (
      <Link className="type-small text-stamp underline-offset-2 hover:underline" href={`/auditor/verify?app=${r.application.id}`}>
        Verify
      </Link>
    ),
  },
];

const eventColumns: Column<LoanEvent>[] = [
  { key: "time", header: "Time", width: 150, kind: "mono", render: (e) => dateTime(e.created_at) },
  { key: "ref", header: "Application", width: 130, kind: "mono", render: (e) => e.ref ?? "" },
  { key: "action", header: "Step", width: 220, kind: "primary", render: (e) => EVENT_LABEL[e.action] ?? e.action },
  { key: "who", header: "By", width: 140, render: (e) => e.actor_name ?? "Unknown" },
  { key: "detail", header: "Detail", kind: "mono", render: (e) => String(e.meta.outcome ?? e.meta.recommendation ?? "") },
];

export function LedgerView() {
  const counts = useApi<Counts>("/loans/counts");
  const decisions = useApi<DecisionRow[]>("/loans/decisions");
  const events = useApi<LoanEvent[]>("/loans/events?limit=50");
  const chain = useApi<ChainVerification>("/trust/ledger/verify");

  if (counts.error) return <ErrorState message={counts.error} onRetry={counts.reload} />;
  if (!counts.data) return <Loading />;

  const c = counts.data;
  const chainStatus = chain.loading ? "pending" : chain.error ? "pending" : chain.data?.ok ? "pass" : chain.data ? "fail" : "pending";
  const chainLabel = chain.loading ? "Checking ledger…" : chain.error ? "Chain check unavailable" : chain.data?.ok ? "Chain verified" : chain.data ? "Chain verification failed" : "Not checked";

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 01 · Ledger · read only · ${c.decisions} decisions`}
        title="Every decision and every step, in order."
        subtitle="Each final decision is checked against its stored hash, chain link and ML-DSA signature. Recommendations awaiting a checker are not signed decisions."
        actions={<Button href="/auditor/verify">Verify a decision</Button>}
      />
      <div className="flex flex-col gap-2 border border-rule bg-paper-2 px-5 py-4 sm:flex-row sm:items-center sm:gap-5">
        <Status status={chainStatus} label={chainLabel} />
        <div className="flex flex-col">
          <p className="type-body-medium text-ink">
            {chain.data ? `${chain.data.checked} ledger entries checked` : `${c.signed} signed decisions reported by API`}
          </p>
          <p className="type-small text-ink-2">
            {chain.data?.ok
              ? "All entries in the ledger passed the global integrity and signature check."
              : chain.data && !chain.data.ok
                ? `First invalid sequence: ${chain.data.first_invalid_seq ?? "unknown"}`
                : chain.error ?? "Waiting for the ledger verification response."}
          </p>
        </div>
      </div>
      <Figures>
        <Figure label="Applications" value={c.applications} note="all of Lender A" />
        <Figure label="Engine runs" value={c.evaluations} note="stored evaluation snapshots" />
        <Figure label="Decisions" value={c.decisions} note="decided by a second person" />
        <Figure label="Steps recorded" value={c.events} note="submitted through decision" />
        <Figure label="Signed" value={c.signed} note="reported by the API" />
      </Figures>
      <DataCard
        eyebrow="Decided by a checker · newest first"
        title={decisions.data ? `Decisions · ${decisions.data.length}` : "Decisions"}
        tag={<Tag>Per-decision verification</Tag>}
        state={decisions}
        isEmpty={(d) => d.length === 0}
        empty={<Empty title="No decisions yet">Applications appear here once a checker decides them. Recommendations still with a checker are not listed.</Empty>}
      >
        {(rows) => (
          <div className="overflow-x-auto">
            <Table className="min-w-[1260px]" caption="Decisions" columns={decisionColumns} rows={rows} rowKey={(r) => r.decision.id} />
          </div>
        )}
      </DataCard>
      <DataCard eyebrow="Latest 50" title="Step history" state={events} isEmpty={(d) => d.length === 0} empty={<Empty title="No steps recorded yet" />}>
        {(rows) => (
          <div className="overflow-x-auto">
            <Table className="min-w-[860px]" caption="Step history" columns={eventColumns} rows={rows} rowKey={(e) => e.id} />
          </div>
        )}
      </DataCard>
    </div>
  );
}
