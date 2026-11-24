"use client";

import Link from "next/link";
import { ruleNote } from "@/components/app/LoanParts";
import { useMe } from "@/components/app/RoleShell";
import { DataCard, Empty, ErrorState, Loading } from "@/components/app/States";
import { Button, Figure, Figures, Icon, PageHead, Status, Tag } from "@/components/ui";
import { appKind, appKindLabel, money, shortDateTime, type AppStatus, type AppSummary } from "@/lib/api/loans";
import { useApi } from "@/lib/useApi";

const WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

type Overview = { counts: Record<AppStatus, number>; waiting: AppSummary[] };

export function OfficerOverview() {
  const me = useMe();
  const overview = useApi<Overview>("/loans/overview");
  const all = useApi<AppSummary[]>("/loans/applications");
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.reload} />;
  if (!overview.data) return <Loading />;
  const { counts, waiting } = overview.data;
  const n = waiting.length;
  const first = me.name.split(/\s+/)[0];
  const decided = counts.approved + counts.approved_modified + counts.rejected;
  const recent = (all.data ?? []).filter((a) => a.status !== "evaluated").slice(0, 5);

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 01 · Overview"
        title={n ? `${first}, ${(WORDS[n] ?? String(n)).toLowerCase()} application${n === 1 ? " is" : "s are"} waiting for you.` : `${first}, nothing is waiting for you.`}
        subtitle="Every line opens the rule-by-rule record. Figures are for Lender A."
        actions={
          <Button href="/officer/applications/new" icon={<Icon name="plus" size={16} />}>
            New application
          </Button>
        }
      />
      <Figures>
        <Figure label="Decided" value={decided} note="by a checker" />
        <Figure label="Approved as asked" value={counts.approved} note="all rules pass" />
        <Figure label="Approved, modified" value={counts.approved_modified} note="amount cut to fit a rule" />
        <Figure label="Declined" value={counts.rejected} note="each names its rule" />
        <Figure label="With the checker" value={counts.recommended} note="waiting for a second person" />
      </Figures>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-7">
          <DataCard
            eyebrow="Queue"
            title="Waiting for you"
            tag={<Tag tone="stamp">{`${n} open`}</Tag>}
            state={{ ...overview, data: waiting }}
            isEmpty={(d) => d.length === 0}
            empty={<Empty title="Nothing waiting">New applications from borrowers and from you appear here after the rules run.</Empty>}
          >
            {(apps) => <AppLines apps={apps} />}
          </DataCard>
          <DataCard
            eyebrow="Latest"
            title="Recommended and decided"
            state={{ ...all, data: all.data ? recent : undefined }}
            isEmpty={(d) => d.length === 0}
            empty={<Empty title="Nothing decided yet" />}
          >
            {(apps) => <AppLines apps={apps} />}
          </DataCard>
        </div>
        <div className="flex min-w-0 flex-col gap-7 lg:w-[440px] lg:shrink-0">
          {/* HOOK(Pulkit): chain health comes from ledger.verify_all when signing lands. */}
          <DataCard eyebrow="Trust layer" title="Chain health" tag={<Tag>Not enabled</Tag>} state={{ ...overview, data: true }}>
            {() => (
              <div className="flex flex-col gap-3 pt-3">
                <Status status="pending" label="Signature pending" />
                <p className="type-small text-ink-2">
                  {`${decided} decision${decided === 1 ? " is" : "s are"} recorded and waiting to be signed. Verification is available when signing is enabled.`}
                </p>
              </div>
            )}
          </DataCard>
        </div>
      </div>
    </div>
  );
}

function AppLines({ apps }: { apps: AppSummary[] }) {
  return (
    <ul className="flex flex-col">
      {apps.map((a) => (
        <li key={a.id}>
          <Link
            href={`/officer/decisions/${a.id}`}
            className="flex flex-col gap-2 border-b border-rule-2 py-3.5 hover:bg-paper sm:flex-row sm:items-center sm:gap-4"
          >
            <span className="w-32 shrink-0 type-mono text-ink-2">{a.ref}</span>
            <span className="flex w-36 shrink-0 flex-col">
              <span className="type-body-medium text-ink">{a.borrower_name}</span>
              <span className="type-caption text-muted">{shortDateTime(a.updated_at)}</span>
            </span>
            <span className="w-24 shrink-0 type-mono text-ink">{money(a.approved_paise ?? a.amount_paise)}</span>
            <span className="min-w-0 flex-1 type-small text-ink-2">{ruleNote(a)}</span>
            <Status status={appKind(a)} label={appKindLabel(a)} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
