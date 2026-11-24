"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useMe } from "@/components/app/RoleShell";
import { LeaderLine, Quote, RulePreview, RuleStatusTag, TestRows } from "@/components/app/RuleParts";
import { DataCard, Empty, ErrorState } from "@/components/app/States";
import { Button, Card, Field, PageHead, Tag } from "@/components/ui";
import { api, failureMessage } from "@/lib/api/client";
import { citation, formatDate, ruleLines, TEMPLATE_LABEL, type Rule } from "@/lib/api/rules";
import { cn } from "@/lib/cn";
import { useApi } from "@/lib/useApi";

export function LibraryView() {
  const me = useMe();
  const router = useRouter();
  const search = useSearchParams();
  const asOf = search.get("as_of") ?? "";
  const lib = useApi<Rule[]>(`/rules/library${asOf ? `?as_of=${asOf}` : ""}`);
  const rules = lib.data ?? [];
  const selectedId = search.get("rule") ?? rules[0]?.id;
  const selected = rules.find((r) => r.id === selectedId) ?? rules[0];
  const sources = new Set(rules.map((r) => r.source_doc_id)).size;

  const go = (next: Record<string, string | undefined>) => {
    const q = new URLSearchParams(search.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) q.set(k, v);
      else q.delete(k);
    }
    router.replace(`/rules/library${q.size ? `?${q}` : ""}`, { scroll: false });
  };

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 03 · Rules · Registry"
        title="The rulebook, with dates."
        subtitle={
          lib.data
            ? `${rules.length} approved rule${rules.length === 1 ? "" : "s"} from ${sources} source document${sources === 1 ? "" : "s"}${asOf ? `, in force on ${formatDate(asOf)}` : ""}. Only rules a checker approved appear here.`
            : "Only rules a checker approved appear here."
        }
        actions={
          <>
            <form
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                const v = new FormData(e.currentTarget).get("as_of");
                go({ as_of: typeof v === "string" && v ? v : undefined, rule: undefined });
              }}
            >
              <Field className="w-44" label="In force on" name="as_of" type="date" defaultValue={asOf} key={asOf} />
              <Button type="submit" variant="secondary">Show</Button>
            </form>
            {me.role === "maker" ? <Button href="/maker/sources">Draft from a circular</Button> : null}
          </>
        }
      />
      <div className="flex flex-col gap-7 xl:flex-row xl:items-start">
        <DataCard
          className="min-w-0 flex-1"
          eyebrow={`${rules.length} entries`}
          title="Registry"
          state={lib}
          isEmpty={(d) => d.length === 0}
          empty={
            <Empty title={asOf ? "No approved rules in force on that date" : "No approved rules yet"}>
              {asOf ? "Clear the date to see every approved rule." : "Rules appear here once a checker approves a draft."}
            </Empty>
          }
        >
          {(data) => (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] table-fixed border-collapse text-left">
                <caption className="sr-only">Approved rules</caption>
                <colgroup>
                  <col style={{ width: 80 }} />
                  <col />
                  <col style={{ width: 130 }} />
                  <col style={{ width: 120 }} />
                  <col style={{ width: 110 }} />
                  <col style={{ width: 110 }} />
                </colgroup>
                <thead>
                  <tr className="border-b border-rule">
                    {["ID", "Rule", "Source", "From", "To", "Status"].map((h) => (
                      <th key={h} scope="col" className="py-3 pr-4 type-label font-medium text-muted">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => go({ rule: r.id })}
                      className={cn(
                        "cursor-pointer border-b border-rule-2",
                        r.id === selected?.id ? "bg-stamp-bg shadow-[inset_2px_0_0_var(--stamp)]" : "hover:bg-paper",
                      )}
                    >
                      <td className="py-3 pr-4 pl-2 type-mono-medium text-ink">{r.code}</td>
                      <td className="py-3 pr-4">
                        <button type="button" onClick={() => go({ rule: r.id })} className="flex flex-col text-left">
                          <span className="type-body-medium text-ink">{r.title}</span>
                          <span className="type-caption text-muted">
                            {TEMPLATE_LABEL[r.template]} · {r.applies_to === "microfinance" ? "Microfinance loans" : "All loans"}
                          </span>
                        </button>
                      </td>
                      <td className="py-3 pr-4 type-body text-ink-2">{`${citation(r)}`}</td>
                      <td className="py-3 pr-4 type-mono text-ink-2">{formatDate(r.effective_from)}</td>
                      <td className={cn("py-3 pr-4 type-mono", r.effective_to ? "text-refer" : "text-ink-2")}>
                        {r.effective_to ? formatDate(r.effective_to) : "Open"}
                      </td>
                      <td className="py-3 pr-4"><RuleStatusTag status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataCard>
        {selected ? <RuleDetail key={selected.id} rule={selected} canRetire={me.role === "checker" && me.id !== selected.made_by} onRetired={lib.reload} /> : null}
      </div>
    </div>
  );
}

function RuleDetail({ rule, canRetire, onRetired }: { rule: Rule; canRetire: boolean; onRetired: () => void }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function retire() {
    setBusy(true);
    setError(undefined);
    try {
      await api.post(`/rules/${rule.id}/retire`, { note });
      onRetired();
    } catch (e) {
      setError(failureMessage(e));
      setBusy(false);
    }
  }

  return (
    <Card
      className="min-w-0 xl:w-[440px] xl:shrink-0"
      eyebrow={`Selected · ${rule.code}`}
      title={rule.title}
      tag={<RuleStatusTag status={rule.status} />}
    >
      <div className="flex flex-col gap-4 pt-3">
        <p className="type-label text-muted">{`Source text · ${citation(rule)}`}</p>
        <Quote note={rule.source_doc_ref ? `${rule.source_doc_title} (${rule.source_doc_ref})` : rule.source_doc_title}>
          {rule.para_text}
        </Quote>
        {rule.related.map((r) => (
          <Quote key={r.para} note={r.note || undefined}>
            <span className="type-label text-muted">Para {r.para} · </span>
            {r.text}
          </Quote>
        ))}
        <p className="type-label text-muted">Machine rule</p>
        <RulePreview lines={ruleLines(rule)} />
        <p className="type-label text-muted">Boundary tests</p>
        {rule.tests.length ? <TestRows tests={rule.tests} /> : <Empty title="No tests">This rule has a value missing.</Empty>}
        <p className="type-label text-muted">Maker and checker</p>
        <div>
          <LeaderLine label="Drafted by" value={rule.made_by_name ?? "Unknown"} />
          <LeaderLine label="Approved by" value={rule.checked_by_name ?? "Not yet"} />
          <LeaderLine label="Approved on" value={formatDate(rule.checked_at)} />
          {rule.review_note ? <LeaderLine label="Note" value={rule.review_note} /> : null}
        </div>
        {canRetire ? (
          <div className="flex flex-col gap-3 border-t border-rule-2 pt-4">
            <Field label="Reason to retire" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Superseded by the amendment of …" />
            <div>
              <Button variant="secondary" onClick={retire} disabled={busy || !note.trim()}>
                {busy ? "Retiring" : "Retire this rule"}
              </Button>
            </div>
            {error ? <ErrorState title="Not retired" message={error} /> : null}
          </div>
        ) : null}
        {rule.problems.length ? <Tag tone="fail">{`${rule.problems.length} problem${rule.problems.length === 1 ? "" : "s"} with the source text`}</Tag> : null}
      </div>
    </Card>
  );
}
