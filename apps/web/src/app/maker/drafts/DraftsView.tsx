"use client";

import Link from "next/link";
import { RuleStatusTag } from "@/components/app/RuleParts";
import { DataCard, Empty } from "@/components/app/States";
import { Button, PageHead, Table, TableCount, Tag, type Column } from "@/components/ui";
import { citation, formatDate, type Rule } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

const columns: Column<Rule>[] = [
  { key: "code", header: "ID", width: 70, kind: "mono", render: (r) => r.code },
  {
    key: "title",
    header: "Rule",
    width: 300,
    kind: "primary",
    render: (r) => (
      <Link href={`/maker/builder?rule=${r.id}`} className="type-body-medium text-ink underline-offset-2 hover:underline">
        {r.title}
      </Link>
    ),
  },
  { key: "source", header: "Source", width: 130, render: (r) => `${citation(r)}` },
  { key: "status", header: "Status", width: 110, kind: "node", render: (r) => <RuleStatusTag status={r.status} /> },
  {
    key: "note",
    header: "Checker note",
    width: 260,
    render: (r) => (r.status === "rejected" ? `${r.checked_by_name ?? "Checker"}: ${r.review_note ?? ""}` : "Waiting for a checker"),
  },
  { key: "updated", header: "Updated", kind: "mono", render: (r) => formatDate(r.updated_at) },
];

export function DraftsView() {
  const drafts = useApi<Rule[]>("/rules?mine=true&status=draft&status=rejected");
  const sentBack = drafts.data?.filter((r) => r.status === "rejected").length ?? 0;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Rules · Drafts"
        title="Your drafts, and what came back."
        subtitle="Drafts wait for a checker. A rule sent back carries the checker's note; edit it and it goes back into review."
        actions={<Button href="/maker/sources">Draft from a circular</Button>}
      />
      <DataCard
        eyebrow="Made by you"
        title="Drafts"
        tag={<Tag tone={sentBack ? "fail" : "stamp"}>{sentBack ? `${sentBack} sent back` : `${drafts.data?.length} in review`}</Tag>}
        state={drafts}
        isEmpty={(d) => d.length === 0}
        empty={<Empty title="No drafts">Open a source document and build a rule from one of its paragraphs.</Empty>}
      >
        {(data) => (
          <div className="overflow-x-auto">
            <Table
              className="min-w-[1000px]"
              caption="Your drafts"
              columns={columns}
              rows={data}
              rowKey={(r) => r.id}
              footer={<TableCount>Open a rule to edit it. Approved rules move to the rule library.</TableCount>}
            />
          </div>
        )}
      </DataCard>
    </div>
  );
}
