"use client";

import { Card, PageHead, Tag } from "@/components/ui";

/* Sizes from the standards: Ed25519 (RFC 8032), RSA-2048, ML-DSA-65 (FIPS 204), ML-KEM-768
 * (FIPS 203). Hybrid X25519 + ML-KEM-768 is the sum of the two. Nothing here signs anything. */
const SIZES = [
  { name: "Ed25519", kind: "Classical signature", a: ["public key", 32], b: ["signature", 64] },
  { name: "RSA-2048", kind: "Classical signature", a: ["public key", 256], b: ["signature", 256] },
  { name: "ML-DSA-65", kind: "Post-quantum signature · FIPS 204", a: ["public key", 1952], b: ["signature", 3309] },
  { name: "ML-KEM-768", kind: "Post-quantum key exchange · FIPS 203", a: ["public key", 1184], b: ["ciphertext", 1088] },
  { name: "X25519 + ML-KEM-768", kind: "Hybrid key wrap", a: ["public key", 1216], b: ["ciphertext", 1120] },
] as const;

const MAX = 3309;

// HOOK(Pulkit): the status of each algorithm comes from the trust module once it is in use.
const CBOM = [
  ["SHA3-256", "Hash chain", "FIPS 202"],
  ["ML-DSA-65", "Record and rule signing", "FIPS 204"],
  ["ML-KEM-768 + X25519", "Key wrapping", "FIPS 203"],
  ["AES-256-GCM", "Field encryption", "FIPS 197, SP 800-38D"],
] as const;

export function CryptoLab() {
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 05 · Crypto lab"
        title="What each key costs, and why we chose these."
        subtitle="Sizes come from the standards. Signing is not enabled yet, so every algorithm here is planned, not in use."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <Card eyebrow="Bytes on the wire" title="Key and signature sizes" tag={<Tag>FIPS 203 · FIPS 204 · RFC 8032</Tag>} className="min-w-0 flex-1">
          <div className="flex flex-col">
            {SIZES.map((s) => (
              <div key={s.name} className="flex flex-col gap-2 border-b border-rule-2 py-4">
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <span className="type-body-medium text-ink">{s.name}</span>
                  <span className="type-caption text-muted">{s.kind}</span>
                </p>
                {[s.a, s.b].map(([label, bytes], i) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="w-20 shrink-0 type-caption text-ink-2">{label}</span>
                    <span aria-hidden className={i ? "h-2 bg-stamp" : "h-2 bg-rule"} style={{ width: `${Math.max(2, (bytes / MAX) * 60)}%` }} />
                    <span className="type-mono whitespace-nowrap text-ink">{`${bytes.toLocaleString("en-IN")} B`}</span>
                  </div>
                ))}
              </div>
            ))}
            <p className="pt-3 type-caption text-muted">Ed25519 sizes from RFC 8032. An RSA-2048 key and signature are each 256 bytes. Post-quantum sizes from FIPS 203 and FIPS 204.</p>
          </div>
        </Card>
        <Card eyebrow="For the Q-SAFE review" title="Cryptographic bill of materials" className="min-w-0 lg:w-[440px] lg:shrink-0">
          <div className="flex flex-col">
            {CBOM.map(([alg, use, std]) => (
              <div key={alg} className="flex items-center gap-3 border-b border-rule-2 py-3">
                <div className="flex min-w-0 flex-1 flex-col">
                  <p className="type-mono-medium text-ink">{alg}</p>
                  <p className="type-caption text-muted">{use}</p>
                </div>
                <Tag>{std}</Tag>
                <Tag tone="refer">Planned</Tag>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
