"use client";

import { Card, PageHead, Status, Tag } from "@/components/ui";
import { ErrorState, Loading } from "@/components/app/States";
import { useApi } from "@/lib/useApi";
import type { ChainVerification, TrustStatus } from "@/lib/api/trust";

export function KeysView() {
  const trust = useApi<TrustStatus>("/trust/status");
  const chain = useApi<ChainVerification>("/trust/ledger/verify");

  if (!trust.data && !trust.error) return <Loading label="Loading cryptographic key status" />;
  if (trust.error) return <ErrorState message={trust.error} onRetry={trust.reload} />;

  const s = trust.data!;
  const sig = s.signature;
  const chainStatus = chain.loading ? "pending" : chain.error ? "pending" : chain.data?.ok ? "pass" : chain.data ? "fail" : "pending";

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Admin · Signing keys"
        title="The key that signs every record."
        subtitle="Live cryptographic configuration and ledger health. Only public key metadata is displayed; private signing material remains on the API server."
      />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card eyebrow="Active key" title={sig.enabled ? "ML-DSA signing enabled" : "Signing not ready"}>
          <div className="flex flex-col gap-3 pt-3">
            <Status status={sig.enabled ? "pass" : "pending"} label={sig.enabled ? "PQC signer enabled" : "PQC signer not configured"} />
            <div className="flex flex-wrap gap-2"><Tag>{sig.algorithm}</Tag><Tag>{sig.standard}</Tag></div>
            <p className="type-small text-ink-2">Native provider: {sig.provider_available ? "available" : "unavailable"}</p>
            <p className="type-small text-ink-2">Private key: {sig.private_key_configured ? "configured (hidden)" : "missing"}</p>
            <p className="type-small text-ink-2">Public key: {sig.public_key_configured ? `${sig.public_key_bytes} bytes` : "missing"}</p>
            <p className="type-mono break-all text-ink-2">Key ID: {sig.key_id ?? "-"}</p>
          </div>
        </Card>
        <Card eyebrow="Ledger health" title={`${s.ledger.entries} ledger entries`}>
          <div className="flex flex-col gap-3 pt-3">
            <Status status={chainStatus} label={chain.loading ? "Verifying ledger…" : chain.error ? "Verification unavailable" : chain.data?.ok ? "All entries verified" : chain.data ? "Ledger verification failed" : "Not checked"} />
            <p className="type-small text-ink-2">Latest sequence: {s.ledger.latest_seq ?? "No entries"}</p>
            <p className="type-small text-ink-2">Entries checked: {chain.data?.checked ?? "Unavailable"}</p>
            <p className="type-small text-ink-2">SHA3-256 chain hashing: {s.hash.enabled ? "enabled" : "disabled"}</p>
            {chain.data && !chain.data.ok ? <p className="type-small text-red-700">First invalid sequence: {chain.data.first_invalid_seq ?? "unknown"}</p> : null}
            {chain.error ? <p className="type-caption text-muted">{chain.error}</p> : null}
          </div>
        </Card>
      </div>
      <Card eyebrow="Rotation policy" title="Rotate without breaking historical verification">
        <ol className="flex flex-col">{[
          "Generate a new ML-DSA key pair in the protected API environment.",
          "Append a key_rotated event signed by the currently active key.",
          "Use the new key for subsequent ledger records.",
          "Retain old public keys with their records so historical signatures remain verifiable."
        ].map((t, i) => <li key={t} className="border-b border-rule-2 py-3 type-small text-ink">{i + 1} · {t}</li>)}</ol>
      </Card>
    </div>
  );
}
