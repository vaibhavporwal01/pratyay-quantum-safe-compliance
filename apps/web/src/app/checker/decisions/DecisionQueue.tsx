"use client";

import { useState } from "react";
import { ResultRow } from "@/components/app/LoanParts";
import { NoteField } from "@/components/app/NoteField";
import { useMe } from "@/components/app/RoleShell";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Field, PageHead, Status, Tag } from "@/components/ui";
import { api, failureMessage } from "@/lib/api/client";
import { money, OUTCOME_LABEL, toPaise, type AppSummary, type Detail } from "@/lib/api/loans";
import { cn } from "@/lib/cn";
import { useApi } from "@/lib/useApi";

const WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

export function DecisionQueue() {
  const queue = useApi<AppSummary[]>("/loans/applications?status=recommended");
  const [picked, setPicked] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const n = queue.data?.length ?? 0;
  const id = picked && queue.data?.some((a) => a.id === picked) ? picked : (queue.data?.[0]?.id ?? null);
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 03 · Decisions to sign · ${n} waiting`}
        title={queue.data ? `${WORDS[n] ?? n} decision${n === 1 ? " needs" : "s need"} your signature.` : "Decisions to sign."}
        subtitle="You did not prepare these, so you can decide them. Nobody can decide their own recommendation. Signing is added when the trust module lands; until then each decision is stored with Signature pending."
      />
      {done ? (
        <div role="status" className="border border-pass bg-pass-bg/50 px-5 py-3 type-body text-ink">
          {done}
        </div>
      ) : null}
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <DataCard
          className="min-w-0 lg:w-[560px] lg:shrink-0"
          eyebrow="Queue"
          title="Waiting for a second person"
          tag={<Tag tone="stamp">{`${n} open`}</Tag>}
          state={queue}
          isEmpty={(d) => d.length === 0}
          empty={<Empty title="Nothing to decide">Recommendations from loan officers appear here.</Empty>}
        >
          {(apps) => (
            <ul className="flex flex-col pt-2">
              {apps.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    onClick={() => setPicked(a.id)}
                    aria-current={a.id === id}
                    className={cn("flex w-full flex-col gap-1 border-b border-rule-2 px-2 py-3 text-left sm:flex-row sm:items-center sm:gap-3", a.id === id && "bg-stamp-bg/60")}
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="type-body-medium text-ink">{`${a.ref} · ${a.borrower_name}`}</span>
                      <span className="type-caption text-ink-2">{a.recommendation ? OUTCOME_LABEL[a.recommendation] : ""}</span>
                    </span>
                    <span className="type-mono text-ink">{money(a.amount_paise)}</span>
                    <Status status="referred" label="With you" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </DataCard>
        {id ? (
          <DecisionPanel
            key={id}
            id={id}
            onDone={(msg) => {
              setDone(msg);
              setPicked(null);
              queue.reload();
            }}
          />
        ) : null}
      </div>
    </div>
  );
}

function DecisionPanel({ id, onDone }: { id: string; onDone: (msg: string) => void }) {
  const me = useMe();
  const detail = useApi<Detail>(`/loans/applications/${id}`);
  const [mode, setMode] = useState<"approve" | "modify" | "reject">("approve");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return <Loading />;
  const d = detail.data;
  const a = d.application;
  const dec = d.decision!;
  const own = dec.officer_id === me.id;
  const amountText = money(dec.recommended_paise ?? a.amount_paise);
  const asked = d.evaluation?.results.filter((r) => r.status !== "not_checked" && r.status !== "not_applicable") ?? [];
  const atRec = d.recommended_evaluation?.results.filter((r) => r.code === "MF-02") ?? [];

  async function decide() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/loans/applications/${a.id}/decide`, {
        outcome: mode,
        amount_paise: mode === "modify" ? toPaise(amount) : null,
        note: note || null,
      });
      onDone(`${a.ref} decided. Stored with Signature pending until signing is enabled.`);
    } catch (e) {
      setError(failureMessage(e));
      setBusy(false);
    }
  }

  return (
    <Card
      className="min-w-0 flex-1"
      eyebrow={`${a.ref} · ${a.borrower_name}`}
      title={dec.recommendation === "reject" ? `Recommended: decline ${money(a.amount_paise)}` : dec.recommendation === "approve_modified" ? `Approve with modified amount: ${amountText} of ${money(a.amount_paise)}` : `Approve ${amountText}`}
      tag={<Tag>{`Prepared by ${dec.officer_name ?? "an officer"}`}</Tag>}
    >
      <div className="flex flex-col">
        {asked.map((r) => (
          <ResultRow key={r.code} r={r} at={money(a.amount_paise)} />
        ))}
        {atRec.map((r) => (
          <ResultRow key={`${r.code}-rec`} r={r} at={amountText} />
        ))}
        <div className="mt-4 flex flex-col gap-1 bg-paper px-4 py-3">
          <p className="type-label text-muted">Officer&apos;s note</p>
          <p className="type-body text-ink">{dec.officer_note ?? "No note."}</p>
        </div>
        {own ? (
          <div className="pt-4">
            <ErrorState title="You prepared this" message="The officer who recommended cannot also decide. Another checker decides it." />
          </div>
        ) : (
          <div className="flex flex-col gap-4 pt-5">
            <div role="group" aria-label="Decision" className="flex flex-wrap gap-2">
              {(["approve", "modify", "reject"] as const).map((m) => (
                <Button
                  key={m}
                  variant={mode === m ? "primary" : "secondary"}
                  aria-pressed={mode === m}
                  onClick={() => setMode(m)}
                  disabled={m === "approve" && dec.recommendation === "reject"}
                >
                  {m === "approve" ? `Approve ${amountText}` : m === "modify" ? "Modify amount" : "Decline"}
                </Button>
              ))}
            </div>
            {mode === "modify" ? <Field label="Amount (₹)" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} hint="The rules run again at this amount; every origination rule must pass." /> : null}
            <NoteField label="Your note" value={note} onChange={setNote} hint={mode === "approve" ? "Optional." : "Required."} />
            {error ? <ErrorState title="Not decided" message={error} /> : null}
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => void decide()} disabled={busy}>
                {busy ? "Deciding" : "Decide"}
              </Button>
              <Status status="pending" label="Signature pending" />
              <span className="flex-1" />
              <p className="type-mono text-muted">{`Officer: ${dec.officer_name ?? ""} · Checker: you`}</p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
