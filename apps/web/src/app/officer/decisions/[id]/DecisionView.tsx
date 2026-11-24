"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { decisionFigures, EventList, LoanReceipt, RuleResults } from "@/components/app/LoanParts";
import { NoteField } from "@/components/app/NoteField";
import { ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Field, Figure, Figures, LedgerRow, PageHead, Tag } from "@/components/ui";
import { api, failureMessage } from "@/lib/api/client";
import { dateTime, money, monthlyRate, toPaise, type Detail, type Recommendation } from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

export function headline(d: Detail): { title: string; subtitle: string } {
  const a = d.application;
  const ev = d.evaluation;
  const asked = `${a.borrower_name} asked for ${money(a.amount_paise)}.`;
  const mf02 = ev?.results.find((r) => r.code === "MF-02");
  const amount = d.decision?.approved_paise ?? d.decision?.recommended_paise;
  if (a.status === "rejected") return { title: `${asked} Declined.`, subtitle: d.decision?.checker_note ?? "Declined by the checker." };
  if (a.status === "approved") return { title: `${asked} Approved as asked.`, subtitle: "Every origination rule passes at the amount asked for." };
  if (a.status === "approved_modified" || (amount && amount !== a.amount_paise))
    return {
      title: `${asked} We offered ${money(amount)}.`,
      subtitle: `Approve with modified amount. ${mf02?.message ?? ""} MF-02 caps repayments (${mf02?.anchor ?? "CF para 55"}).`,
    };
  if (ev?.outcome === "pass") return { title: `${asked} Every rule passes.`, subtitle: "Recommend it to a checker, who signs off as the second person." };
  if (ev?.outcome === "refer")
    return { title: `${asked} A fact is missing.`, subtitle: "A missing fact refers the application to a person. Fill it in and the rules run again." };
  if (ev?.offer)
    return {
      title: `${asked} It fits at ${money(ev.offer.amount_paise)}.`,
      subtitle: `${mf02?.message ?? ""} The largest amount that fits is ${money(ev.offer.amount_paise)}.`,
    };
  return { title: `${asked} No amount fits.`, subtitle: mf02?.message ?? "A rule fails at every amount." };
}

