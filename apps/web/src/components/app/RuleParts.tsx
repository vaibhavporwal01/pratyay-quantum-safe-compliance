import type { ReactNode } from "react";
import { Status, Tag } from "@/components/ui";
import {
  STATUS_LABEL,
  STATUS_TONE,
  type BoundaryTest,
  type ExtractedValue,
  type Paragraph,
  type RuleStatus,
} from "@/lib/api/rules";

export function RuleStatusTag({ status }: { status: RuleStatus }) {
  return <Tag tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Tag>;
}

/** Classifier label and score, toned as in Dec v1 (below 0.80 goes to a person). */
export function LabelTag({ paragraph }: { paragraph: Paragraph }) {
  if (!paragraph.label) return <Tag tone="neutral">Not classified</Tag>;
  const score = paragraph.confidence ? Number(paragraph.confidence).toFixed(2) : "";
  const low = paragraph.confidence !== null && Number(paragraph.confidence) < 0.8;
  const tone = low ? "refer" : paragraph.label === "requirement" ? "pass" : paragraph.label === "definition" ? "ink" : "neutral";
  return <Tag tone={tone}>{`${paragraph.label}${score ? ` · ${score}` : ""}`}</Tag>;
}

/** The paragraph exactly as stored, with each extracted value marked. */
export function MarkedText({ text, values = [] }: { text: string; values?: ExtractedValue[] }) {
  const parts: ReactNode[] = [];
  let at = 0;
  for (const v of [...values].sort((a, b) => a.start - b.start)) {
    if (v.start < at) continue;
    parts.push(text.slice(at, v.start));
    parts.push(
      <mark key={`${v.start}-${v.kind}`} title={v.kind} className="rounded-[2px] bg-stamp-bg px-0.5 text-stamp">
        {text.slice(v.start, v.end)}
      </mark>,
    );
    at = v.end;
  }
  parts.push(text.slice(at));
  return <>{parts}</>;
}

/** Quoted source text in a paper block with a rule on the left. */
export function Quote({ children, note }: { children: ReactNode; note?: ReactNode }) {
  return (
    <figure className="flex flex-col gap-2">
      <blockquote className="border-l-2 border-ink bg-paper px-4 py-3 type-body break-words text-ink">{children}</blockquote>
      {note ? <figcaption className="type-caption text-muted">{note}</figcaption> : null}
    </figure>
  );
}

/** The machine rule as aligned mono lines. */
export function RulePreview({ lines }: { lines: [string, string][] }) {
  return (
    <dl className="grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-4 gap-y-1 overflow-x-auto bg-paper px-4 py-3 type-mono text-ink">
      {lines.map(([k, v], i) => (
        <div key={`${k}-${i}`} className="contents">
          <dt className="whitespace-nowrap text-ink-2">{k}</dt>
          <dd className="min-w-0 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Boundary tests: case, outcome, verdict. */
export function TestRows({ tests }: { tests: BoundaryTest[] }) {
  return (
    <ul className="flex flex-col">
      {tests.map((t) => (
        <li key={t.label} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rule-2 py-2.5">
          <span className="min-w-0 flex-1 type-mono break-words text-ink">{t.label}</span>
          <span className="type-small text-ink-2">
            {t.actual ? "passes" : "blocked"}
            {t.passed ? ", as expected" : `, expected ${t.expected ? "pass" : "block"}`}
          </span>
          <Status status={t.passed ? "pass" : "fail"} />
        </li>
      ))}
    </ul>
  );
}

/** A label and value on one line with a dotted leader, as in the Dec v1 detail panels. */
export function LeaderLine({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center gap-3 border-b border-rule-2 py-2.5">
      <span className="shrink-0 type-body text-ink-2">{label}</span>
      <span aria-hidden className="leader" />
      <span className="min-w-0 text-right type-mono break-words text-ink">{value}</span>
    </div>
  );
}
