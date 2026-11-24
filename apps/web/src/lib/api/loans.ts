/** Loans API types (apps/api/app/loans) and display helpers. Money is integer paise. */

import type { StatusKind } from "@/components/ui";
import { rupees } from "./rules";

export type AppStatus = "evaluated" | "recommended" | "approved" | "approved_modified" | "rejected";
export type Outcome = "pass" | "fail" | "refer";
export type ResultStatus = Outcome | "not_checked" | "not_applicable";

export type Fee = { name: string; paise: number; payable_to: string; assumed: boolean; basis: string };

export type Kfs = {
  amount_paise: number;
  tenor_months: number;
  rate_bps_month: number;
  rate_month_percent: string;
  rate_year_percent: string;
  emi_paise: number;
  emi_exact: string;
  instalments: number;
  first_due_on: string;
  fees: Fee[];
  fees_total_paise: number;
  net_disbursal_paise: number;
  total_interest_paise: number;
  total_payable_paise: number;
  monthly_irr_percent: string;
  apr_percent: string;
  apr_method: string;
  rounding: string;
  issued_on: string;
  valid_until: string | null;
  validity_working_days: number | null;
  validity_anchor: string | null;
  notes: string[];
};

export type RuleResult = {
  rule_id: string;
  code: string;
  version: number;
  title: string;
  stage: "origination" | "servicing" | "recovery";
  applies_to: string;
  status: ResultStatus;
  message: string;
  anchor: string;
  para_text: string;
  values: Record<string, string | number | boolean>;
  missing: string[];
};

export type Offer = {
  amount_paise: number;
  emi_paise: number;
  e_max_paise: number;
  l_max_exact: string;
  ratio_percent: string;
  step_paise: number;
  rounding: string;
  outcome?: Outcome;
  kfs?: Kfs | null;
};

export type Evaluation = {
  id: string;
  on_date: string;
  amount_paise: number;
  outcome: Outcome;
  microfinance: boolean | null;
  results: RuleResult[];
  rules_used: { rule_id: string; code: string; version: number }[];
  offer: Offer | null;
  kfs: Kfs | null;
  created_at: string;
};

/** POST /loans/preview: an engine run that is not saved. */
export type Preview = Omit<Evaluation, "id" | "amount_paise" | "created_at"> & { notes: string[] };

export type Application = {
  id: string;
  ref: string;
  borrower_id: string | null;
  borrower_name: string;
  purpose: string | null;
  product: string;
  product_name: string;
  amount_paise: number;
  tenor_months: number;
  rate_bps_month: number;
  household_income_annual_paise: number | null;
  existing_monthly_repayments_paise: number | null;
  collateral: boolean | null;
  status: AppStatus;
  created_at: string;
  updated_at: string;
};

export type AppSummary = Application & {
  outcome: Outcome | null;
  first_problem: string | null;
  offer_paise: number | null;
  approved_paise: number | null;
  recommendation: Recommendation | null;
  signed: boolean;
};

export type Recommendation = "approve" | "approve_modified" | "reject";

export type Decision = {
  id: string;
  recommendation: Recommendation;
  recommended_paise: number | null;
  officer_id: string;
  officer_name: string | null;
  officer_note: string | null;
  recommended_at: string;
  outcome: "approved" | "approved_modified" | "rejected" | null;
  approved_paise: number | null;
  checker_id: string | null;
  checker_name: string | null;
  checker_note: string | null;
  decided_at: string | null;
  ledger_seq: number | null;
  /** HOOK(Pulkit): "signed" once ledger.append signs the decision. */
  signature: "signed" | "pending";
};

export type LoanEvent = {
  id: string;
  action: string;
  actor_name: string | null;
  meta: Record<string, unknown>;
  created_at: string;
  ref?: string;
};

export type Detail = {
  application: Application & { submitted_by_name: string | null };
  evaluation: Evaluation | null;
  final_evaluation: Evaluation | null;
  recommended_evaluation: Evaluation | null;
  decision: Decision | null;
  events: LoanEvent[];
};

export type Product = {
  code: string;
  name: string;
  category: string;
  rate_bps_month: number;
  tenors: number[];
  fees: { name: string; bps?: number; paise?: number; assumed?: boolean }[];
};

/** GET /loans/decisions: decided applications only. */
export type DecisionRow = {
  application: Application;
  decision: Decision;
  final_evaluation: Evaluation | null;
  rules: {
    /** Rules in force on the day, every stage. */
    in_force: number;
    /** Of those, checked at origination (pass, fail or refer). */
    checked: number;
    /** "MF-02 v1", every rule in force with its version. */
    versions: string[];
    /** Rules that failed or referred at the amount asked for: what decided the outcome. */
    deciding: string[];
  };
};

/** "8 rules · MF-02 v1 decided", or "8 rules · all pass". */
export function rulesUsed(r: DecisionRow["rules"]): string {
  const n = `${r.in_force} rule${r.in_force === 1 ? "" : "s"}`;
  return r.deciding.length ? `${n} · ${r.deciding.join(", ")} decided` : `${n} · all pass`;
}

export type Replay = {
  application: Application;
  evaluation_id: string;
  on_date: string;
  amount_paise: number;
  stored_outcome: Outcome;
  replayed_outcome: Outcome;
  same_outcome: boolean;
  same_results: boolean;
  different_results: string[];
  same_rules: boolean;
  rules_used: string[];
  rules_now: string[];
  signature: "signed" | "pending";
  decision: Decision | null;
};

