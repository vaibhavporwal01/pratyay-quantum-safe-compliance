import type { Params, Template } from "@/lib/api/rules";

export type FieldKind = "text" | "rupees" | "percent" | "time" | "list" | "bool" | "fact";
export type FieldSpec = { key: string; label: string; kind: FieldKind; optional?: boolean; hint?: string };

/** The params form for each template (apps/api/app/rules/templates.py). Tiers have their own editor. */
export const FIELDS: Record<Template, FieldSpec[]> = {
  max_amount: [
    { key: "fact", label: "Fact checked", kind: "fact" },
    { key: "subject", label: "Subject", kind: "text", hint: "What is capped, e.g. annual household income." },
    { key: "max_paise", label: "Maximum (₹)", kind: "rupees" },
    { key: "must_be_false", label: "Must be no (optional)", kind: "fact", optional: true, hint: "A yes/no fact that fails the rule when yes, e.g. collateral." },
    { key: "decides_scope", label: "Decides whether the loan is in this rule's scope", kind: "bool" },
  ],
  max_ratio: [
    { key: "numerator_fact", label: "Numerator fact", kind: "fact" },
    { key: "denominator_fact", label: "Denominator fact", kind: "fact" },
    { key: "numerator", label: "Numerator", kind: "text" },
    { key: "denominator", label: "Denominator", kind: "text" },
    { key: "max_percent", label: "Maximum (%)", kind: "percent" },
    { key: "exclude", label: "Exclude", kind: "list", optional: true, hint: "Comma separated." },
    { key: "offer_on_fail", label: "On a fail, offer the largest amount that fits", kind: "bool" },
  ],
  min_days: [
    { key: "fact", label: "Fact checked", kind: "fact" },
    { key: "subject", label: "Subject", kind: "text" },
    { key: "working_days", label: "Counted in working days", kind: "bool" },
  ],
  time_window: [
    { key: "activity", label: "Activity", kind: "text" },
    { key: "start", label: "Not before", kind: "time" },
    { key: "end", label: "Not after", kind: "time" },
  ],
  prohibited_charge: [
    { key: "fact", label: "Fact checked", kind: "fact" },
    { key: "charge", label: "Charge", kind: "text" },
    { key: "unless", label: "Unless", kind: "text", optional: true },
  ],
  required_disclosure: [
    { key: "fact", label: "Fact checked", kind: "fact" },
    { key: "item", label: "Item", kind: "text" },
    { key: "includes", label: "Includes", kind: "list", optional: true, hint: "Comma separated." },
  ],
};

export type Tier = { min_days: number | null; tenor_days_min?: number | null; tenor_days_below?: number | null };

/** Params ready to send: optional blanks become null, lists drop empty items. */
export function cleanParams(template: Template, params: Params): Params {
  const out: Params = {};
  for (const f of FIELDS[template]) {
    const v = params[f.key];
    if (f.kind === "list") out[f.key] = Array.isArray(v) ? v.filter((x) => String(x).trim()) : [];
    else if (f.kind === "bool") out[f.key] = Boolean(v);
    else if (f.kind === "fact") out[f.key] = typeof v === "string" && v.trim() ? v.trim() : null;
    else if (v === "" || v === undefined) out[f.key] = f.optional ? null : f.kind === "text" ? "" : null;
    else out[f.key] = v;
  }
  if (template === "min_days") {
    const tiers = (params.tiers as Tier[] | undefined) ?? [{ min_days: null }];
    out.tiers = tiers.map((t) => {
      const tier: Tier = { min_days: t.min_days ?? null };
      if (t.tenor_days_min != null) tier.tenor_days_min = t.tenor_days_min;
      if (t.tenor_days_below != null) tier.tenor_days_below = t.tenor_days_below;
      return tier;
    });
  }
  const scope = typeof params.scope === "string" ? params.scope.trim() : "";
  out.scope = scope || null;
  return out;
}
