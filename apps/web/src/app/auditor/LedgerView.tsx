"use client";

import Link from "next/link";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Figure, Figures, PageHead, Status, Table, Tag, type Column } from "@/components/ui";
import { dateTime, EVENT_LABEL, finalLabel, money, rulesUsed, shortDateTime, type Counts, type DecisionRow, type LoanEvent } from "@/lib/api/loans";
import { useApi } from "@/lib/useApi";

const decisionColumns: Column<DecisionRow>[] = [
  { key: "ref", header: "Subject", width: 130, kind: "mono", render: (r) => r.application.ref },
  { key: "name", header: "Borrower", width: 120, kind: "primary", render: (r) => r.application.borrower_name },
  { key: "outcome", header: "Outcome", width: 190, render: (r) => finalLabel(r.application.status) },
  { key: "amount", header: "Amount", width: 90, kind: "mono", render: (r) => money(r.decision.approved_paise ?? r.decision.recommended_paise) },
  {
    key: "rules",
    header: "Rules used",
    width: 230,
    kind: "node",
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
  // HOOK(Pulkit): hash, previous hash and key id come from the ledger entry (ledger_seq).
  { key: "seal", header: "Seal", kind: "node", render: (r) => <Status status="pending" label={r.decision.ledger_seq === null ? "Signature pending" : `#${r.decision.ledger_seq}`} /> },
  {
    key: "check",
    header: "",
    width: 70,
    kind: "node",
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
  if (counts.error) return <ErrorState message={counts.error} onRetry={counts.reload} />;
  if (!counts.data) return <Loading />;
  const c = counts.data;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 01 · Ledger · read only · ${c.decisions} decisions`}
        title="Every decision and every step, in order."
        subtitle="When signing is enabled each record will hold the hash of the one before it and be signed with ML-DSA-65. Until then this is the stored record, unsigned."
        actions={<Button href="/auditor/verify">Verify a decision</Button>}
      />
      {/* HOOK(Pulkit): replace with ledger.verify_all(session) -> ChainReport. */}
      <div className="flex flex-col gap-2 border border-rule bg-paper-2 px-5 py-4 sm:flex-row sm:items-center sm:gap-5">
        <Status status="pending" label="Not verified" />
        <div className="flex flex-col">
          <p className="type-body-medium text-ink">{`${c.signed} of ${c.decisions} decisions signed`}</p>
          <p className="type-small text-ink-2">Verification available when signing is enabled. Replay checks work now, on the Verify tab.</p>
        </div>
      </div>
      <Figures>
        <Figure label="Applications" value={c.applications} note="all of Lender A" />
        <Figure label="Engine runs" value={c.evaluations} note="each stored as a snapshot" />
        <Figure label="Decisions" value={c.decisions} note="by a second person" />
        <Figure label="Steps recorded" value={c.events} note="submitted to decided" />
        <Figure label="Signed" value={c.signed} note="signing not enabled" />
      </Figures>
      <DataCard
        eyebrow="Decided by a checker · newest first"
        title={decisions.data ? `Decisions · ${decisions.data.length}` : "Decisions"}
        tag={<Tag>Unsigned</Tag>}
        state={decisions}
        isEmpty={(d) => d.length === 0}
        empty={<Empty title="No decisions yet">Applications appear here once a checker decides them. Recommendations still with a checker are not listed.</Empty>}
      >
        {(rows) => (
          <div className="overflow-x-auto">
            <Table className="min-w-[1120px]" caption="Decisions" columns={decisionColumns} rows={rows} rowKey={(r) => r.decision.id} />
          </div>
        )}
      </DataCard>
      {/* HOOK(Lokesh): the full audit log (audit.service) joins this list when it lands. */}
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
