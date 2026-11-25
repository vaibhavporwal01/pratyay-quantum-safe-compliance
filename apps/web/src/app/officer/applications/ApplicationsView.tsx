"use client";

import { useState } from "react";
import { ApplicationTable } from "@/components/app/LoanParts";
import { DataCard, Empty } from "@/components/app/States";
import { Button, PageHead, TableCount, Tag } from "@/components/ui";
import type { AppStatus, AppSummary } from "@/lib/api/loans";
import { cn } from "@/lib/cn";
import { useApi } from "@/lib/useApi";

const FILTERS: { key: string; label: string; statuses: AppStatus[] | null }[] = [
  { key: "all", label: "All", statuses: null },
  { key: "officer", label: "With officer", statuses: ["evaluated"] },
  { key: "checker", label: "With checker", statuses: ["recommended"] },
  { key: "decided", label: "Decided", statuses: ["approved", "approved_modified", "rejected"] },
];

/** The officer's Applications tab (every application) and Decisions tab (recommended or decided). */
export function ApplicationsView({ mode }: { mode: "all" | "decisions" }) {
  const apps = useApi<AppSummary[]>("/loans/applications");
  const [filter, setFilter] = useState(mode === "decisions" ? "decided" : "all");
  const filters = mode === "decisions" ? FILTERS.filter((f) => f.key === "checker" || f.key === "decided") : FILTERS;
  const active = FILTERS.find((f) => f.key === filter)!;
  const count = (f: (typeof FILTERS)[number]) =>
    (apps.data ?? []).filter((a) => !f.statuses || f.statuses.includes(a.status)).length;
  const rows = (apps.data ?? []).filter((a) => !active.statuses || active.statuses.includes(a.status));
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={mode === "decisions" ? "§ 03 · Decisions" : `§ 02 · Applications${apps.data ? ` · ${apps.data.length} in all` : ""}`}
        title={mode === "decisions" ? "Decisions" : "Applications"}
        subtitle={
          mode === "decisions"
            ? "Recommendations waiting for a checker, and decisions a checker has made. Open one to see every rule and its paragraph."
            : "Every application, where it is, and which rule is holding it. Open one to run checks or recommend."
        }
        actions={<Button href="/officer/applications/new">New application</Button>}
      />
      <div role="group" aria-label="Filter applications" className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.key}
            type="button"
            aria-pressed={filter === f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              "rounded-[2px] border px-[7px] py-[3px] type-label",
              filter === f.key ? "border-ink bg-ink text-paper" : "border-rule bg-paper-2 text-ink-2 hover:border-ink",
            )}
          >
            {`${f.label} · ${count(f)}`}
          </button>
        ))}
      </div>
      <DataCard
        eyebrow="Lender A"
        title={active.key === "all" ? "All applications" : active.label}
        tag={<Tag>Newest first</Tag>}
        state={{ ...apps, data: apps.data ? rows : undefined }}
        isEmpty={(d) => d.length === 0}
        empty={<Empty title="No applications here">Applications appear once a borrower or an officer submits one.</Empty>}
      >
        {(data) => (
          <>
            <ApplicationTable apps={data} caption="Applications" href={(a) => `/officer/decisions/${a.id}`} />
            <div className="pt-3.5">
              <TableCount>{`Showing ${data.length} of ${apps.data?.length ?? 0}`}</TableCount>
            </div>
          </>
        )}
      </DataCard>
    </div>
  );
}
