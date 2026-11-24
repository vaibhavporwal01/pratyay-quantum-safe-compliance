import { describe, expect, it } from "vitest";
import { appKind, appKindLabel, monthlyRate, resultSummary, resultValue, rulesUsed, toPaise, type RuleResult } from "../api/loans";
import { canAccess } from "../roles";

const base: Omit<RuleResult, "code" | "status" | "values"> = {
  rule_id: "r",
  version: 1,
  title: "t",
  stage: "origination",
  applies_to: "microfinance",
  message: "",
  anchor: "CF para 55",
  para_text: "",
  missing: [],
};

describe("loan helpers", () => {
  it("reads rupees typed by people as paise", () => {
    expect(toPaise("80,000")).toBe(8_000_000);
    expect(toPaise("₹ 66000")).toBe(6_600_000);
    expect(toPaise("0")).toBeNull();
    expect(toPaise("eighty")).toBeNull();
  });

  it("formats rates and results", () => {
    expect(monthlyRate(200)).toBe("2% a month");
    expect(monthlyRate(125)).toBe("1.25% a month");
    const fail = { ...base, code: "MF-02", status: "fail" as const, values: { ratio_percent: "53.3", limit_percent: "50" } };
    const pass = { ...base, code: "MF-02", status: "pass" as const, values: { ratio_percent: "49.95", limit_percent: "50" } };
    expect(resultValue(fail)).toBe("53.3% > 50%");
    expect(resultValue(pass)).toBe("49.95% ≤ 50%");
    const later = { ...base, code: "MF-05", status: "not_checked" as const, stage: "recovery" as const, values: {} };
    expect(resultSummary([fail, pass, later])).toBe("1 pass · 1 fail · 1 later stage");
  });

  it("names the rules a decision used", () => {
    expect(rulesUsed({ in_force: 8, checked: 5, versions: [], deciding: ["MF-02 v1"] })).toBe("8 rules · MF-02 v1 decided");
    expect(rulesUsed({ in_force: 8, checked: 5, versions: [], deciding: [] })).toBe("8 rules · all pass");
  });

  it("marks an application by its decision first", () => {
    expect(appKind({ status: "approved_modified", outcome: "fail" })).toBe("pass");
    expect(appKindLabel({ status: "recommended", outcome: "pass" })).toBe("With checker");
    expect(appKind({ status: "evaluated", outcome: "refer" })).toBe("referred");
  });

  it("guards each area by role", () => {
    expect(canAccess("borrower", "borrower")).toBe(true);
    expect(canAccess("officer", "borrower")).toBe(false);
    expect(canAccess("admin", "auditor")).toBe(true);
    expect(canAccess("officer", "auditor")).toBe(false);
    expect(canAccess("checker", "cryptolab")).toBe(true);
  });
});
