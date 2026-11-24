"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { LabelTag, MarkedText, Quote, RulePreview, RuleStatusTag } from "@/components/app/RuleParts";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Figure, Figures, PageHead, Tag } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  rupees,
  ruleLines,
  shortDocName,
  shortHash,
  TEMPLATE_LABEL,
  type ExtractedValue,
  type Paragraph,
  type Rule,
  type SourceDoc,
  type Suggestion,
} from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

function shown(v: ExtractedValue): string {
  if (v.kind === "amount" && typeof v.value === "number") return `${v.value} paise (${rupees(v.value)})`;
  if (v.kind === "percent") return `${v.value}%`;
  if (v.kind === "days") return `${v.value} ${v.unit === "working_day" ? "working days" : "days"}`;
  if (v.kind === "para_ref") return `para ${v.value}`;
  return String(v.value);
}

function firstLine(text: string): string {
  return text.length > 90 ? `${text.slice(0, 88).trimEnd()}…` : text;
}

export function DraftView() {
  const { docId } = useParams<{ docId: string }>();
  const doc = useApi<SourceDoc>(`/rules/sources/${docId}`);
  const paras = useApi<Paragraph[]>(`/rules/sources/${docId}/paragraphs`);
  const rules = useApi<Rule[]>("/rules");
  const [onlyRequirements, setOnlyRequirements] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);

  const labelled = paras.data?.some((p) => p.label) ?? false;
  const list = (paras.data ?? []).filter((p) => !onlyRequirements || !labelled || p.label === "requirement");
  const selected = picked ?? list[0]?.id ?? null;
  const suggestion = useApi<Suggestion>(selected ? `/rules/paragraphs/${selected}/suggestion` : null);
  const docRules = (rules.data ?? []).filter((r) => r.source_doc_id === docId);
  const paraRules = docRules.filter((r) => r.source_para === suggestion.data?.paragraph.number);

  if (doc.error) return <ErrorState message={doc.error} onRetry={doc.reload} />;
  if (!doc.data) return <Loading />;
  const d = doc.data;
  const waiting = d.rules.draft ?? 0;

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 01 · Rules · Draft from a circular"
        title="Read a circular. Draft the rules. A person signs off."
        subtitle="Pratyay splits the PDF into numbered paragraphs, finds the requirements, and drafts each one as a rule that points back to its paragraph. Nothing goes live until a checker approves it."
        actions={
          <>
            <Button href="/maker/sources/upload" variant="secondary">Upload another PDF</Button>
            <Button href="/maker/drafts">{waiting ? `${waiting} draft${waiting === 1 ? "" : "s"} with the checker` : "My drafts"}</Button>
          </>
        }
      />
      <div className="flex flex-col gap-3">
        <Figures>
          <Figure label="1 · Uploaded" value={<span title={d.title} className="line-clamp-2 block whitespace-normal break-words">{shortDocName(d.title)}</span>} note={`SHA3-256 ${shortHash(d.sha3_256)}${d.pages ? ` · ${d.pages} pages` : ""}`} />
          <Figure label="2 · Paragraphs" value={d.paragraphs} note={d.ref_no ?? "Reference not recorded"} />
          <Figure
            label="3 · Requirements"
            value={labelled ? (d.labels.requirement ?? 0) : "Not classified"}
            note={labelled ? `${d.needs_review} below 0.80 need a person` : "Run the classifier to label paragraphs"}
          />
          <Figure label="4 · Rules drafted" value={(d.rules.draft ?? 0) + (d.rules.approved ?? 0)} note={`${d.rules.approved ?? 0} approved · ${d.rules.rejected ?? 0} sent back`} />
          <Figure label="5 · Checker" value={waiting ? "Waiting" : "Clear"} note={waiting ? `${waiting} in review` : "Nothing waiting"} />
        </Figures>
        <p className="type-caption text-muted">Counts come from the parser run and the rule register.</p>
      </div>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <DataCard
          className="min-w-0 lg:w-[480px] lg:shrink-0"
          eyebrow="Step 3 · Classifier output"
          title="Paragraphs"
          tag={
            labelled ? (
              <button
                type="button"
                onClick={() => setOnlyRequirements((v) => !v)}
                className="type-label text-stamp underline-offset-2 hover:underline"
              >
                {onlyRequirements ? "Show all" : "Requirements only"}
              </button>
            ) : undefined
          }
          state={paras}
          isEmpty={(p) => p.length === 0}
          empty={<Empty title="No paragraphs were found in this document." />}
        >
          {() => (
            <>
              <ul className="flex max-h-[720px] flex-col overflow-y-auto">
                {list.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => setPicked(p.id)}
                      aria-current={p.id === selected ? "true" : undefined}
                      className={cn(
                        "flex w-full flex-wrap items-center gap-x-4 gap-y-1 border-b border-rule-2 px-2 py-3 text-left",
                        p.id === selected ? "bg-stamp-bg" : "hover:bg-paper",
                      )}
                    >
                      <span className="w-16 shrink-0 type-mono text-ink-2">para {p.number}</span>
                      <span className="min-w-0 flex-1 type-body text-ink">{firstLine(p.text)}</span>
                      <LabelTag paragraph={p} />
                    </button>
                  </li>
                ))}
              </ul>
              <p className="pt-3 type-caption text-muted">Score = classifier confidence. Below 0.80 goes to a person to write the rule by hand.</p>
            </>
          )}
        </DataCard>
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          <DataCard
            eyebrow={suggestion.data ? `${shortDocName(d.title)} · Para ${suggestion.data.paragraph.number}` : "Selected paragraph"}
            title="What the parser found"
            tag={suggestion.data ? <Tag tone="ink">{`Template: ${TEMPLATE_LABEL[suggestion.data.template]}`}</Tag> : undefined}
            state={suggestion}
          >
            {(s) => (
              <div className="flex flex-col gap-4 pt-3">
                <Quote note="The original paragraph as stored. Marked words are the values the extractor found.">
                  <MarkedText text={s.paragraph.text} values={s.values} />
                </Quote>
                {s.values.length ? (
                  <dl className="flex flex-col">
                    {s.values.map((v) => (
                      <div key={`${v.start}-${v.kind}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rule-2 py-2.5">
                        <dt className="w-24 shrink-0 type-label text-ink-2">{v.kind.replace("_", " ")}</dt>
                        <dd className="min-w-0 flex-1 type-body text-ink">“{v.text}”</dd>
                        <dd className="type-mono text-stamp">→ {shown(v)}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <Empty title="No numbers in this paragraph">
                    It can still be a prohibited charge or a required disclosure. Numbers are never added by hand unless they are in the text.
                  </Empty>
                )}
              </div>
            )}
          </DataCard>
          {suggestion.data ? (
            <Card eyebrow="Suggested rule" title={`${TEMPLATE_LABEL[suggestion.data.template]} from para ${suggestion.data.paragraph.number}`}>
              <div className="flex flex-col gap-4 pt-3">
                <RulePreview lines={ruleLines({ template: suggestion.data.template, params: suggestion.data.params, applies_to: "to be chosen" })} />
                <p className="type-small text-ink-2">
                  {suggestion.data.missing.length
                    ? `Not found in the text, left empty: ${suggestion.data.missing.join(", ")}.`
                    : "Every number above was found in the paragraph. Name the subject and scope in the builder."}
                </p>
                {paraRules.length ? (
                  <div className="flex flex-col">
                    <p className="type-label text-muted">Rules already drawn from this paragraph</p>
                    {paraRules.map((r) => (
                      <Link
                        key={r.id}
                        href={r.status === "draft" || r.status === "rejected" ? `/maker/builder?rule=${r.id}` : `/rules/library?rule=${r.id}`}
                        className="flex flex-wrap items-center gap-3 border-b border-rule-2 py-2.5 hover:bg-paper"
                      >
                        <span className="w-16 type-mono-medium text-ink">{r.code}</span>
                        <span className="min-w-0 flex-1 type-body text-ink">{r.title}</span>
                        <RuleStatusTag status={r.status} />
                      </Link>
                    ))}
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-3">
                  <Button href={`/maker/builder?paragraph=${suggestion.data.paragraph.id}`}>Build this rule</Button>
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
