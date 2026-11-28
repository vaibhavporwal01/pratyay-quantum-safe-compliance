"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Card, LedgerRow, PageHead, Status, Tag, type StatusKind } from "@/components/ui";
import { Empty, ErrorState, Loading } from "@/components/app/States";
import {
  money,
  type DecisionRow,
  type DecisionVerification,
  type Replay,
} from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";
import type { TrustStatus } from "@/lib/api/trust";

export function VerifyView() {
  const params = useSearchParams();
  const router = useRouter();
  const decisions = useApi<DecisionRow[]>("/loans/decisions");
  const decided = (decisions.data ?? []).filter((r) => r.decision.outcome);
  const id = params.get("app") ?? decided[0]?.application.id ?? null;
  const replay = useApi<Replay>(id ? `/loans/applications/${id}/replay` : null);
  const verification = useApi<DecisionVerification>(
    id ? `/loans/applications/${id}/verification` : null,
  );
  const trust = useApi<TrustStatus>("/trust/status");

  const decisionLoading = decisions.loading || (!!id && (replay.loading || verification.loading));
  const unavailable = !!verification.error;

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Verify · read only"
        title="Check any decision without trusting us."
        subtitle="This view checks the stored decision against its SHA3-256 ledger hash, previous-hash link, ML-DSA signature and application binding, separately from rule replay."
      />
      <label className="flex flex-col gap-1.5">
        <span className="type-label text-ink-2">Decision</span>
        <select
          value={id ?? ""}
          onChange={(e) => router.replace(`/auditor/verify?app=${e.target.value}`)}
          className="h-12 w-full rounded-[2px] border border-stamp bg-white px-3 type-mono text-ink focus:outline-none"
        >
          {decisions.data === undefined ? <option value="">Loading decisions…</option> : null}
          {decided.map((r) => (
            <option key={r.application.id} value={r.application.id}>
              {`${r.application.ref} · ${r.application.borrower_name}`}
            </option>
          ))}
        </select>
      </label>

      {decisions.error ? <ErrorState message={decisions.error} onRetry={decisions.reload} /> : null}
      {decisions.data && decided.length === 0 ? (
        <Empty title="No decided applications yet">A decision appears here once a checker decides it.</Empty>
      ) : null}
      {id && decisionLoading ? <Loading label="Checking decision and ledger" /> : null}
      {replay.error ? <ErrorState message={replay.error} onRetry={replay.reload} /> : null}
      {verification.error ? <ErrorState message={verification.error} onRetry={verification.reload} /> : null}
      {id && replay.data && verification.data ? (
        <Result r={replay.data} verification={verification.data} trust={trust.data} trustError={trust.error} />
      ) : null}
      {trust.error ? <p className="type-small text-ink-2">Active key metadata unavailable: {trust.error}</p> : null}
    </div>
  );
}

