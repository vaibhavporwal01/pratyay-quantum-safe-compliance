"use client";

import { useMe } from "@/components/app/RoleShell";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Figure, Figures, PageHead, Tag } from "@/components/ui";
import type { Overview } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";
import { QueueList } from "./QueueList";

const NUMBER_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

export function CheckerOverview() {
  const me = useMe();
  const overview = useApi<Overview>("/rules/overview");
  const first = me.name.split(/\s+/)[0];
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.reload} />;
  if (!overview.data) return <Loading />;
  const o = overview.data;
  const n = o.waiting_for_you.length;
  const count = NUMBER_WORDS[n] ?? String(n);

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 01 · Overview"
        title={n ? `${first}, ${count.toLowerCase()} rule draft${n === 1 ? "" : "s"} need${n === 1 ? "s" : ""} a checker.` : `${first}, nothing is waiting for you.`}
        subtitle={
          n
            ? "Each was prepared by someone else and is waiting for your signature. You cannot check a rule you drafted."
            : "New rule drafts from the compliance makers will appear here."
        }
        actions={n ? <Button href="/checker/review">Open review queue</Button> : undefined}
      />
      <Figures>
        <Figure label="Rule drafts" value={o.counts.draft} note={n === o.counts.draft ? "all for you" : `${n} for you`} />
        <Figure label="Rules in force" value={o.counts.approved} note="approved" />
        <Figure label="Sent back" value={o.counts.rejected} note="with the maker" />
        <Figure label="Retired" value={o.counts.retired} note="no longer applied" />
        <Figure label="Source documents" value={o.sources} note="stored with hash" />
      </Figures>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <DataCard
          className="min-w-0 flex-1"
          eyebrow="Queue"
          title="Waiting for you"
          tag={<Tag tone="stamp">{`${n} open`}</Tag>}
          state={{ ...overview, data: o.waiting_for_you }}
          isEmpty={(d) => d.length === 0}
          empty={<Empty title="Nothing to check">Drafts you made yourself are not listed; another checker signs those.</Empty>}
        >
          {(rules) => <QueueList rules={rules} />}
        </DataCard>
        <DataCard
          className="min-w-0 lg:w-[440px] lg:shrink-0"
          eyebrow="Latest"
          title="Recently checked"
          state={{ ...overview, data: o.recently_checked }}
          isEmpty={(d) => d.length === 0}
          empty={<Empty title="No rules checked yet" />}
        >
          {(rules) => <QueueList rules={rules} checked />}
        </DataCard>
      </div>
    </div>
  );
}
