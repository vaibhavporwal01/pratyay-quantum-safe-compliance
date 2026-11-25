"use client";

import { useEffect, useState } from "react";
import { DecisionReceipt } from "@/components/trust/DecisionReceipt";
import { Icon } from "@/components/ui/icons";
import { LedgerRow } from "@/components/ui/LedgerRow";
import { Tag } from "@/components/ui/Tag";
import { money, monthlyRate, resultKind, type Preview, type RuleResult } from "@/lib/api/loans";

/**
 * The landing page's worked example, APP-2026-0142 (fictional). Every figure comes from the
 * engine through GET /api/v1/loans/worked-example (read only, cached by the API); none is typed
 * into the page. If the API is down, a short neutral message shows instead.
 */
export type WorkedExampleData = {
  ref: string;
  purpose: string;
  on_date: string;
  facts: {
    amount_paise: number;
    tenor_months: number;
    rate_bps_month: number;
    household_income_annual_paise: number;
    existing_monthly_repayments_paise: number;
    product_name: string;
  };
  asked: Preview;
  at_offer: Preview | null;
};

export const UNAVAILABLE = "The worked example is unavailable right now.";

let pending: Promise<WorkedExampleData> | null = null;

/** Tests only: forget the shared request. */
export function resetWorkedExample() {
  pending = null;
}

function load(): Promise<WorkedExampleData> {
  pending ??= fetch("/api/v1/loans/worked-example", { credentials: "omit" }).then((r) => {
    if (!r.ok) throw new Error(String(r.status));
    return r.json() as Promise<WorkedExampleData>;
  });
  pending.catch(() => {
    pending = null;
  });
  return pending;
}

type State = { data?: WorkedExampleData; failed?: boolean };

/** One request shared by every part of the page. */
export function useWorkedExample(): State {
  const [state, setState] = useState<State>({});
  useEffect(() => {
    let live = true;
    load()
      .then((data) => live && setState({ data }))
      .catch(() => live && setState({ failed: true }));
    return () => {
      live = false;
    };
  }, []);
  return state;
}

const checked = (r: RuleResult) => r.status === "pass" || r.status === "fail" || r.status === "refer";
/** The ratio rule (it carries ratio_percent), found by its values, not by its code. */
const ratioOf = (p: Preview | null | undefined) => p?.results.find((r) => r.values.ratio_percent !== undefined);

export function dateLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function Fallback({ className = "" }: { className?: string }) {
  return (
    <p className={`flex items-start gap-2.5 rounded-[2px] border border-rule bg-white px-3.5 py-3 type-small text-ink-2 ${className}`}>
      <Icon name="info-circle" size={16} className="mt-px shrink-0 text-ink-2" />
      {UNAVAILABLE}
    </p>
  );
}

function Pending({ className = "" }: { className?: string }) {
  return <p className={`type-small text-muted ${className}`}>Running the engine on the worked example.</p>;
}

