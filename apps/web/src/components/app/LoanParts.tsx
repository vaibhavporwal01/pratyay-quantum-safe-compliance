"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { DecisionReceipt } from "@/components/trust/DecisionReceipt";
import { Button, Card, Field, LedgerRow, Status, Table, Tag, type Column } from "@/components/ui";
import { api, ApiFailure, failureMessage } from "@/lib/api/client";
import {
  appKind,
  appKindLabel,
  dateTime,
  EVENT_LABEL,
  finalLabel,
  money,
  monthlyRate,
  ratioAt,
  resultKind,
  resultLabel,
  resultSummary,
  resultValue,
  shortDateTime,
  toPaise,
  type AppSummary,
  type Detail,
  type DecisionVerification,
  type Evaluation,
  type Kfs,
  type LoanEvent,
  type Preview,
  type Product,
  type RuleResult,
} from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";
import { ErrorState, Loading } from "./States";

/* ---- rule results ---------------------------------------------------------------------- */

/** One line per rule result, origination first; later stages and not-applicable rules after. */
export function RuleResults({ results, at }: { results: RuleResult[]; at?: string }) {
  const checked = results.filter((r) => r.status === "pass" || r.status === "fail" || r.status === "refer");
  const later = results.filter((r) => r.status === "not_checked");
  const na = results.filter((r) => r.status === "not_applicable");
  return (
    <div className="flex flex-col">
      <GroupHead label="A · Checked at origination" count={checked.length} />
      {checked.map((r) => (
        <ResultRow key={`${r.code}-${at ?? ""}`} r={r} at={at} />
      ))}
      {later.length ? (
        <>
          <GroupHead label="B · Later stages, not checked now" count={later.length} />
          {later.map((r) => (
            <ResultRow key={r.code} r={r} />
          ))}
        </>
      ) : null}
      {na.length ? (
        <>
          <GroupHead label="C · Not applicable to this loan" count={na.length} />
          {na.map((r) => (
            <ResultRow key={r.code} r={r} />
          ))}
        </>
      ) : null}
    </div>
  );
}

function GroupHead({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex items-center gap-3 pt-5 pb-1">
      <p className="type-label whitespace-nowrap text-stamp">{label}</p>
      <span aria-hidden className="h-px flex-1 bg-rule" />
      <p className="type-mono whitespace-nowrap text-muted">{`${count} rule${count === 1 ? "" : "s"}`}</p>
    </div>
  );
}

export function ResultRow({ r, at }: { r: RuleResult; at?: string }) {
  const later = r.status === "not_checked" || r.status === "not_applicable";
  return (
    <LedgerRow
      id={r.code}
      title={at && r.code === "MF-02" ? `${r.title}, at ${at}` : r.title}
      source={`${r.anchor} · v${r.version}${r.missing.length ? ` · ${r.message}` : later ? ` · ${r.message}` : ""}`}
      value={resultValue(r)}
      status={resultKind(r.status)}
      className={later ? "opacity-80" : undefined}
    />
  );
}

/** The quoted paragraph behind a result, for "why" cards. */
export function ParagraphQuote({ r }: { r: RuleResult }) {
  return (
    <blockquote className="border-l-2 border-stamp bg-paper px-4 py-3 type-small text-ink-2">
      <p className="type-label pb-1 text-muted">{r.anchor}</p>
      {r.para_text}
    </blockquote>
  );
}

/* ---- receipt --------------------------------------------------------------------------- */

