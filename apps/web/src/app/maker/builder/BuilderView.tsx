"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ReactNode } from "react";
import { LabelTag, MarkedText, Quote, RulePreview, RuleStatusTag, TestRows } from "@/components/app/RuleParts";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Field, PageHead, Tag } from "@/components/ui";
import { api, ApiFailure, failureMessage } from "@/lib/api/client";
import {
  ruleLines,
  TEMPLATE_LABEL,
  TEMPLATES,
  type CheckResult,
  type Paragraph,
  type Params,
  type Rule,
  type Suggestion,
  type Template,
} from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";
import { cleanParams, FIELDS, type Tier } from "./fields";

const boxClass =
  "h-11 w-full rounded-[2px] border border-rule bg-white px-3 type-body text-ink outline-none focus:border-stamp";

function Labelled({ label, htmlFor, hint, children }: { label: string; htmlFor: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex w-full flex-col gap-1.5">
      <label htmlFor={htmlFor} className="type-label text-ink-2">
        {label}
      </label>
      {children}
      {hint ? <p className="type-caption text-muted">{hint}</p> : null}
    </div>
  );
}

function numOrNull(raw: string): number | null {
  if (raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** Loads the rule (edit) or the paragraph's suggestion (new), then shows the form. */
export function BuilderView() {
  const search = useSearchParams();
  const ruleId = search.get("rule");
  const paragraphId = search.get("paragraph");
  const rule = useApi<Rule>(ruleId ? `/rules/${ruleId}` : null);
  const docParas = useApi<Paragraph[]>(rule.data ? `/rules/sources/${rule.data.source_doc_id}/paragraphs` : null);
  const para = rule.data ? docParas.data?.find((p) => p.number === rule.data?.source_para) : undefined;
  const pid = paragraphId ?? para?.id ?? null;
  const suggestion = useApi<Suggestion>(pid ? `/rules/paragraphs/${pid}/suggestion` : null);

  if (!ruleId && !paragraphId) {
    return (
      <Empty title="Pick a paragraph first" action={<Button href="/maker/sources" variant="secondary">Open source documents</Button>}>
        Open a source document and choose a requirement paragraph to build a rule from.
      </Empty>
    );
  }
  const error = rule.error ?? docParas.error ?? suggestion.error;
  if (error) return <ErrorState message={error} />;
  if (ruleId && rule.data && docParas.data && !para) {
    return <ErrorState message={`Paragraph ${rule.data.source_para} is no longer in the stored document.`} />;
  }
  if (!suggestion.data || (ruleId && !rule.data)) return <Loading />;
  return <BuilderForm key={ruleId ?? paragraphId} suggestion={suggestion.data} rule={rule.data} />;
}

function BuilderForm({ suggestion, rule }: { suggestion: Suggestion; rule?: Rule }) {
  const router = useRouter();
  const paragraph = suggestion.paragraph;
  const editable = !rule || rule.status === "draft" || rule.status === "rejected";
  const [code, setCode] = useState(rule?.code ?? "");
  const [title, setTitle] = useState(rule?.title ?? "");
  const [template, setTemplate] = useState<Template>(rule?.template ?? suggestion.template);
  const [params, setParams] = useState<Params>(rule?.params ?? suggestion.params);
  const [appliesTo, setAppliesTo] = useState(rule?.applies_to ?? "all");
  const [effectiveFrom, setEffectiveFrom] = useState(rule?.effective_from ?? "");
  const [related, setRelated] = useState(rule?.related.map(({ para, note }) => ({ para, note })) ?? []);
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState<"check" | "send" | null>(null);
  const [failure, setFailure] = useState<{ message: string; problems: string[] } | null>(null);

  const cleaned = cleanParams(template, params);
  const relatedOut = related.filter((r) => r.para.trim());
  const set = (key: string, value: unknown) => {
    setParams((p) => ({ ...p, [key]: value }));
    setCheck(null);
  };

  async function runTests() {
    setBusy("check");
    setFailure(null);
    try {
      setCheck(
        await api.post<CheckResult>("/rules/check", {
          template,
          params: cleaned,
          paragraph_id: paragraph.id,
          related: relatedOut,
        }),
      );
    } catch (e) {
      setFailure({ message: failureMessage(e), problems: e instanceof ApiFailure ? e.problems : [] });
    } finally {
      setBusy(null);
    }
  }

  async function send() {
    setBusy("send");
    setFailure(null);
    const body = {
      code: code.trim(),
      title: title.trim(),
      template,
      params: cleaned,
      applies_to: appliesTo,
      effective_from: effectiveFrom || null,
      related: relatedOut,
    };
    try {
      if (rule) await api.patch<Rule>(`/rules/${rule.id}`, body);
      else
        await api.post<Rule>("/rules", {
          ...body,
          paragraph_id: paragraph.id,
          origin: template === suggestion.template ? "auto" : "manual",
        });
      router.push("/maker/drafts");
    } catch (e) {
      setFailure({ message: failureMessage(e), problems: e instanceof ApiFailure ? e.problems : [] });
      setBusy(null);
    }
  }

  const found = suggestion.values.filter((v) => v.kind !== "para_ref");
  const tiers = (params.tiers as Tier[] | undefined) ?? [{ min_days: null }];
  const setTier = (i: number, key: keyof Tier, raw: string) =>
    set("tiers", tiers.map((t, j) => (j === i ? { ...t, [key]: numOrNull(raw) } : t)));

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 02 · Rules · ${rule ? `${rule.code} · ${rule.status === "rejected" ? "sent back" : rule.status}` : "Write by hand"}`}
        title={rule ? `${rule.code}: edit the draft.` : `Para ${paragraph.number}: write the rule.`}
        subtitle="Build the check from the fields below. Every number must appear in the paragraph, and the rule still points to its paragraph and goes to a checker."
        actions={
          <>
            <Button href="/maker/drafts" variant="secondary">Cancel</Button>
            <Button onClick={send} disabled={!editable || busy !== null || !code.trim() || !title.trim()}>
              {busy === "send" ? "Sending" : "Send to checker"}
            </Button>
          </>
        }
      />
      {rule?.status === "rejected" && rule.review_note ? (
        <ErrorState title={`Sent back by ${rule.checked_by_name ?? "the checker"}`} message={rule.review_note} />
      ) : null}
      {!editable && rule ? (
        <ErrorState title="Read only" message={`${rule.code} is ${rule.status}. Only drafts and rules sent back can be edited.`} />
      ) : null}
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <Card
          className="min-w-0 lg:w-[480px] lg:shrink-0"
          eyebrow={`Para ${paragraph.number}`}
          title="Source paragraph"
          tag={<LabelTag paragraph={paragraph} />}
        >
          <div className="flex flex-col gap-3 pt-3">
            <Quote note="The original text. Marked words are the values the extractor found; only these can be used as numbers.">
              <MarkedText text={paragraph.text} values={suggestion.values} />
            </Quote>
            {rule?.related.length ? (
              <div className="flex flex-col gap-2">
                {rule.related.map((r) => (
                  <Quote key={r.para} note={r.note || undefined}>
                    <span className="type-label text-muted">Para {r.para} · </span>
                    {r.text}
                  </Quote>
                ))}
              </div>
            ) : null}
          </div>
        </Card>
        <Card
          className="min-w-0 flex-1"
          eyebrow={rule ? `Rule ${rule.code} · ${rule.status}` : "New rule · draft"}
          title={title || "Untitled rule"}
          tag={rule ? <RuleStatusTag status={rule.status} /> : <Tag tone="neutral">{template === suggestion.template ? "Suggested" : "Manual"}</Tag>}
        >
          <fieldset disabled={!editable} className="flex flex-col gap-4 pt-4">
            <div className="flex flex-col gap-4 sm:flex-row">
              <Field className="sm:w-48" label="Rule ID" value={code} onChange={(e) => setCode(e.target.value)} placeholder="MF-02" />
              <Field label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Repayments within 50% of household income" />
            </div>
            <div className="flex flex-col gap-4 sm:flex-row">
              <Labelled label="Template" htmlFor="template">
                <select
                  id="template"
                  className={boxClass}
                  value={template}
                  onChange={(e) => {
                    setTemplate(e.target.value as Template);
                    setParams({ scope: params.scope });
                    setCheck(null);
                  }}
                >
                  {TEMPLATES.map((t) => (
                    <option key={t} value={t}>
                      {TEMPLATE_LABEL[t]}
                    </option>
                  ))}
                </select>
              </Labelled>
              <Labelled label="Applies to" htmlFor="applies">
                <select id="applies" className={boxClass} value={appliesTo} onChange={(e) => setAppliesTo(e.target.value as "all" | "microfinance")}>
                  <option value="microfinance">Microfinance loans</option>
                  <option value="all">All loans</option>
                </select>
              </Labelled>
              <Field label="Effective from" type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
            </div>
            {found.length ? (
              <p className="type-small text-ink-2">
                Values in the paragraph: {found.map((v) => `“${v.text}”`).join(", ")}
              </p>
            ) : (
              <p className="type-small text-ink-2">This paragraph has no numbers, so this rule cannot carry one.</p>
            )}
            {FIELDS[template].map((f) => {
              const id = `param-${f.key}`;
              const v = params[f.key];
              if (f.kind === "bool")
                return (
                  <label key={f.key} className="flex items-center gap-2 type-body text-ink">
                    <input type="checkbox" checked={Boolean(v)} onChange={(e) => set(f.key, e.target.checked)} className="size-4 accent-stamp" />
                    {f.label}
                  </label>
                );
              if (f.kind === "rupees")
                return (
                  <Field
                    key={f.key}
                    id={id}
                    label={f.label}
                    inputMode="numeric"
                    value={typeof v === "number" ? String(v / 100) : ""}
                    onChange={(e) => {
                      const n = numOrNull(e.target.value.replace(/,/g, ""));
                      set(f.key, n === null ? null : Math.round(n * 100));
                    }}
                    hint="Stored in paise."
                  />
                );
              if (f.kind === "list")
                return (
                  <Field
                    key={f.key}
                    id={id}
                    label={f.label}
                    hint={f.hint}
                    value={Array.isArray(v) ? v.join(", ") : ""}
                    onChange={(e) => set(f.key, e.target.value.split(",").map((s) => s.trim()))}
                  />
                );
              return (
                <Field
                  key={f.key}
                  id={id}
                  label={f.label}
                  hint={f.hint}
                  type={f.kind === "time" ? "time" : "text"}
                  inputMode={f.kind === "percent" ? "decimal" : undefined}
                  value={v === null || v === undefined ? "" : String(v)}
                  onChange={(e) => set(f.key, e.target.value)}
                />
              );
            })}
            {template === "min_days" ? (
              <div className="flex flex-col gap-2">
                <p className="type-label text-ink-2">Tiers</p>
                {tiers.map((t, i) => (
                  <div key={i} className="flex flex-col gap-3 border-b border-rule-2 pb-3 sm:flex-row sm:items-end">
                    <Field label="At least (days)" inputMode="numeric" value={t.min_days ?? ""} onChange={(e) => setTier(i, "min_days", e.target.value)} />
                    <Field label="If tenor at least" inputMode="numeric" value={t.tenor_days_min ?? ""} onChange={(e) => setTier(i, "tenor_days_min", e.target.value)} />
                    <Field label="If tenor below" inputMode="numeric" value={t.tenor_days_below ?? ""} onChange={(e) => setTier(i, "tenor_days_below", e.target.value)} />
                    {tiers.length > 1 ? (
                      <Button variant="quiet" onClick={() => set("tiers", tiers.filter((_, j) => j !== i))}>Remove</Button>
                    ) : null}
                  </div>
                ))}
                <div>
                  <Button variant="quiet" onClick={() => set("tiers", [...tiers, { min_days: null }])}>Add a tier</Button>
                </div>
              </div>
            ) : null}
            <Field
              label="Scope, copied from the text"
              value={typeof params.scope === "string" ? params.scope : ""}
              onChange={(e) => set("scope", e.target.value)}
              placeholder="microfinance loans"
              hint="Optional. Words that limit which loans the rule covers, exactly as in this paragraph or a related one."
            />
            <div className="flex flex-col gap-2">
              <p className="type-label text-ink-2">Related paragraphs</p>
              {related.map((r, i) => (
                <div key={i} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <Field
                    className="sm:w-32"
                    label="Para"
                    value={r.para}
                    onChange={(e) => setRelated(related.map((x, j) => (j === i ? { ...x, para: e.target.value } : x)))}
                  />
                  <Field
                    label="What it adds"
                    value={r.note}
                    onChange={(e) => setRelated(related.map((x, j) => (j === i ? { ...x, note: e.target.value } : x)))}
                  />
                  <Button variant="quiet" onClick={() => setRelated(related.filter((_, j) => j !== i))}>Remove</Button>
                </div>
              ))}
              <div>
                <Button variant="quiet" onClick={() => setRelated([...related, { para: "", note: "" }])}>Add a related paragraph</Button>
              </div>
            </div>
          </fieldset>
          <div className="flex flex-col gap-4 pt-5">
            <div className="flex flex-col gap-2">
              <p className="type-label text-muted">Preview</p>
              <RulePreview
                lines={ruleLines({
                  code: code || undefined,
                  template,
                  params: cleaned,
                  applies_to: appliesTo,
                  source_doc_title: rule?.source_doc_title,
                  source_para: paragraph.number ?? undefined,
                  effective_from: effectiveFrom || null,
                })}
              />
            </div>
            {check ? (
              check.problems.length ? (
                <ErrorState title="Does not match the paragraph" message="Fix these before sending." problems={check.problems} />
              ) : (
                <div className="flex flex-col gap-2">
                  <p className="type-label text-muted">Boundary tests, generated</p>
                  {check.missing.length ? (
                    <Empty title="Values missing">{`Fill ${check.missing.join(", ")} to generate the tests. A checker cannot approve a rule with a missing value.`}</Empty>
                  ) : (
                    <TestRows tests={check.tests} />
                  )}
                </div>
              )
            ) : null}
            {failure ? <ErrorState title="Not sent" message={failure.message} problems={failure.problems} /> : null}
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={runTests} disabled={busy !== null}>
                {busy === "check" ? "Running" : "Run tests"}
              </Button>
              <Button onClick={send} disabled={!editable || busy !== null || !code.trim() || !title.trim()}>
                {busy === "send" ? "Sending" : "Send to checker"}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
