"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Card, LedgerRow, PageHead, Status, Tag, type StatusKind } from "@/components/ui";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import { money, type DecisionRow, type Replay } from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

/** Verify (75:12325) and the tampered view (78:11182): the replay decides which one shows. */
export function VerifyView() {
  const params = useSearchParams();
  const router = useRouter();
  const decisions = useApi<DecisionRow[]>("/loans/decisions");
  const decided = (decisions.data ?? []).filter((r) => r.decision.outcome);
  const id = params.get("app") ?? decided[0]?.application.id ?? null;
  const replay = useApi<Replay>(id ? `/loans/applications/${id}/replay` : null);
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Verify · read only"
        title="Check any decision without trusting us."
        subtitle="Two checks work today: the rules in force on the day, and a replay of the same inputs. Hash, chain and signature checks are available when signing is enabled."
      />
      <label className="flex flex-col gap-1.5">
        <span className="type-label text-ink-2">Decision</span>
        <select
          value={id ?? ""}
          onChange={(e) => router.replace(`/auditor/verify?app=${e.target.value}`)}
          className="h-12 w-full rounded-[2px] border border-stamp bg-white px-3 type-mono text-ink focus:outline-none"
        >
          {decisions.data === undefined ? <option>Loading</option> : null}
          {decided.map((r) => (
            <option key={r.application.id} value={r.application.id}>
              {`${r.application.ref} · ${r.application.borrower_name}`}
            </option>
          ))}
        </select>
      </label>
      {decisions.error ? <ErrorState message={decisions.error} onRetry={decisions.reload} /> : null}
      {decisions.data && decided.length === 0 ? <Empty title="No decided applications yet">A decision appears here once a checker decides it.</Empty> : null}
      {replay.error ? <ErrorState message={replay.error} onRetry={replay.reload} /> : null}
      {id && !replay.data && !replay.error ? <Loading label="Replaying" /> : null}
      {replay.data ? <Result r={replay.data} /> : null}
    </div>
  );
}

function Result({ r }: { r: Replay }) {
  const replayOk = r.same_outcome && r.same_results;
  const ok = replayOk && r.same_rules;
  const pending = "Available when signing is enabled";
  // HOOK(Pulkit): HASH, LINK and SIG come from ledger.verify(session, seq) -> VerifyReport.
  const checks: { id: string; title: string; source: string; value: string; status: StatusKind; label?: string }[] = [
    { id: "HASH", title: "Record hash", source: "SHA3-256 of the record body", value: pending, status: "pending", label: "Pending" },
    { id: "LINK", title: "Chain link", source: "Holds the hash of the record before", value: pending, status: "pending", label: "Pending" },
    { id: "SIG", title: "Signature", source: "ML-DSA-65 with Lender A's public key", value: pending, status: "pending", label: "Pending" },
    {
      id: "RULES",
      title: "Rule versions",
      source: `Rules in force on ${formatDate(r.on_date)}`,
      value: r.rules_used.filter((x) => x.startsWith("MF-0")).join(" · "),
      status: r.same_rules ? "pass" : "fail",
    },
    {
      id: "REPLAY",
      title: "Replay",
      source: "Same inputs, same date, run today",
      value: replayOk ? `${money(r.amount_paise)} · same result` : `stored ${r.stored_outcome} · replay ${r.replayed_outcome}`,
      status: replayOk ? "pass" : "fail",
    },
  ];
  return (
    <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
      <div className="flex min-w-0 flex-1 flex-col gap-7">
        <Card
          eyebrow={`${r.application.ref} · engine run of ${formatDate(r.on_date)}`}
          title={ok ? "Two checks pass, three wait for signing" : "The replay does not match the stored record"}
          tag={<Tag tone={ok ? "pass" : "fail"}>{ok ? "Replay verified" : "Changed"}</Tag>}
        >
          {checks.map((c) => (
            <LedgerRow key={c.id} id={c.id} title={c.title} source={c.source} value={c.value} status={c.status} />
          ))}
        </Card>
        <Card eyebrow="Plain words" title="What this proves">
          <ul className="flex flex-col">
            {(ok
              ? [
                  `The rules in force on ${formatDate(r.on_date)} are the ones the decision used.`,
                  `Running the same inputs today gives the same result: ${r.replayed_outcome} at ${money(r.amount_paise)}.`,
                  "It does not yet prove the record was not changed: that needs the hash chain and signature.",
                  "It does not prove the income declared was true. That is what bank statements are for.",
                ]
              : [
                  r.same_rules ? "The rules of that day are unchanged." : `The rules in force that day now read ${r.rules_now.join(", ")}, not ${r.rules_used.join(", ")}.`,
                  `Replaying gives ${r.replayed_outcome}; the stored record says ${r.stored_outcome}.`,
                  r.different_results.length ? `Rules with a different result: ${r.different_results.join(", ")}.` : "Every rule gives the same result; the overall outcome differs.",
                ]
            ).map((t) => (
              <li key={t} className="border-b border-rule-2 py-3 type-body text-ink">
                {t}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <div className="flex min-w-0 flex-col gap-7 lg:w-[420px] lg:shrink-0">
        <Card eyebrow="Result" title={ok ? "Replay verified, signature pending" : "Not verified"}>
          <div className="flex flex-col gap-3 pt-3">
            <Status status={ok ? "pass" : "fail"} label={ok ? "Replay matches" : "Replay differs"} />
            <Status status="pending" label="Signature pending" />
            <p className="type-small text-ink-2">Verification available when signing is enabled. This check is read only and changes nothing.</p>
          </div>
        </Card>
        {/* HOOK(Pulkit): Lender A's public key, algorithm and fingerprint from the trust module. */}
        <Card eyebrow="Lender A" title="Public key">
          <p className="pt-3 type-small text-ink-2">No signing key yet. The key and its fingerprint appear here when signing is enabled.</p>
        </Card>
      </div>
    </div>
  );
}