/** The decision receipt for an application. Unsigned until the trust module lands. */
export function LoanReceipt({ d, verification, className }: { d: Detail; verification?: DecisionVerification; className?: string }) {
  const a = d.application;
  const dec = d.decision;
  const final = d.final_evaluation ?? d.recommended_evaluation;
  const kfs = final?.kfs ?? d.evaluation?.kfs;
  const offered = dec?.approved_paise ?? dec?.recommended_paise ?? null;
  const modified = offered !== null && offered !== a.amount_paise;
  const lines = [
    { label: "Requested", value: money(a.amount_paise), tone: modified ? ("fail" as const) : undefined },
    ...(offered !== null ? [{ label: modified ? "Offered" : "Approved", value: money(offered), tone: "pass" as const }] : []),
    { label: "Interest", value: `${monthlyRate(a.rate_bps_month)}, ${a.tenor_months} months` },
    ...(kfs
      ? [
          { label: "Monthly EMI", value: money(kfs.emi_paise) },
          ...(ratioAt(final ?? d.evaluation) ? [{ label: "Repayments to income", value: `${ratioAt(final ?? d.evaluation)}%` }] : []),
          ...kfs.fees.map((f) => ({ label: f.name, value: money(f.paise) })),
          { label: "Paid to the account", value: money(kfs.net_disbursal_paise) },
          { label: "Total repayment", value: money(kfs.total_payable_paise) },
          { label: "APR", value: `${kfs.apr_percent}%`, tone: "total" as const },
        ]
      : []),
  ];
  const results = (final ?? d.evaluation)?.results ?? [];
  return (
    <DecisionReceipt
      className={className}
      name={a.borrower_name}
      applicationId={a.ref}
      lender="Lender A"
      decidedAt={dec?.decided_at ? `${dateTime(dec.decided_at)} IST` : "Not decided yet"}
      outcome={dec?.outcome ? finalLabel(a.status) : dec ? "With the checker" : "With the officer"}
      lines={lines}
      checks={results.length ? [{ label: "Rules", value: resultSummary(results) }] : []}
      verificationStatus={verification?.status ?? "pending"}
      seal={
        verification?.verified && verification.hash && verification.previous_hash
          ? {
              hash: `${verification.hash.slice(0, 8)}…${verification.hash.slice(-8)}`,
              prev: `${verification.previous_hash.slice(0, 8)}…${verification.previous_hash.slice(-8)}`,
              signature: `${verification.algorithm} signature · ${verification.signature_bytes?.toLocaleString() ?? "N/A"} B · key ${verification.key_id ?? "unknown"}`,
            }
          : undefined
      }
    />
  );
}

/* ---- KFS ------------------------------------------------------------------------------- */

export function kfsRows(kfs: Kfs): [string, string, string?][] {
  return [
    ["Loan amount", money(kfs.amount_paise)],
    ["Tenure", `${kfs.tenor_months} monthly instalments`],
    ["Instalment", money(kfs.emi_paise), `first due ${formatDate(kfs.first_due_on)}`],
    ["Interest rate", `${trimPct(kfs.rate_year_percent)}% a year, reducing`, `${kfs.rate_month_percent}% a month, fixed`],
    ["Total interest", money(kfs.total_interest_paise)],
    ...kfs.fees.map((f): [string, string, string] => [
      f.name,
      money(f.paise),
      `${f.basis}${f.assumed ? " · assumed product fee" : ""}`,
    ]),
    ["Net amount paid out", money(kfs.net_disbursal_paise), "loan amount less fees"],
    ["Total amount to be paid", money(kfs.total_payable_paise), `${kfs.instalments} × ${money(kfs.emi_paise)}`],
    ["Annual percentage rate", `${kfs.apr_percent}%`, "see the computation sheet"],
  ];
}

function trimPct(s: string): string {
  return s.replace(/\.00$/, "");
}

/** Numbered KFS rows: label, value, note. Stacks on phones. */
export function KfsTable({ rows, start = 1 }: { rows: [string, string, string?][]; start?: number }) {
  return (
    <ol className="flex flex-col">
      {rows.map(([label, value, note], i) => (
        <li key={label} className="grid grid-cols-[28px_1fr] gap-x-3 border-b border-rule-2 py-2.5 sm:grid-cols-[28px_1fr_200px_1fr]">
          <span className="type-mono text-muted">{start + i}</span>
          <span className="type-body-medium text-ink">{label}</span>
          <span className="col-start-2 type-mono text-ink sm:col-start-auto">{value}</span>
          {note ? <span className="col-start-2 type-caption text-muted sm:col-start-auto">{note}</span> : <span />}
        </li>
      ))}
    </ol>
  );
}

