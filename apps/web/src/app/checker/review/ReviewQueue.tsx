"use client";

import { useMe } from "@/components/app/RoleShell";
import { DataCard, Empty } from "@/components/app/States";
import { PageHead, Tag } from "@/components/ui";
import type { Rule } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";
import { QueueList } from "../QueueList";

export function ReviewQueue() {
  const me = useMe();
  const drafts = useApi<Rule[]>("/rules?status=draft");
  const mine = drafts.data?.filter((r) => r.made_by === me.id) ?? [];
  const others = drafts.data?.filter((r) => r.made_by !== me.id);
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 02 · Review queue${others ? ` · ${others.length} draft${others.length === 1 ? "" : "s"} waiting` : ""}`}
        title="Rule drafts waiting for a checker."
        subtitle="Open a draft to read its paragraph, its generated tests and the checklist, then approve it or send it back with a note."
      />
      <DataCard
        eyebrow="Queue"
        title="Waiting for you"
        tag={<Tag tone="stamp">{`${others?.length} open`}</Tag>}
        state={{ ...drafts, data: others }}
        isEmpty={(d) => d.length === 0}
        empty={<Empty title="The queue is clear">New drafts from the compliance makers will appear here.</Empty>}
      >
        {(rules) => <QueueList rules={rules} />}
      </DataCard>
      {mine.length ? (
        <DataCard eyebrow="Drafted by you" title="Another checker signs these" state={{ ...drafts, data: mine }}>
          {(rules) => <QueueList rules={rules} />}
        </DataCard>
      ) : null}
    </div>
  );
}