/** Hero: the decision receipt and what it shows. */
export function ExampleReceipt() {
  const { data, failed } = useWorkedExample();
  if (failed) return <Fallback className="self-start sm:w-[360px]" />;
  if (!data) return <Pending className="sm:w-[360px]" />;
  const final = data.at_offer ?? data.asked;
  const kfs = final.kfs;
  const ratio = ratioOf(data.asked);
  const ratioAtOffer = ratioOf(data.at_offer);
  const offer = data.asked.offer;
  const later = final.results.filter((r) => r.status === "not_checked").length;
  const passed = final.results.filter((r) => r.status === "pass").length;
  const fee = kfs?.fees[0];
  const annotations: [string, string][] = [];
  if (ratio && ratio.status === "fail")
    annotations.push(["A", `The request failed ${ratio.code}: repayments would reach ${ratio.values.ratio_percent}% of household income.`]);
  if (offer && ratioAtOffer)
    annotations.push(["B", `The offer is the largest loan that fits: ${money(offer.amount_paise)} at ${ratioAtOffer.values.ratio_percent}%.`]);
  if (kfs) annotations.push(["C", `The fee is counted in the APR, so ${kfs.rate_year_percent}% interest shows as ${kfs.apr_percent}%.`]);
  annotations.push(["D", "Signing with ML-DSA-65 comes with the trust layer. Until then the receipt says Signature pending."]);
  return (
    <>
      <DecisionReceipt
        className="shrink-0 self-center sm:self-start"
        name="Rekha K."
        applicationId={data.ref}
        lender="Lender A"
        decidedAt={dateLabel(data.on_date)}
        outcome={offer ? "Approve with modified amount" : final.outcome === "pass" ? "Approve" : "Refer"}
        lines={[
          { label: "Requested", value: money(data.facts.amount_paise), tone: offer ? "fail" : undefined },
          ...(offer ? [{ label: "Offered", value: money(offer.amount_paise), tone: "pass" as const }] : []),
          { label: "Interest", value: `${monthlyRate(data.facts.rate_bps_month)}, ${data.facts.tenor_months} months` },
          ...(kfs
            ? [
                { label: "Monthly EMI", value: money(kfs.emi_paise) },
                ...(ratioAtOffer ? [{ label: "Repayments to income", value: `${ratioAtOffer.values.ratio_percent}% of ${ratioAtOffer.values.limit_percent}%` }] : []),
                ...(fee ? [{ label: fee.name, value: money(fee.paise) }] : []),
                { label: "Paid to her account", value: money(kfs.net_disbursal_paise) },
                { label: "Total repayment", value: money(kfs.total_payable_paise) },
                { label: "APR", value: `${kfs.apr_percent}%`, tone: "total" as const },
              ]
            : []),
        ]}
        checks={[{ label: "Rules", value: `${passed} pass · ${later} later stage` }]}
      />
      <ol aria-label="What the receipt shows" className="flex flex-col gap-3 sm:flex-1 sm:justify-between xl:w-[168px] xl:flex-none">
        {annotations.map(([letter, text]) => (
          <li key={letter} className="flex gap-2.5 xl:flex-col xl:gap-2">
            <span className="flex items-center gap-2 xl:w-full">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-[2px] border border-stamp type-mono-medium text-stamp">
                {letter}
              </span>
              <span aria-hidden className="hidden h-px flex-1 border-t border-dashed border-stamp xl:block" />
            </span>
            <span className="type-small text-ink-2">{text}</span>
          </li>
        ))}
      </ol>
    </>
  );
}

/** "Rules in force" for the hero figures: how many the engine used on the example's date. */
export function RulesInForce() {
  const { data } = useWorkedExample();
  return <>{data ? String(data.asked.rules_used.length) : "·"}</>;
}

export function MonoBox({ lines }: { lines: readonly string[] }) {
  return (
    <div className="flex w-full flex-col gap-1 overflow-x-auto rounded-[2px] border border-rule-2 bg-paper-2 px-3.5 py-3 type-mono text-ink-2">
      {lines.map((l) => (
        <p key={l} className="whitespace-pre">
          {l}
        </p>
      ))}
    </div>
  );
}

/** Steps 02 and 03 of "How it decides", from the engine's run on the worked example. */
export function StepLines({ step }: { step: "check" | "offer" }) {
  const { failed } = useWorkedExample();
  const lines = useStepLines();
  if (failed) return <MonoBox lines={[UNAVAILABLE]} />;
  return <MonoBox lines={lines ? lines[step] : ["Running the engine."]} />;
}

/** Mono lines for steps 02 and 03 of "How it decides". */
function useStepLines(): { check: string[]; offer: string[] } | null {
  const { data } = useWorkedExample();
  if (!data) return null;
  const check = data.asked.results.filter(checked).slice(0, 3).map((r) => {
    const v = r.values.ratio_percent !== undefined ? `${r.values.ratio_percent}%` : r.values.household_income_annual ?? r.values.prepayment_charge ?? "";
    return `${r.code.padEnd(6)} ${String(v).padEnd(14)} ${r.status.toUpperCase()}`;
  });
  const ratio = ratioOf(data.asked);
  const offer = data.asked.offer;
  const lines =
    ratio && offer
      ? [
          `E_max = ${ratio.values.limit_percent}% x ${ratio.values.monthly_income}`,
          `        - ${ratio.values.existing_repayments}`,
          `      = ${ratio.values.e_max} a month`,
          `L_max = ${ratio.values.l_max} -> ${money(offer.amount_paise)}`,
        ]
      : ["No offer needed: every limit passes."];
  return { check, offer: lines };
}

function summary(r: RuleResult): string {
  const v = r.values;
  if (v.ratio_percent !== undefined) return `${v.repayments} = ${v.ratio_percent}%`;
  if (v.household_income_annual !== undefined) return `${v.household_income_annual} ≤ ${v.limit}`;
  if (v.apr_percent !== undefined) return `APR ${v.apr_percent}%`;
  if (v.valid_until !== undefined) return `until ${dateLabel(String(v.valid_until))}`;
  if (v.prepayment_charge !== undefined) return v.prepayment_charge === "₹0" ? "Nil" : String(v.prepayment_charge);
  return "";
}

