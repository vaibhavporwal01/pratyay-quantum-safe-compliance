"use client";

import { useParams } from "next/navigation";
import { KfsDocument } from "@/components/app/KfsDocument";
import { ErrorState, Loading, Empty } from "@/components/app/States";
import { Button, PageHead } from "@/components/ui";
import { currentKfs, type Detail } from "@/lib/api/loans";
import { formatDate } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

export function KfsView() {
  const { id } = useParams<{ id: string }>();
  const detail = useApi<Detail>(`/loans/applications/${id}`);
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return <Loading />;
  const d = detail.data;
  const kfs = currentKfs(d);
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 04 · Key facts statement · ${d.application.ref}`}
        title={`Key Facts Statement for ${d.application.borrower_name}.`}
        subtitle={
          kfs
            ? `Issued ${formatDate(kfs.issued_on)}${kfs.valid_until ? ` and valid until ${formatDate(kfs.valid_until)} (${kfs.validity_working_days} working days, KF-01)` : ""}. Acceptance by one-time code arrives with sign-in.`
            : "No KFS yet."
        }
        actions={
          <Button variant="secondary" href={`/officer/decisions/${d.application.id}`}>
            Back to the decision
          </Button>
        }
      />
      {kfs ? <KfsDocument d={d} kfs={kfs} /> : <Empty title="No KFS">The amount, tenor or rate is missing, so the KFS cannot be computed.</Empty>}
    </div>
  );
}
