"use client";

import { Card, PageHead, Status } from "@/components/ui";

/** Signing keys (85:11574). HOOK(Pulkit): keys, fingerprints and rotation come from the trust module. */
export function KeysView() {
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 02 · Admin · Signing keys"
        title="The key that will sign every record."
        subtitle="Only the public half will be shown. Old keys are retired, never deleted, so every past record can still be verified."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <Card eyebrow="Active key" title="No signing key yet" className="min-w-0 flex-1">
          <div className="flex flex-col gap-3 pt-3">
            <Status status="pending" label="Signing not enabled" />
            <p className="type-small text-ink-2">The trust module creates an ML-DSA-65 key pair (FIPS 204). Its algorithm, public key size, fingerprint and the records it signed appear here when signing is enabled.</p>
          </div>
        </Card>
        <Card eyebrow="How rotation will work" title="Rotate without breaking the chain" className="min-w-0 lg:w-[440px] lg:shrink-0">
          <ol className="flex flex-col">
            {[
              "Generate a new ML-DSA-65 key pair.",
              "Write a key_rotated record, signed with the old key, naming the new public key.",
              "Sign every later record with the new key.",
              "Keep the old public key so past records verify.",
            ].map((t, i) => (
              <li key={t} className="border-b border-rule-2 py-3 type-small text-ink">{`${i + 1} · ${t}`}</li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
