import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Detail, Kfs, RuleResult } from "@/lib/api/loans";
import { kfsRows, LoanReceipt, RuleResults } from "../LoanParts";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(cleanup);

const kfs: Kfs = {
  amount_paise: 6_600_000, tenor_months: 24, rate_bps_month: 200, rate_month_percent: "2", rate_year_percent: "24.00",
  emi_paise: 348_900, emi_exact: "₹3,489.49", instalments: 24, first_due_on: "2026-12-25",
  fees: [{ name: "Processing fee", paise: 66_000, payable_to: "lender", assumed: true, basis: "1% of the loan" }],
  fees_total_paise: 66_000, net_disbursal_paise: 6_534_000, total_interest_paise: 1_773_600, total_payable_paise: 8_373_600,
  monthly_irr_percent: "2.089", apr_percent: "25.07", apr_method: "", rounding: "", issued_on: "2026-11-25",
  valid_until: "2026-11-30", validity_working_days: 3, validity_anchor: "RBC para 29(2)", notes: [],
};

const r = (code: string, status: RuleResult["status"], stage: RuleResult["stage"] = "origination"): RuleResult => ({
  rule_id: code, code, version: 1, title: `${code} title`, stage, applies_to: "microfinance", status,
  message: "", anchor: "CF para 55", para_text: "", values: {}, missing: [],
});

const results = [r("MF-01", "pass"), r("MF-02", "pass"), r("MF-05", "not_checked", "recovery")];

const detail: Detail = {
  application: {
    id: "a", ref: "APP-2026-0142", borrower_id: "b", borrower_name: "Rekha K.", purpose: null, product: "MFL",
    product_name: "Microfinance term loan", amount_paise: 8_000_000, tenor_months: 24, rate_bps_month: 200,
    household_income_annual_paise: 26_400_000, existing_monthly_repayments_paise: 750_000, collateral: false,
    status: "approved_modified", created_at: "2026-11-25T05:00:00Z", updated_at: "2026-11-25T06:00:00Z", submitted_by_name: "Rekha K.",
  },
  evaluation: null,
  final_evaluation: { id: "e", on_date: "2026-11-25", amount_paise: 6_600_000, outcome: "pass", microfinance: true, results, rules_used: [], offer: null, kfs, created_at: "" },
  recommended_evaluation: null,
  decision: {
    id: "d", recommendation: "approve_modified", recommended_paise: 6_600_000, officer_id: "o", officer_name: "Anita Sharma",
    officer_note: null, recommended_at: "2026-11-25T05:30:00Z", outcome: "approved_modified", approved_paise: 6_600_000,
    checker_id: "c", checker_name: "Rahul Mehta", checker_note: null, decided_at: "2026-11-25T06:12:00Z", ledger_seq: null, signature: "pending",
  },
  events: [],
};

describe("loan parts", () => {
  it("shows an unsigned receipt with no hash", () => {
    render(<LoanReceipt d={detail} />);
    expect(screen.getByText("Signature pending")).toBeTruthy();
    expect(screen.queryByText(/SHA3-256/)).toBeNull();
    expect(screen.getByText("₹66,000")).toBeTruthy();
    expect(screen.getByText("25.07%")).toBeTruthy();
    expect(screen.getByText("Approve with modified amount")).toBeTruthy();
  });

  it("groups results by stage", () => {
    render(<RuleResults results={results} />);
    expect(screen.getByText("A · Checked at origination")).toBeTruthy();
    expect(screen.getByText("B · Later stages, not checked now")).toBeTruthy();
    expect(screen.getAllByText("Pass")).toHaveLength(2);
  });

  it("lists the KFS figures, the assumed fee and the total", () => {
    const rows = kfsRows(kfs);
    expect(rows.find(([l]) => l === "Processing fee")?.[2]).toContain("assumed");
    expect(rows.find(([l]) => l === "Total amount to be paid")?.[1]).toBe("₹83,736");
    expect(rows.find(([l]) => l === "Annual percentage rate")?.[1]).toBe("25.07%");
  });
});
