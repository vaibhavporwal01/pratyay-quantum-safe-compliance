import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ExampleLedger, ExampleReceipt, ExampleStory, resetWorkedExample, UNAVAILABLE } from "../WorkedExample";

const ratio = (pct: string, status: string) => ({
  rule_id: "r2", code: "MF-02", version: 1, title: "Repayments within 50%", stage: "origination", applies_to: "microfinance",
  status, message: "m", anchor: "CF para 55", para_text: "",
  values: { ratio_percent: pct, limit_percent: "50", repayments: "₹11,730", monthly_income: "₹22,000",
            existing_repayments: "₹7,500", e_max: "₹3,500", l_max: "₹66,198.74", formula: "f" },
  missing: [],
});
const kfs = { amount_paise: 6_600_000, emi_paise: 348_900, instalments: 24, apr_percent: "25.07", rate_year_percent: "24.00",
  fees: [{ name: "Processing fee", paise: 66_000 }], net_disbursal_paise: 6_534_000, total_payable_paise: 8_373_600 };
const BODY = {
  ref: "APP-2026-0142", purpose: "x", on_date: "2026-10-12",
  facts: { amount_paise: 8_000_000, tenor_months: 24, rate_bps_month: 200, household_income_annual_paise: 26_400_000,
           existing_monthly_repayments_paise: 750_000, product_name: "MFL" },
  asked: { outcome: "fail", results: [ratio("53.3", "fail")], rules_used: [{}, {}], offer: { amount_paise: 6_600_000, rounding: "r" }, kfs: null },
  at_offer: { outcome: "pass", results: [ratio("49.95", "pass")], rules_used: [], offer: null, kfs },
};

beforeEach(() => resetWorkedExample());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("worked example", () => {
  it("renders the engine's figures", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(BODY), { status: 200 })));
    render(<><ExampleReceipt /><ExampleStory /><ExampleLedger /></>);
    expect(await screen.findByText(/Rekha asked for ₹80,000/)).toBeTruthy();
    expect(screen.getAllByText(/53.3%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/25.07%/).length).toBeGreaterThan(0);
    expect(screen.getByText("₹3,500")).toBeTruthy();
  });

  it("shows a neutral message when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("down"); }));
    render(<><ExampleReceipt /><ExampleStory /></>);
    expect((await screen.findAllByText(UNAVAILABLE)).length).toBe(2);
    expect(screen.queryByText(/₹/)).toBeNull();
  });
});
