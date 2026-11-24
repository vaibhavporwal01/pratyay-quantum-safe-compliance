"use client";

import { Status } from "@/components/ui";
import { money, type Detail, type Kfs } from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { AprSheet, KfsTable, kfsRows, validityText } from "./LoanParts";

/** The full KFS: Part 1 figures, Part 2 terms the engine knows, the APR sheet and signatures. */
export function KfsDocument({ d, kfs }: { d: Detail; kfs: Kfs }) {
  const a = d.application;
  const results = (d.final_evaluation ?? d.evaluation)?.results ?? [];
  const mf04 = results.find((r) => r.code === "MF-04");
  const mf06 = results.find((r) => r.code === "MF-06");
  const part2: [string, string, string?][] = [
    ["Validity of this statement", validityText(kfs), kfs.notes[0]],
    ["Pre-payment charge", "Nil", mf04 ? `${mf04.anchor}` : "product setting"],
    ...(mf06 ? [["Delayed payment charge", mf06.title, `${mf06.anchor} · checked at servicing`] as [string, string, string]] : []),
  ];
  return (
    <article className="flex flex-col gap-6 border border-rule bg-white px-5 py-6 sm:px-9 sm:py-8">
      <header className="flex flex-col gap-3 border-b-2 border-ink pb-5 sm:flex-row sm:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="type-label text-muted">Lender A · Key Facts Statement</p>
          <h2 className="type-title-l text-ink">{`${a.product_name} · ${a.ref}`}</h2>
          <p className="type-small text-ink-2">
            {`Borrower: ${a.borrower_name}${a.household_income_annual_paise ? ` · Household income ${money(a.household_income_annual_paise / 12)} a month` : ""}`}
          </p>
        </div>
        {/* HOOK(Pulkit): the signing stamp goes here once ledger.append signs the KFS record. */}
        <Status status="pending" label="Signature pending" />
      </header>
      <section className="flex flex-col gap-1">
        <h3 className="type-label text-stamp">Part 1 · Interest and fees</h3>
        <KfsTable rows={kfsRows(kfs)} />
      </section>
      <section className="flex flex-col gap-1">
        <h3 className="type-label text-stamp">Part 2 · Other terms</h3>
        <KfsTable rows={part2} start={kfsRows(kfs).length + 1} />
        <p className="pt-2 type-caption text-muted">Only terms with a rule or product setting behind them are listed. Cooling-off and grievance terms are not modelled yet.</p>
      </section>
      <section className="flex flex-col gap-2">
        <h3 className="type-label text-stamp">APR computation sheet</h3>
        <AprSheet kfs={kfs} />
      </section>
      <footer className="grid gap-6 sm:grid-cols-2">
        <div className="flex flex-col gap-1 border-t border-ink pt-3">
          <p className="type-label text-muted">Borrower</p>
          <p className="type-body-medium text-ink">{a.borrower_name}</p>
          <p className="type-caption text-muted">Not accepted yet. Acceptance by one-time code arrives with sign-in.</p>
        </div>
        <div className="flex flex-col gap-1 border-t border-ink pt-3">
          <p className="type-label text-muted">Lender</p>
          <p className="type-body-medium text-ink">Lender A</p>
          <p className="type-caption text-muted">{`Issued ${formatDate(kfs.issued_on)}. Signature pending: verification available when signing is enabled.`}</p>
        </div>
      </footer>
    </article>
  );
}