/** § 02: the story's figures, from the engine's facts and values. */
export function ExampleStory() {
  const { data, failed } = useWorkedExample();
  if (!data) {
    return (
      <>
        <h2 id="example-title" className="type-title-l md:type-title-xl text-ink">
          A microfinance application, rule by rule.
        </h2>
        {failed ? <Fallback /> : <Pending />}
      </>
    );
  }
  const ratio = ratioOf(data.asked);
  return (
    <>
      <h2 id="example-title" className="type-title-l md:type-title-xl text-ink">
        Rekha asked for {money(data.facts.amount_paise)} to buy two sewing machines.
      </h2>
      <p className="type-body md:type-body-l text-ink-2">
        She runs a tailoring business from home in a town in Bihar. Her husband drives an e-rickshaw.
        {ratio ? ` The household earns ${ratio.values.monthly_income} a month and already repays ${ratio.values.existing_repayments} to other lenders.` : ""}
      </p>
      <p className="type-body text-ink-2">
        Her own estimate of extra income from the machines is kept on file but not counted, because the Directions
        exclude income the loan is expected to produce.
      </p>
      <div className="flex flex-col border border-rule bg-white px-[18px] pt-1 pb-2.5">
        <p className="border-b border-ink py-2.5 type-label text-muted">Household on file</p>
        <dl>
          {[
            ["Members", "Rekha, Mahesh, 2 children"],
            ["Income", `${money(data.facts.household_income_annual_paise)} a year`],
            ["Existing EMIs", `${money(data.facts.existing_monthly_repayments_paise)} a month`],
            ["Request", `${money(data.facts.amount_paise)} · ${data.facts.tenor_months} months · ${monthlyRate(data.facts.rate_bps_month)}`],
          ].map(([k, v], i, all) => (
            <div key={k} className={`flex gap-3 py-[9px] ${i < all.length - 1 ? "border-b border-rule-2" : ""}`}>
              <dt className="w-[110px] shrink-0 type-small text-ink-2">{k}</dt>
              <dd className="min-w-0 type-mono text-ink">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </>
  );
}

/** § 02: rule by rule, as the engine returned it. */
export function ExampleLedger() {
  const { data, failed } = useWorkedExample();
  if (failed) return <Fallback />;
  if (!data) return <Pending />;
  const asked = data.asked.results.filter(checked);
  const ratio = ratioOf(data.asked);
  const ratioAtOffer = ratioOf(data.at_offer);
  const offer = data.asked.offer;
  const kfs = (data.at_offer ?? data.asked).kfs;
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink py-3.5 text-muted">
        <p className="type-label">{data.ref} · rule by rule</p>
        <p className="type-mono">As of {dateLabel(data.on_date)}</p>
      </div>
      {asked.map((r) => (
        <LedgerRow
          key={`${r.code}-asked`}
          id={r.code}
          title={r === ratio ? `${r.title}, at ${money(data.facts.amount_paise)}` : r.title}
          source={`${r.anchor} · ${r.message}`}
          value={summary(r)}
          status={resultKind(r.status)}
        />
      ))}
      {ratio && offer ? (
        <>
          <LedgerRow id="E_max" title="Largest new EMI" source={String(ratio.values.formula)} value={String(ratio.values.e_max)} />
          <LedgerRow
            id="L_max"
            title="Largest loan for that EMI"
            source={`${data.facts.tenor_months} months at ${monthlyRate(data.facts.rate_bps_month)}. ${offer.rounding}`}
            value={String(ratio.values.l_max)}
          />
        </>
      ) : null}
      {ratioAtOffer && offer ? (
        <LedgerRow
          id={ratioAtOffer.code}
          title={`${ratioAtOffer.title}, at ${money(offer.amount_paise)}`}
          source={`${ratioAtOffer.anchor} · ${ratioAtOffer.message}`}
          value={summary(ratioAtOffer)}
          status={resultKind(ratioAtOffer.status)}
        />
      ) : null}
      {kfs ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-ink pt-4">
          <p className="type-title-m text-ink">Offer</p>
          <span className="hidden flex-1 sm:block" />
          <p className="type-mono-medium text-ink">
            {`${money(kfs.amount_paise)} · EMI ${money(kfs.emi_paise)} × ${kfs.instalments} · APR ${kfs.apr_percent}%`}
          </p>
          <Tag tone="stamp">{offer ? "Approve with modified amount" : "Approve"}</Tag>
        </div>
      ) : null}
    </>
  );
}