export type Counts = { applications: number; evaluations: number; decisions: number; events: number; signed: number };

export const STATUS_LABEL: Record<AppStatus, string> = {
  evaluated: "With officer",
  recommended: "With checker",
  approved: "Approved",
  approved_modified: "Approved, modified",
  rejected: "Declined",
};

export const OUTCOME_LABEL: Record<Recommendation, string> = {
  approve: "Approve",
  approve_modified: "Approve with modified amount",
  reject: "Decline",
};

export function finalLabel(status: AppStatus): string {
  if (status === "approved_modified") return "Approve with modified amount";
  if (status === "approved") return "Approve as asked";
  if (status === "rejected") return "Decline";
  return STATUS_LABEL[status];
}

/** Status mark for an engine result. Not checked and not applicable read as pending. */
export function resultKind(status: ResultStatus | Outcome | null | undefined): StatusKind {
  switch (status) {
    case "pass":
      return "pass";
    case "fail":
      return "fail";
    case "refer":
      return "referred";
    default:
      return "pending";
  }
}

export function resultLabel(status: ResultStatus): string {
  return {
    pass: "Pass",
    fail: "Fail",
    refer: "Refer",
    not_checked: "Later stage",
    not_applicable: "Not applicable",
  }[status];
}

/** The status mark for an application row: its decision if decided, else the engine outcome. */
export function appKind(a: Pick<AppSummary, "status" | "outcome">): StatusKind {
  if (a.status === "approved" || a.status === "approved_modified") return "pass";
  if (a.status === "rejected") return "fail";
  if (a.status === "recommended") return "referred";
  return resultKind(a.outcome);
}

export function appKindLabel(a: Pick<AppSummary, "status" | "outcome">): string {
  if (a.status === "approved" || a.status === "approved_modified") return "Approved";
  if (a.status === "rejected") return "Declined";
  if (a.status === "recommended") return "With checker";
  return a.outcome ? { pass: "Pass", fail: "Fail", refer: "Refer" }[a.outcome] : "Pending";
}

/** "2% a month" from basis points. */
export function monthlyRate(bps: number): string {
  return `${trimZeros((bps / 100).toFixed(2))}% a month`;
}

function trimZeros(s: string): string {
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

/** "₹80,000" from paise, or a dash. */
export function money(paise: number | null | undefined): string {
  return paise === null || paise === undefined ? "Not given" : rupees(paise);
}

/** Rupees typed by a person ("80,000", "₹80000") to paise; null if not a whole positive amount. */
export function toPaise(text: string): number | null {
  const clean = text.replace(/[₹,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const paise = Math.round(Number(clean) * 100);
  return paise > 0 ? paise : null;
}

/** "12 Oct 2026, 11:42" in IST. */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "Not yet";
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });
}

export function shortDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });
}

/** Counts of results by status, e.g. "5 pass · 3 later stage". */
export function resultSummary(results: RuleResult[]): string {
  const n = (s: ResultStatus) => results.filter((r) => r.status === s).length;
  const parts = [
    [n("pass"), "pass"],
    [n("fail"), "fail"],
    [n("refer"), "refer"],
    [n("not_checked"), "later stage"],
    [n("not_applicable"), "not applicable"],
  ] as const;
  return parts.filter(([c]) => c > 0).map(([c, l]) => `${c} ${l}`).join(" · ") || "No rules in force";
}

/** The one figure a rule result is about, for the value column. */
export function resultValue(r: RuleResult): string {
  const v = r.values;
  switch (r.code) {
    case "MF-01":
      return v.household_income_annual ? `${v.household_income_annual} ≤ ${v.limit}` : r.missing.length ? "fact missing" : "";
    case "MF-02":
      return v.ratio_percent ? `${v.ratio_percent}% ${r.status === "pass" ? "≤" : ">"} ${v.limit_percent}%` : "fact missing";
    case "KF-01":
      return v.valid_until ? `valid until ${v.valid_until}` : "";
    case "KF-03":
      return v.apr_percent ? `APR ${v.apr_percent}%` : "";
    case "MF-04":
      return v.prepayment_charge !== undefined ? `pre-payment ${v.prepayment_charge}` : "";
    default:
      return r.status === "not_checked" ? `at ${r.stage}` : "";
  }
}

/** The KFS that applies: the decided amount's, else the offer's, else the amount asked for. */
export function currentKfs(d: Detail): Kfs | null {
  return d.final_evaluation?.kfs ?? d.recommended_evaluation?.kfs ?? d.evaluation?.kfs ?? null;
}

export function ratioAt(ev: Evaluation | null): string | null {
  const mf02 = ev?.results.find((r) => r.code === "MF-02");
  return mf02?.values.ratio_percent ? String(mf02.values.ratio_percent) : null;
}

/** "₹10,989 of ₹22,000" from the MF-02 values. */
export function repaymentsOf(ev: Evaluation | null): string | null {
  const v = ev?.results.find((r) => r.code === "MF-02")?.values;
  return v?.repayments ? `${v.repayments} of ${v.monthly_income}` : null;
}

export const EVENT_LABEL: Record<string, string> = {
  submitted: "Submitted",
  evaluated: "Rules checked",
  facts_updated: "Facts updated",
  recommended: "Recommended by the officer",
  decided: "Decided by a second person",
};
