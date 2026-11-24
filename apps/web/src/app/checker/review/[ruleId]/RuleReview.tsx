"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMe } from "@/components/app/RoleShell";
import { LeaderLine, Quote, RulePreview, RuleStatusTag, TestRows } from "@/components/app/RuleParts";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Card, Field, Icon, PageHead, Status, Tag } from "@/components/ui";
import { api, ApiFailure, failureMessage } from "@/lib/api/client";
import { citation, formatDate, ruleLines, shortDocName, type Rule, type SourceDoc } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

export function RuleReview() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const me = useMe();
  const router = useRouter();
  const rule = useApi<Rule>(`/rules/${ruleId}`);
  const doc = useApi<SourceDoc>(rule.data ? `/rules/sources/${rule.data.source_doc_id}` : null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [failure, setFailure] = useState<{ message: string; problems: string[] } | null>(null);

  if (rule.error) return <ErrorState message={rule.error} onRetry={rule.reload} />;
  if (!rule.data) return <Loading />;
  const r = rule.data;
  const isMaker = r.made_by === me.id;
  const passed = r.tests.filter((t) => t.passed).length;
  const checklist: [string, boolean][] = [
    [`Every number is in ${citation(r)}`, r.problems.length === 0],
    ["No value is missing", r.missing.length === 0],
    [r.tests.length ? `All ${r.tests.length} generated tests pass` : "Generated tests run", r.tests.length > 0 && passed === r.tests.length],
    ["Effective date is set", r.effective_from !== null],
    [`The maker (${r.made_by_name ?? "unknown"}) is not the checker (${me.name})`, !isMaker],
  ];
  const ready = checklist.every(([, ok]) => ok) && r.status === "draft";

  async function act(action: "approve" | "reject") {
    setBusy(action);
    setFailure(null);
    try {
      await api.post<Rule>(`/rules/${r.id}/${action}`, { note: note.trim() || null });
      router.push("/checker/review");
    } catch (e) {
      setFailure({ message: failureMessage(e), problems: e instanceof ApiFailure ? e.problems : [] });
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 02 · Review queue · ${r.code}`}
        title={r.status === "draft" ? `${r.code} is ready for your check.` : `${r.code} is ${r.status}.`}
        subtitle={
          isMaker
            ? "You drafted this rule, so another checker must approve it."
            : `Drafted by ${r.made_by_name ?? "a maker"} from ${shortDocName(r.source_doc_title)}, para ${r.source_para}. You did not write it, so you can check it.`
        }
        actions={
          r.status === "draft" && !isMaker ? (
            <>
              <Button variant="secondary" onClick={() => act("reject")} disabled={busy !== null || !note.trim()}>
                {busy === "reject" ? "Sending back" : "Send back"}
              </Button>
              <Button onClick={() => act("approve")} disabled={busy !== null || !ready} icon={<Icon name="check" size={16} />}>
                {busy === "approve" ? "Approving" : "Approve"}
              </Button>
            </>
          ) : (
            <RuleStatusTag status={r.status} />
          )
        }
      />
      {failure ? <ErrorState title="Not saved" message={failure.message} problems={failure.problems} /> : null}
      <div className="grid gap-7 lg:grid-cols-2">
        <Card
          className="min-w-0"
          eyebrow="Source"
          title={shortDocName(r.source_doc_title)}
          tag={<Tag tone="stamp">{r.effective_from ? `From ${formatDate(r.effective_from)}` : "No date"}</Tag>}
        >
          <div className="flex flex-col gap-3 pt-1">
            <div>
              <LeaderLine label="Issued" value={doc.data ? formatDate(doc.data.issued_on) : "Loading"} />
              <LeaderLine label="In force from" value={formatDate(r.effective_from)} />
              <LeaderLine label="Reference" value={r.source_doc_ref ?? "Not recorded"} />
            </div>
            <p className="type-label text-muted">Para {r.source_para} · original text</p>
            <Quote>{r.para_text}</Quote>
            {r.related.map((x) => (
              <div key={x.para} className="flex flex-col gap-2">
                <p className="type-label text-muted">Para {x.para} · related</p>
                <Quote note={x.note || undefined}>{x.text}</Quote>
              </div>
            ))}
            <p className="type-caption text-muted">Read the original paragraph before approving.</p>
          </div>
        </Card>
        <Card
          className="min-w-0"
          eyebrow={`Draft · ${r.origin === "auto" ? "suggested by Policy-to-Code" : "written by hand"}, edited by ${r.made_by_name ?? "the maker"}`}
          title="What the rule will do"
          tag={<Tag tone="neutral">{r.applies_to === "microfinance" ? "Microfinance" : "All loans"}</Tag>}
        >
          <div className="flex flex-col gap-3 pt-3">
            <RulePreview lines={ruleLines(r)} />
            {r.problems.length ? (
              <ErrorState title="Does not match the paragraph" message="The maker must fix these first." problems={r.problems} />
            ) : null}
          </div>
        </Card>
        <Card
          className="min-w-0"
          eyebrow="Generated tests"
          title={r.tests.length ? `${passed} of ${r.tests.length} pass` : "No tests yet"}
          tag={r.tests.length ? <Tag tone={passed === r.tests.length ? "pass" : "fail"}>{`${passed} / ${r.tests.length}`}</Tag> : undefined}
        >
          {r.tests.length ? (
            <TestRows tests={r.tests} />
          ) : (
            <div className="pt-3">
              <Empty title="Values missing">{`Not filled: ${r.missing.join(", ")}. Send it back to the maker.`}</Empty>
            </div>
          )}
        </Card>
        <Card
          className="min-w-0"
          eyebrow="Before you approve"
          title="Checklist"
          tag={<Tag tone={ready ? "pass" : "refer"}>{ready ? "All checked" : "Open items"}</Tag>}
        >
          <ul className="flex flex-col">
            {checklist.map(([label, ok]) => (
              <li key={label} className="flex items-center gap-3 border-b border-rule-2 py-3">
                <Status status={ok ? "pass" : "fail"} label={ok ? "Yes" : "No"} />
                <span className="min-w-0 flex-1 type-body text-ink">{label}</span>
              </li>
            ))}
          </ul>
          {r.status === "draft" && !isMaker ? (
            <div className="flex flex-col gap-3 pt-4">
              <Field
                label="Note to the maker"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                hint="Needed to send it back. Kept with the rule and in the audit log."
              />
            </div>
          ) : r.review_note ? (
            <div className="pt-3">
              <LeaderLine label="Note" value={r.review_note} />
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
