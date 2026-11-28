"use client";

import { Card, PageHead, Tag, Status } from "@/components/ui";
import { ErrorState, Loading } from "@/components/app/States";
import { useApi } from "@/lib/useApi";
import type { TrustStatus } from "@/lib/api/trust";

const SIZES = [
  { name: "Ed25519", kind: "Classical signature", a: ["public key", 32], b: ["signature", 64] },
  { name: "RSA-2048", kind: "Classical signature", a: ["public key", 256], b: ["signature", 256] },
  { name: "ML-DSA-65", kind: "Post-quantum signature · FIPS 204", a: ["public key", 1952], b: ["signature", 3309] },
  { name: "ML-KEM-768", kind: "Post-quantum key exchange · FIPS 203", a: ["public key", 1184], b: ["ciphertext", 1088] },
  { name: "X25519 + ML-KEM-768", kind: "Hybrid key establishment", a: ["public key", 1216], b: ["ciphertext", 1120] },
] as const;
const MAX = 3309;

export function CryptoLab() {
  const trust = useApi<TrustStatus>("/trust/status");
  if (!trust.data && !trust.error) return <Loading label="Checking cryptographic services" />;
  if (trust.error) return <ErrorState message={trust.error} onRetry={trust.reload} />;
  const s = trust.data!;
  const items = [
    ["AES-256-GCM", "Field and audit metadata encryption", "FIPS 197 · SP 800-38D", s.encryption.configured],
    ["HMAC-SHA-256", "Email blind-index key", "RFC 2104", s.email_index.configured],
    ["SHA3-256", "Append-only ledger hash chain", "FIPS 202", s.hash.enabled],
    ["ML-DSA-65", "Ledger record signatures", "FIPS 204", s.signature.enabled],
  ] as const;
  return (
    <div className="flex flex-col gap-7">
      <PageHead eyebrow="§ 05 · Crypto lab" title="Cryptographic controls and live readiness."
        subtitle="Algorithm standards are shown alongside configuration and provider status reported by this API instance." />
      <Card eyebrow="Live deployment status" title="Cryptographic bill of materials">
        <div className="flex flex-col">{items.map(([alg, use, standard, enabled]) => (
          <div key={alg} className="flex flex-wrap items-center gap-3 border-b border-rule-2 py-3">
            <div className="min-w-0 flex-1"><p className="type-mono-medium text-ink">{alg}</p><p className="type-caption text-muted">{use}</p></div>
            <Tag>{standard}</Tag><Status status={enabled ? "pass" : "pending"} label={enabled ? "Configured" : "Not configured"} />
          </div>
        ))}</div>
      </Card>
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <Card eyebrow="Reference" title="Key and signature sizes" tag={<Tag>FIPS 203 · FIPS 204 · RFC 8032</Tag>} className="min-w-0 flex-1">
          <div className="flex flex-col">{SIZES.map((item) => (
            <div key={item.name} className="flex flex-col gap-2 border-b border-rule-2 py-4">
              <p className="flex flex-wrap items-baseline gap-x-2"><span className="type-body-medium text-ink">{item.name}</span><span className="type-caption text-muted">{item.kind}</span></p>
              {[item.a, item.b].map(([label, bytes], i) => (
                <div key={label} className="flex items-center gap-3"><span className="w-24 shrink-0 type-caption text-ink-2">{label}</span><span aria-hidden className={i ? "h-2 bg-stamp" : "h-2 bg-rule"} style={{ width: `${Math.max(2, (bytes / MAX) * 60)}%` }} /><span className="type-mono whitespace-nowrap text-ink">{bytes.toLocaleString("en-IN")} B</span></div>
              ))}
            </div>
          ))}</div>
        </Card>
        <Card eyebrow="Ledger" title="Current chain" className="min-w-0 lg:w-[360px] lg:shrink-0">
          <p className="type-small text-ink-2">Persisted records: {s.ledger.entries}</p>
          <p className="type-small text-ink-2">Latest sequence: {s.ledger.latest_seq ?? "-"}</p>
          <p className="type-small text-ink-2">Signer key ID: {s.signature.key_id ?? "Not available"}</p>
        </Card>
      </div>
    </div>
  );
}