export function AprSheet({ kfs }: { kfs: Kfs }) {
  const lines = [
    ["Net received", money(kfs.net_disbursal_paise)],
    ["Paid back", `${kfs.instalments} × ${money(kfs.emi_paise)} = ${money(kfs.total_payable_paise)}`],
    ["Monthly IRR", `${kfs.monthly_irr_percent}%`],
    ["APR", `12 × ${kfs.monthly_irr_percent}% = ${kfs.apr_percent}%`],
  ];
  return (
    <div className="flex flex-col gap-2">
      <dl className="flex flex-col gap-1 overflow-x-auto border border-rule bg-paper px-4 py-3 type-mono text-ink-2">
        {lines.map(([k, v]) => (
          <div key={k} className="flex gap-4 whitespace-nowrap">
            <dt className="w-28 shrink-0">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="type-caption text-muted">
        {kfs.apr_method} The IRR uses the unrounded EMI ({kfs.emi_exact}); you pay the rounded one.
      </p>
    </div>
  );
}

/** "Valid until 30 Nov 2026 (3 working days, KF-01)" */
export function validityText(kfs: Kfs): string {
  if (!kfs.valid_until) return "No validity rule in force";
  return `Valid until ${formatDate(kfs.valid_until)}, ${kfs.validity_working_days} working day${
    kfs.validity_working_days === 1 ? "" : "s"
  } (${kfs.validity_anchor ?? "KF-01"})`;
}

/* ---- events ---------------------------------------------------------------------------- */

export function EventList({ events, verification }: { events: LoanEvent[]; verification?: DecisionVerification }) {
  return (
    <ol className="flex flex-col">
      {events.map((e) => (
        <li key={e.id} className="flex items-start gap-3 border-b border-rule-2 py-3">
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <p className="type-body-medium text-ink">{EVENT_LABEL[e.action] ?? e.action}</p>
            <p className="type-caption text-muted">
              {`${dateTime(e.created_at)} · ${e.actor_name ?? "Unknown"}`}
              {eventDetail(e) ? ` · ${eventDetail(e)}` : ""}
            </p>
          </div>
          {e.action === "decided" ? <Status status={verification?.status === "verified" ? "pass" : verification?.status === "failed" ? "fail" : "pending"} label={verification?.status === "verified" ? "Signature verified" : verification?.status === "failed" ? "Verification failed" : "Signature pending"} /> : null}
        </li>
      ))}
    </ol>
  );
}

function eventDetail(e: LoanEvent): string {
  const m = e.meta;
  if (e.action === "evaluated") return `${m.outcome} at ${money(m.amount_paise as number)}`;
  if (e.action === "recommended") return `${String(m.recommendation).replace("_", " ")}${m.amount_paise ? ` at ${money(m.amount_paise as number)}` : ""}`;
  if (e.action === "decided") return `${String(m.outcome).replace("_", " ")}${m.amount_paise ? ` at ${money(m.amount_paise as number)}` : ""}`;
  return "";
}

/* ---- application table ----------------------------------------------------------------- */

export function ApplicationTable({ apps, href, caption }: { apps: AppSummary[]; href: (a: AppSummary) => string; caption: string }) {
  const columns: Column<AppSummary>[] = [
    {
      key: "ref",
      header: "ID",
      width: 130,
      kind: "mono",
      render: (a) => (
        <Link href={href(a)} className="text-ink-2 underline-offset-2 hover:underline">
          {a.ref}
        </Link>
      ),
    },
    { key: "name", header: "Borrower", width: 150, kind: "primary", render: (a) => a.borrower_name },
    { key: "amount", header: "Amount", width: 100, kind: "mono", render: (a) => money(a.approved_paise ?? a.amount_paise) },
    { key: "stage", header: "Stage", width: 130, render: (a) => STAGE[a.status] },
    { key: "rules", header: "Rules", width: 220, render: (a) => ruleNote(a) },
    { key: "updated", header: "Updated", width: 110, kind: "mono", render: (a) => shortDateTime(a.updated_at) },
    { key: "status", header: "Status", kind: "node", render: (a) => <Status status={appKind(a)} label={appKindLabel(a)} /> },
  ];
  return (
    <div className="overflow-x-auto">
      <Table className="min-w-[960px]" caption={caption} columns={columns} rows={apps} rowKey={(a) => a.id} />
    </div>
  );
}

const STAGE: Record<AppSummary["status"], string> = {
  evaluated: "With officer",
  recommended: "With checker",
  approved: "Decided",
  approved_modified: "Decided",
  rejected: "Decided",
};

export function ruleNote(a: AppSummary): string {
  if (a.status === "approved_modified") return `cut to ${money(a.approved_paise)} to fit MF-02`;
  if (a.status === "rejected") return a.first_problem ? `${a.first_problem}, declined` : "declined";
  if (a.first_problem) return a.offer_paise ? `${a.first_problem}, fits at ${money(a.offer_paise)}` : a.first_problem;
  return a.outcome ? "all origination rules pass" : "not checked yet";
}

/* ---- the application form (borrower and officer) ---------------------------------------- */

type FormState = { name: string; product: string; amount: string; tenor: string; purpose: string; income: string; existing: string };

/**
 * Amount, tenor, purpose, monthly household income and existing repayments, with live checks
 * from POST /loans/preview (nothing saved). Rate and fees come from the product.
 */
export function ApplicationForm({
  asOfficer,
  onSubmitted,
  side,
}: {
  asOfficer: boolean;
  onSubmitted: (d: Detail) => void;
  side?: ReactNode;
}) {
  const products = useApi<Product[]>("/loans/products");
  const [f, setF] = useState<FormState>({ name: "", product: "MFL", amount: "", tenor: "", purpose: "", income: "", existing: "" });
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFailure | Error | null>(null);
  const [touched, setTouched] = useState(false);
  const product = products.data?.find((p) => p.code === f.product);
  const tenor = Number(f.tenor) || product?.tenors.at(-1) || null;
  const amount = toPaise(f.amount);
  const monthly = f.income.trim() ? toPaise(f.income) : null;
  const existing = f.existing.trim() === "0" ? 0 : f.existing.trim() ? toPaise(f.existing) : null;
  const body = {
    product: f.product,
    amount_paise: amount,
    tenor_months: tenor,
    household_income_annual_paise: monthly === null ? null : monthly * 12,
    existing_monthly_repayments_paise: existing,
  };
  const preview = usePreview(product ? body : null);
  const errors = {
    name: asOfficer && !f.name.trim() ? "The borrower's name is needed." : undefined,
    amount: amount === null ? "Enter the amount in rupees, for example 80,000." : undefined,
    income: f.income.trim() && monthly === null ? "Enter a whole amount in rupees." : undefined,
    existing: f.existing.trim() && existing === null ? "Enter a whole amount in rupees, or 0." : undefined,
  };
  const valid = !Object.values(errors).some(Boolean);

  async function submit() {
    setTouched(true);
    if (!valid) return;
    setBusy(true);
    setFailure(null);
    try {
      const d = await api.post<Detail>("/loans/applications", {
        ...body,
        purpose: f.purpose || null,
        borrower_name: asOfficer ? f.name.trim() : undefined,
      });
      onSubmitted(d);
    } catch (e) {
      setFailure(e instanceof Error ? e : new Error(failureMessage(e)));
      setBusy(false);
    }
  }

  if (products.error) return <ErrorState message={products.error} onRetry={products.reload} />;
  if (!products.data) return <Loading />;
  const set = (k: keyof FormState) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
      <Card eyebrow="§ 1 · Application" title="The loan and the household" className="min-w-0 flex-1">
        <form
          className="flex flex-col gap-5 pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          {asOfficer ? (
            <Field label="1.1 · Borrower's name" value={f.name} onChange={set("name")} error={touched ? errors.name : undefined} autoComplete="off" />
          ) : null}
          <div className="grid gap-5 sm:grid-cols-2">
            <SelectField label="1.2 · Product" value={f.product} onChange={set("product")}>
              {products.data.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name}
                </option>
              ))}
            </SelectField>
            <SelectField label="1.3 · Tenor" value={String(tenor ?? "")} onChange={set("tenor")}>
              {(product?.tenors ?? []).map((t) => (
                <option key={t} value={t}>
                  {`${t} months`}
                </option>
              ))}
            </SelectField>
          </div>
          <Field
            label="1.4 · Amount asked for (₹)"
            inputMode="numeric"
            placeholder="80,000"
            value={f.amount}
            onChange={set("amount")}
            error={touched || f.amount ? errors.amount : undefined}
            hint={product ? `${monthlyRate(product.rate_bps_month)} on a reducing balance. Fees are listed on the key facts.` : undefined}
          />
          <Field label="1.5 · Purpose" value={f.purpose} onChange={set("purpose")} placeholder="Two sewing machines for a tailoring unit" />
          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              label="1.6 · Monthly household income (₹)"
              inputMode="numeric"
              placeholder="22,000"
              value={f.income}
              onChange={set("income")}
              error={errors.income}
              hint="Everyone who earns. Income the loan is expected to produce is not counted (CF para 55)."
            />
            <Field
              label="1.7 · Existing monthly repayments (₹)"
              inputMode="numeric"
              placeholder="7,500"
              value={f.existing}
              onChange={set("existing")}
              error={errors.existing}
              hint="All loans of the household, principal and interest (CF para 56)."
            />
          </div>
          {monthly !== null ? (
            <dl className="flex flex-col border border-rule bg-paper px-4 py-2">
              {[
                ["Household income counted", `${money(monthly)} a month`],
                ["Per year, for MF-01", money(monthly * 12)],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 border-b border-rule-2 py-2 last:border-0">
                  <dt className="type-small text-ink-2">{k}</dt>
                  <span aria-hidden className="leader" />
                  <dd className="type-mono text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {failure ? (
            <ErrorState
              title="Not submitted"
              message={failure.message}
              problems={failure instanceof ApiFailure ? failure.problems : []}
            />
          ) : null}
          <div className="flex flex-wrap items-center justify-end gap-3">
            {touched && !valid ? <p className="type-small text-fail">Fix the marked fields to continue.</p> : null}
            <Button type="submit" disabled={busy}>
              {busy ? "Submitting" : "Submit and run the rules"}
            </Button>
          </div>
        </form>
      </Card>
      <div className="flex min-w-0 flex-col gap-7 lg:w-[380px] lg:shrink-0">
        <LiveChecks state={preview} />
        {side}
      </div>
    </div>
  );
}

