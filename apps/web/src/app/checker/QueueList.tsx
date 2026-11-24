import Link from "next/link";
import { RuleStatusTag } from "@/components/app/RuleParts";
import { Status, Tag } from "@/components/ui";
import { citation, formatDate, type Rule } from "@/lib/api/rules";

/** Rule drafts waiting for a checker, or rules already checked. */
export function QueueList({ rules, checked = false }: { rules: Rule[]; checked?: boolean }) {
  return (
    <ul className="flex flex-col">
      {rules.map((r) => (
        <li key={r.id}>
          <Link
            href={checked ? `/rules/library?rule=${r.id}` : `/checker/review/${r.id}`}
            className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-rule-2 py-3.5 hover:bg-paper"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <p className="type-body-medium text-ink">
                {r.code} · {r.title}
              </p>
              <p className="type-small text-ink-2">
                {checked
                  ? `${r.checked_by_name ?? "Checker"} · ${formatDate(r.checked_at)}${r.review_note ? ` · ${r.review_note}` : ""}`
                  : `${citation(r)} · drafted by ${r.made_by_name ?? "unknown"} on ${formatDate(r.updated_at)}`}
              </p>
            </div>
            {checked ? (
              <RuleStatusTag status={r.status} />
            ) : (
              <>
                <Tag tone="neutral">Rule draft</Tag>
                <Status status={r.problems.length || r.missing.length ? "flagged" : "pending"} label={r.problems.length || r.missing.length ? "Needs work" : "Pending"} />
              </>
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}