function Result({
  r,
  verification,
  trust,
  trustError,
}: {
  r: Replay;
  verification: DecisionVerification;
  trust?: TrustStatus;
  trustError?: string;
}) {
  const replayOk = r.same_outcome && r.same_results && r.same_rules;
  const cryptoStatus: StatusKind =
    verification.status === "verified" ? "pass" :
    verification.status === "failed" ? "fail" : "pending";
  const cryptoLabel =
    verification.status === "verified" ? "Cryptographically verified" :
    verification.status === "failed" ? "Verification failed" :
    "Signature pending";

  const checks: { id: string; title: string; source: string; value: string; status: StatusKind }[] = [
    {
      id: "HASH",
      title: "Record hash",
      source: "SHA3-256 ledger entry hash",
      value: verification.hash ?? "No ledger hash",
      status: verification.checks.entry_hash === undefined ? "pending" : verification.checks.entry_hash ? "pass" : "fail",
    },
    {
      id: "LINK",
      title: "Chain link",
      source: "Previous entry hash linkage",
      value: verification.previous_hash ?? "No previous hash",
      status: verification.checks.previous_hash === undefined ? "pending" : verification.checks.previous_hash ? "pass" : "fail",
    },
    {
      id: "SIG",
      title: "PQC signature",
      source: verification.algorithm ?? "Signing algorithm unavailable",
      value: verification.signature_bytes ? `${verification.signature_bytes.toLocaleString()} signature bytes` : "No signature recorded",
      status: verification.checks.signature === undefined ? "pending" : verification.checks.signature ? "pass" : "fail",
    },
    {
      id: "KEY",
      title: "Key identifier",
      source: "Signing key associated with this ledger entry",
      value: verification.key_id ?? "No key identifier",
      status: verification.checks.key_id === undefined ? "pending" : verification.checks.key_id ? "pass" : "fail",
    },
    {
      id: "BIND",
      title: "Application binding",
      source: "Ledger decision belongs to this application",
      value: r.application.ref,
      status: verification.checks.application_binding === undefined ? "pending" : verification.checks.application_binding ? "pass" : "fail",
    },
    {
      id: "RULES",
      title: "Rule versions",
      source: `Rules in force on ${formatDate(r.on_date)}`,
      value: r.rules_used.filter((x) => x.startsWith("MF-0")).join(" · ") || r.rules_used.join(" · "),
      status: r.same_rules ? "pass" : "fail",
    },
    {
      id: "REPLAY",
      title: "Decision replay",
      source: "Same inputs and date, evaluated again",
      value: replayOk ? `${money(r.amount_paise)} · same result` : `stored ${r.stored_outcome} · replay ${r.replayed_outcome}`,
      status: replayOk ? "pass" : "fail",
    },
  ];

  const verified = verification.status === "verified";
  const title = verified
    ? (replayOk ? "Signature and replay verified" : "Signature verified; replay differs")
    : verification.status === "failed"
      ? "Cryptographic verification failed"
      : "Decision signature pending";

  return (
    <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
      <div className="flex min-w-0 flex-1 flex-col gap-7">
        <Card
          eyebrow={`${r.application.ref} · decision dated ${formatDate(r.on_date)}`}
          title={title}
          tag={<Tag>{cryptoLabel}</Tag>}
        >
          {checks.map((c) => (
            <LedgerRow key={c.id} id={c.id} title={c.title} source={c.source} value={c.value} status={c.status} />
          ))}
        </Card>
        <Card eyebrow="Replay result" title={replayOk ? "Stored rules and outcome reproduced" : "Replay differs from the stored decision"}>
          <div className="flex flex-col gap-3 pt-3">
            <Status status={replayOk ? "pass" : "fail"} label={replayOk ? "Replay matches" : "Replay differs"} />
            <p className="type-small text-ink-2">
              {replayOk
                ? `The rules in force on ${formatDate(r.on_date)} and the replayed outcome match the stored decision.`
                : `Stored outcome: ${r.stored_outcome}. Replayed outcome: ${r.replayed_outcome}. Different rules: ${r.different_results.join(", ") || "none reported"}.`}
            </p>
            <p className="type-small text-ink-2">Cryptographic verification is a separate check and does not prove that borrower-supplied information is factually true.</p>
          </div>
        </Card>
      </div>
      <div className="flex min-w-0 flex-col gap-7 lg:w-[420px] lg:shrink-0">
        <Card eyebrow="Ledger verification" title={cryptoLabel}>
          <div className="flex flex-col gap-3 pt-3">
            <Status status={cryptoStatus} label={cryptoLabel} />
            <p className="type-small text-ink-2">
              {verified
                ? "The entry hash, chain link, signature, key identifier and application binding passed server-side verification."
                : verification.status === "failed"
                  ? "At least one cryptographic integrity or application-binding check failed. Do not treat this receipt as verified."
                  : "No signed decision entry is available for this application yet."}
            </p>
            {verification.seq !== null ? <p className="type-mono text-ink-2">Ledger sequence #{verification.seq}</p> : null}
            {verification.created_at ? <p className="type-small text-ink-2">Recorded: {new Date(verification.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST</p> : null}
          </div>
        </Card>
        <Card eyebrow="Signing key metadata" title={trust?.signature.enabled ? "Active ML-DSA signer" : "Signer configuration"}>
          <div className="flex flex-col gap-2 pt-3">
            <p className="type-small text-ink-2">Algorithm: {verification.algorithm ?? trust?.signature.algorithm ?? "Unavailable"}</p>
            <p className="type-small text-ink-2">Standard: {trust?.signature.standard ?? "Unavailable"}</p>
            <p className="type-small text-ink-2">Key ID: {verification.key_id ?? "Not recorded"}</p>
            <p className="type-small text-ink-2">Public key configured: {trust ? (trust.signature.public_key_configured ? `${trust.signature.public_key_bytes} bytes` : "No") : "Unavailable"}</p>
            <p className="type-caption text-muted">Public key material and private signing material are not exposed in this view.</p>
            {trustError ? <p className="type-caption text-muted">{trustError}</p> : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