function SelectField({ label, value, onChange, children }: { label: string; value: string; onChange: (e: { target: { value: string } }) => void; children: ReactNode }) {
  return (
    <label className="flex w-full flex-col gap-1.5">
      <span className="type-label text-ink-2">{label}</span>
      <select
        value={value}
        onChange={onChange}
        className="h-11 w-full rounded-[2px] border border-rule bg-white px-3 type-body text-ink focus:border-stamp focus:outline-none"
      >
        {children}
      </select>
    </label>
  );
}

type PreviewState = { data?: Preview; error?: string; loading: boolean };

/** Debounced POST /loans/preview. Pass null to wait. */
function usePreview(body: object | null): PreviewState {
  const key = body ? JSON.stringify(body) : null;
  const [state, setState] = useState<{ key: string | null; data?: Preview; error?: string }>({ key: null });
  useEffect(() => {
    if (!key) return;
    let live = true;
    const t = setTimeout(() => {
      api
        .post<Preview>("/loans/preview", JSON.parse(key))
        .then((data) => live && setState({ key, data }))
        .catch((e) => live && setState({ key, error: failureMessage(e) }));
    }, 400);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [key]);
  const current = state.key === key;
  return { data: current ? state.data : undefined, error: current ? state.error : undefined, loading: key !== null && !current };
}

function LiveChecks({ state }: { state: PreviewState }) {
  const checked = state.data?.results.filter((r) => r.status !== "not_checked" && r.status !== "not_applicable") ?? [];
  return (
    <Card eyebrow="Checked as you type · not saved" title="Live checks" tag={state.data ? <Tag tone="stamp">{`as of ${formatDate(state.data.on_date)}`}</Tag> : undefined}>
      {state.error ? (
        <div className="pt-3">
          <ErrorState message={state.error} />
        </div>
      ) : !state.data ? (
        <Loading label="Running the rules" />
      ) : (
        <div className="flex flex-col">
          {checked.map((r) => (
            <div key={r.code} className="flex items-start gap-3 border-b border-rule-2 py-3">
              <p className="w-12 shrink-0 type-mono-medium text-ink">{r.code}</p>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <p className="type-small-medium text-ink">{r.title}</p>
                <p className="type-caption text-muted">{r.message}</p>
              </div>
              <Status status={resultKind(r.status)} label={resultLabel(r.status)} />
            </div>
          ))}
          {state.data.offer ? (
            <p className="pt-3 type-small text-ink-2">
              {`The largest amount that fits MF-02 is ${money(state.data.offer.amount_paise)}, with an EMI of ${money(state.data.offer.emi_paise)}.`}
            </p>
          ) : null}
          <p className="pt-3 type-caption text-muted">A missing fact gives Refer, never a guessed pass. The final check runs when you submit.</p>
        </div>
      )}
    </Card>
  );
}

/** Headline figures for a decision. */
export function decisionFigures(d: Detail): { label: string; value: string; note: string }[] {
  const a = d.application;
  const offered = d.decision?.approved_paise ?? d.decision?.recommended_paise ?? d.evaluation?.offer?.amount_paise ?? null;
  const at: Evaluation | null = d.final_evaluation ?? d.recommended_evaluation ?? d.evaluation;
  const kfs = at?.kfs;
  const mf02 = at?.results.find((r) => r.code === "MF-02");
  return [
    { label: "Requested", value: money(a.amount_paise), note: `${a.tenor_months} months at ${monthlyRate(a.rate_bps_month)}` },
    {
      label: offered !== null && offered !== a.amount_paise ? "Offered" : "Amount",
      value: money(offered ?? a.amount_paise),
      note: offered !== null && offered !== a.amount_paise ? "largest fit, rounded down" : "as asked",
    },
    { label: "Monthly EMI", value: kfs ? money(kfs.emi_paise) : "Not computed", note: `for ${a.tenor_months} months` },
    {
      label: "Repayments to income",
      value: mf02?.values.ratio_percent ? `${mf02.values.ratio_percent}%` : "Not computed",
      note: mf02?.values.repayments ? `${mf02.values.repayments} of ${mf02.values.monthly_income}` : mf02?.message ?? "MF-02 not in force",
    },
  ];
}
