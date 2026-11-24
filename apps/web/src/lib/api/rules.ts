/** Rules API types (apps/api/app/rules/schemas.py) and small display helpers. */

import type { Role } from "./auth";

export type Me = { id: string; org_id: string; role: Role; name: string; dev_stand_in: boolean };

export type SourceDoc = {
  id: string;
  title: string;
  /** Citation code stored on the source, e.g. "CF". Null for an upload that gave none. */
  short_code: string | null;
  ref_no: string | null;
  issued_on: string | null;
  url: string | null;
  sha3_256: string | null;
  pages: number | null;
  uploaded_at: string;
  paragraphs: number;
  labels: Record<string, number>;
  needs_review: number;
  rules: Record<string, number>;
};

export type Paragraph = {
  id: string;
  number: string | null;
  page: number | null;
  text: string;
  label: "requirement" | "definition" | "information" | null;
  confidence: string | null;
};

export type ExtractedValue = {
  kind: "amount" | "percent" | "days" | "time" | "para_ref";
  value: number | string;
  text: string;
  start: number;
  end: number;
  unit: string | null;
};

export type Params = Record<string, unknown>;

export type Suggestion = {
  paragraph: Paragraph;
  doc_id: string;
  template: Template;
  params: Params;
  missing: string[];
  values: ExtractedValue[];
};

export type BoundaryTest = {
  label: string;
  facts: Record<string, unknown>;
  expected: boolean;
  actual: boolean;
  passed: boolean;
};

export type CheckResult = { problems: string[]; missing: string[]; tests: BoundaryTest[] };

export type RuleStatus = "draft" | "approved" | "rejected" | "retired";

export type Rule = {
  id: string;
  code: string;
  title: string;
  template: Template;
  params: Params;
  applies_to: "microfinance" | "all";
  effective_from: string | null;
  effective_to: string | null;
  status: RuleStatus;
  source_doc_id: string;
  source_doc_title: string;
  source_doc_code: string | null;
  source_doc_ref: string | null;
  source_para: string;
  para_text: string;
  /** The heading the paragraph sits under; context, not a quote. */
  section: string | null;
  related: { para: string; text: string; note: string }[];
  origin: "auto" | "manual";
  made_by: string;
  made_by_name: string | null;
  checked_by: string | null;
  checked_by_name: string | null;
  review_note: string | null;
  created_at: string;
  updated_at: string;
  checked_at: string | null;
  missing: string[];
  problems: string[];
  tests: BoundaryTest[];
};

export type Overview = {
  counts: Record<RuleStatus, number>;
  sources: number;
  waiting_for_you: Rule[];
  recently_checked: Rule[];
};

export type IngestResult = {
  doc_id: string;
  sha3_256: string;
  duplicate: boolean;
  classified: boolean;
  report: { pages: number; paragraphs: number; unmatched: unknown[]; removed: unknown[] };
};

export const TEMPLATES = [
  "max_amount",
  "max_ratio",
  "min_days",
  "time_window",
  "prohibited_charge",
  "required_disclosure",
] as const;
export type Template = (typeof TEMPLATES)[number];

export const TEMPLATE_LABEL: Record<Template, string> = {
  max_amount: "Amount cap",
  max_ratio: "Ratio cap",
  min_days: "Minimum days",
  time_window: "Time window",
  prohibited_charge: "Prohibited charge",
  required_disclosure: "Required disclosure",
};

export const STATUS_TONE = {
  draft: "stamp",
  approved: "pass",
  rejected: "fail",
  retired: "neutral",
} as const;

export const STATUS_LABEL: Record<RuleStatus, string> = {
  draft: "In review",
  approved: "Approved",
  rejected: "Sent back",
  retired: "Retired",
};

/** "Reserve Bank of India (NBFCs – Credit Facilities) Directions, 2025" -> "Credit Facilities Directions". */
export function shortDocName(title: string): string {
  const m = title.match(/\s[–-]\s+([^)]+)\)\s*Directions/);
  return m ? `${m[1].trim()} Directions` : title;
}

/** The source's stored short code ("CF"), or its short name when the upload gave no code. */
export function docCode(code: string | null | undefined, title: string): string {
  return code || shortDocName(title);
}

/** "CF para 51": the anchor every rule cites. */
export function citation(r: { source_doc_code: string | null; source_doc_title: string; source_para: string }): string {
  return `${docCode(r.source_doc_code, r.source_doc_title)} para ${r.source_para}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Not set";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function shortHash(hex: string | null): string {
  return hex ? `${hex.slice(0, 8)}…${hex.slice(-4)}` : "Not recorded";
}

/** 30000000 paise -> "₹3,00,000". */
export function rupees(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function show(value: unknown): string {
  if (value === null || value === undefined || value === "") return "missing";
  if (Array.isArray(value)) return value.length ? value.map(show).join(", ") : "none";
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => `${k} ${show(v)}`)
      .join(", ");
  }
  return String(value);
}

/** The machine rule as aligned key and value lines, for the mono preview blocks. */
export function ruleLines(r: {
  code?: string;
  template: Template;
  params: Params;
  applies_to: string;
  source_doc_title?: string;
  source_doc_code?: string | null;
  source_para?: string;
  effective_from?: string | null;
}): [string, string][] {
  const lines: [string, string][] = [];
  if (r.code) lines.push(["rule_id", r.code]);
  lines.push(["template", r.template]);
  lines.push(["applies_to", r.applies_to]);
  for (const [k, v] of Object.entries(r.params)) {
    if (k === "max_paise" && typeof v === "number") lines.push([k, `${v} (${rupees(v)})`]);
    else if (k === "tiers" && Array.isArray(v)) {
      v.forEach((t, i) => lines.push([`tier ${i + 1}`, show(t)]));
    } else if (v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0)) {
      lines.push([k, show(v)]);
    }
  }
  if (r.source_doc_title && r.source_para) {
    lines.push(["anchor", `${docCode(r.source_doc_code, r.source_doc_title)} para ${r.source_para}`]);
  }
  if (r.effective_from !== undefined) lines.push(["valid_from", r.effective_from ?? "not set"]);
  return lines;
}
