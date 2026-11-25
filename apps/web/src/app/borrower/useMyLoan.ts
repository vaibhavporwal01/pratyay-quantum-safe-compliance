"use client";

import { useSearchParams } from "next/navigation";
import type { AppSummary, Detail } from "@/lib/api/loans";
import { useApi } from "@/lib/useApi";

/** The borrower's application: ?app=<id>, else the newest. Loading, error and empty states. */
export function useMyLoan() {
  const params = useSearchParams();
  const list = useApi<AppSummary[]>("/loans/applications");
  const id = params.get("app") ?? list.data?.[0]?.id ?? null;
  const detail = useApi<Detail>(id ? `/loans/applications/${id}` : null);
  return {
    list,
    detail,
    none: list.data !== undefined && list.data.length === 0,
    error: list.error ?? detail.error,
    reload: () => {
      list.reload();
      detail.reload();
    },
  };
}
