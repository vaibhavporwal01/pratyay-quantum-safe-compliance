import { describe, expect, it } from "vitest";
import { cleanParams } from "@/app/maker/builder/fields";
import { citation, docCode, rupees, ruleLines, shortDocName, shortHash } from "../api/rules";
import { activeTab, navForRole, roleHome } from "../roles";

const CF = "Reserve Bank of India (Non-Banking Financial Companies – Credit Facilities) Directions, 2025";

describe("rule display helpers", () => {
  it("shortens Direction titles", () => {
    expect(shortDocName(CF)).toBe("Credit Facilities Directions");
    expect(docCode("CF", CF)).toBe("CF");
    expect(docCode(null, CF)).toBe("Credit Facilities Directions");
    // Stored, not derived: a "Non-Banking ..." title never turns into "NCF".
    expect(citation({ source_doc_code: "RBC", source_doc_title: "NBFC Responsible Business Conduct Directions, 2025", source_para: "29(2)" })).toBe("RBC para 29(2)");
    expect(shortDocName("Some circular")).toBe("Some circular");
  });

  it("formats paise as Indian rupees and hashes as head and tail", () => {
    expect(rupees(30_000_000)).toBe("₹3,00,000");
    expect(shortHash("a1754500ffff3f0e")).toBe("a1754500…3f0e");
    expect(shortHash(null)).toBe("Not recorded");
  });

  it("writes the machine rule as lines", () => {
    const lines = ruleLines({
      code: "MF-01",
      template: "max_amount",
      params: { subject: "annual household income", max_paise: 30_000_000, scope: null },
      applies_to: "microfinance",
      source_doc_title: CF,
      source_doc_code: "CF",
      source_para: "51",
      effective_from: "2025-11-28",
    });
    expect(lines).toContainEqual(["max_paise", "30000000 (₹3,00,000)"]);
    expect(lines).toContainEqual(["anchor", "CF para 51"]);
    expect(lines.find(([k]) => k === "scope")).toBeUndefined();
  });
});

describe("builder params", () => {
  it("drops optional blanks and keeps required ones for the server to report", () => {
    expect(cleanParams("prohibited_charge", { charge: "", unless: "", scope: "  " })).toEqual({
      charge: "",
      unless: null,
      scope: null,
    });
    expect(cleanParams("max_ratio", { numerator: "a", denominator: "b", max_percent: "50", exclude: ["x", " "] })).toEqual({
      numerator: "a",
      denominator: "b",
      max_percent: "50",
      exclude: ["x"],
      scope: null,
    });
  });

  it("keeps only the tenor bounds that are set", () => {
    const out = cleanParams("min_days", {
      subject: "KFS",
      working_days: true,
      tiers: [{ min_days: 3, tenor_days_min: 7, tenor_days_below: null }],
    });
    expect(out.tiers).toEqual([{ min_days: 3, tenor_days_min: 7 }]);
  });
});

describe("navigation by role", () => {
  it("gives makers and checkers their own tabs", () => {
    expect(navForRole("maker").map((t) => t.label)).toEqual(["Sources", "Drafts", "Rule library"]);
    expect(navForRole("checker").map((t) => t.number)).toEqual(["01", "02", "03", "04", "05"]);
    expect(navForRole("officer").map((t) => t.label)).toEqual(["Overview", "Applications", "Decisions"]);
    expect(navForRole("borrower").map((t) => t.label)).toEqual(["Home", "Application", "Key facts", "Receipt"]);
    expect(navForRole("auditor").map((t) => t.label)).toEqual(["Ledger", "Verify", "Findings", "Crypto lab", "Rule library"]);
  });

  it("sends each role home", () => {
    expect(roleHome("maker")).toBe("/maker/sources");
    expect(roleHome("checker")).toBe("/checker");
    expect(roleHome("officer")).toBe("/officer");
    expect(roleHome("borrower")).toBe("/borrower");
    expect(roleHome("auditor")).toBe("/auditor");
    expect(roleHome("admin")).toBe("/admin");
  });

  it("marks the longest matching tab", () => {
    const tabs = navForRole("checker");
    expect(activeTab(tabs, "/checker/review/abc")).toBe("/checker/review");
    expect(activeTab(tabs, "/checker")).toBe("/checker");
    expect(activeTab(tabs, "/checker/decisions")).toBe("/checker/decisions");
    expect(activeTab(tabs, "/elsewhere")).toBe("");
  });
});