export function DecisionView() {
  const { id } = useParams<{ id: string }>();
  const detail = useApi<Detail>(`/loans/applications/${id}`);
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return <Loading />;
  const d = detail.data;
  const a = d.application;
  const ev = d.evaluation;
  const head = headline(d);
  const other = d.final_evaluation ?? d.recommended_evaluation;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 03 · Decision · ${a.ref} · ${dateTime(a.updated_at)} IST`}
        title={head.title}
        subtitle={head.subtitle}
        actions={
          <Button variant="secondary" href={`/officer/decisions/${a.id}/kfs`}>
            Key facts
          </Button>
        }
      />
      <Figures>
        {decisionFigures(d).map((f) => (
          <Figure key={f.label} label={f.label} value={f.value} note={f.note} />
        ))}
      </Figures>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          {ev ? (
            <Card
              eyebrow={`${ev.results.length} rules in force · as of ${formatDate(ev.on_date)}`}
              title={`Rules at ${money(ev.amount_paise)}`}
              tag={<Tag tone={ev.outcome === "pass" ? "pass" : ev.outcome === "fail" ? "fail" : "refer"}>{ev.outcome}</Tag>}
            >
              <RuleResults results={ev.results} at={money(ev.amount_paise)} />
              {ev.offer && !other ? (
                <div className="flex flex-col pt-4">
                  <p className="type-label pt-2 text-stamp">The largest amount that fits</p>
                  <LedgerRow id="E_max" title="Largest new EMI" source="limit × monthly income − existing repayments" value={money(ev.offer.e_max_paise)} />
                  <LedgerRow id="L_max" title="Largest loan for that EMI" source={`${a.tenor_months} months at ${monthlyRate(a.rate_bps_month)}`} value={`≈ ${ev.offer.l_max_exact}`} />
                  <LedgerRow
                    id="MF-02"
                    title={`Repayments within the limit, at ${money(ev.offer.amount_paise)}`}
                    source={ev.offer.rounding}
                    value={`${ev.offer.ratio_percent}%`}
                    status={ev.offer.outcome === "pass" ? "pass" : "fail"}
                  />
                </div>
              ) : null}
            </Card>
          ) : null}
          {other ? (
            <Card eyebrow={`Run again at the decided amount · ${formatDate(other.on_date)}`} title={`Rules at ${money(other.amount_paise)}`} tag={<Tag tone="pass">{other.outcome}</Tag>}>
              <RuleResults results={other.results} at={money(other.amount_paise)} />
            </Card>
          ) : null}
        </div>
        <div className="flex min-w-0 flex-col gap-7 lg:w-[380px] lg:shrink-0">
          <LoanReceipt d={d} className="self-center lg:self-stretch" />
          {a.status === "evaluated" && ev ? <RecommendCard d={d} onDone={detail.reload} /> : null}
          {a.status === "evaluated" && ev?.outcome === "refer" ? <FactsCard d={d} onDone={detail.reload} /> : null}
          {d.decision ? <NotesCard d={d} /> : null}
          <Card eyebrow="Step history" title="What happened, in order">
            <EventList events={d.events} />
          </Card>
        </div>
      </div>
    </div>
  );
}

function NotesCard({ d }: { d: Detail }) {
  const dec = d.decision!;
  return (
    <Card eyebrow="Four eyes" title="Notes">
      <dl className="flex flex-col gap-3 pt-3">
        <div>
          <dt className="type-label text-muted">{`Officer · ${dec.officer_name ?? ""}`}</dt>
          <dd className="type-small text-ink-2">{dec.officer_note ?? "No note."}</dd>
        </div>
        <div>
          <dt className="type-label text-muted">{`Checker · ${dec.checker_name ?? "not decided yet"}`}</dt>
          <dd className="type-small text-ink-2">{dec.checker_note ?? (dec.decided_at ? "No note." : "Waiting for the checker.")}</dd>
        </div>
      </dl>
    </Card>
  );
}

function RecommendCard({ d, onDone }: { d: Detail; onDone: () => void }) {
  const ev = d.evaluation!;
  const choices: { key: Recommendation; label: string; enabled: boolean; why: string }[] = [
    { key: "approve", label: `Approve at ${money(d.application.amount_paise)}`, enabled: ev.outcome === "pass", why: "Every rule must pass." },
    {
      key: "approve_modified",
      label: ev.offer ? `Approve at ${money(ev.offer.amount_paise)}` : "Approve with modified amount",
      enabled: Boolean(ev.offer),
      why: "Only when a smaller amount fits.",
    },
    { key: "reject", label: "Recommend declining", enabled: true, why: "Needs a note." },
  ];
  const [choice, setChoice] = useState<Recommendation>(choices.find((c) => c.enabled)!.key);
  const [amount, setAmount] = useState(ev.offer ? String(ev.offer.amount_paise / 100) : "");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/loans/applications/${d.application.id}/recommend`, {
        recommendation: choice,
        amount_paise: choice === "approve_modified" ? toPaise(amount) : null,
        note: note || null,
      });
      onDone();
    } catch (e) {
      setError(failureMessage(e));
      setBusy(false);
    }
  }

  return (
    <Card eyebrow="Your step" title="Recommend to a checker">
      <div className="flex flex-col gap-4 pt-3">
        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">Recommendation</legend>
          {choices.map((c) => (
            <label key={c.key} className={`flex items-start gap-2.5 ${c.enabled ? "" : "opacity-50"}`}>
              <input type="radio" name="rec" className="mt-1 accent-[var(--stamp)]" disabled={!c.enabled} checked={choice === c.key} onChange={() => setChoice(c.key)} />
              <span className="flex flex-col">
                <span className="type-body-medium text-ink">{c.label}</span>
                <span className="type-caption text-muted">{c.why}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {choice === "approve_modified" ? (
          <Field label="Amount (₹)" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} hint="The rules run again at this amount before it is sent." />
        ) : null}
        <NoteField label="Note for the checker" value={note} onChange={setNote} hint={choice === "reject" ? "Required to recommend declining." : "Optional."} />
        {error ? <ErrorState title="Not sent" message={error} /> : null}
        <Button onClick={() => void send()} disabled={busy}>
          {busy ? "Sending" : "Send to the checker"}
        </Button>
        <p className="type-caption text-muted">A checker who is not you makes the decision.</p>
      </div>
    </Card>
  );
}

function FactsCard({ d, onDone }: { d: Detail; onDone: () => void }) {
  const a = d.application;
  const [income, setIncome] = useState(a.household_income_annual_paise ? String(a.household_income_annual_paise / 1200) : "");
  const [existing, setExisting] = useState(a.existing_monthly_repayments_paise !== null ? String(a.existing_monthly_repayments_paise / 100) : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save() {
    const monthly = toPaise(income);
    const ex = existing.trim() === "0" ? 0 : toPaise(existing);
    if (monthly === null || ex === null) {
      setError("Enter both amounts in whole rupees.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.patch(`/loans/applications/${a.id}`, {
        household_income_annual_paise: monthly * 12,
        existing_monthly_repayments_paise: ex,
      });
      onDone();
    } catch (e) {
      setError(failureMessage(e));
      setBusy(false);
    }
  }
  return (
    <Card eyebrow="Refer" title="Fill in the missing facts">
      <div className="flex flex-col gap-4 pt-3">
        <Field label="Monthly household income (₹)" inputMode="numeric" value={income} onChange={(e) => setIncome(e.target.value)} />
        <Field label="Existing monthly repayments (₹)" inputMode="numeric" value={existing} onChange={(e) => setExisting(e.target.value)} />
        {error ? <ErrorState title="Not saved" message={error} /> : null}
        <Button variant="secondary" onClick={() => void save()} disabled={busy}>
          {busy ? "Running the rules" : "Save and run the rules"}
        </Button>
      </div>
    </Card>
  );
}
