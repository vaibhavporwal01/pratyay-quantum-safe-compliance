import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { barcodeWidths, DecisionReceipt } from "../DecisionReceipt";
import { Stamp } from "../Stamp";

afterEach(cleanup);

describe("barcodeWidths", () => {
  it("is deterministic, 1 to 3 px wide", () => {
    const a = barcodeWidths("7f3a91c2…e04b5d18");
    expect(a).toEqual(barcodeWidths("7f3a91c2…e04b5d18"));
    expect(a).toHaveLength(46);
    expect(a.every((w) => w >= 1 && w <= 3)).toBe(true);
    expect(barcodeWidths("2b8d4a10")).not.toEqual(a);
  });

  it("copes with a hash that has no hex characters", () => {
    expect(barcodeWidths("…")).toHaveLength(46);
  });
});

describe("Stamp", () => {
  it("has an accessible name from its three lines", () => {
    render(<Stamp bottom="12 Oct 2026" />);
    expect(screen.getByRole("img", { name: "Signed, ML-DSA-65, 12 Oct 2026" })).toBeTruthy();
  });
});

describe("DecisionReceipt", () => {
  const props = {
    name: "Rekha K.",
    applicationId: "APP-2026-0142",
    lender: "Lender A",
    decidedAt: "12 Oct 2026, 11:42 IST",
    outcome: "Approve with modified amount",
    lines: [
      { label: "Requested", value: "₹80,000", tone: "fail" as const },
      { label: "Offered", value: "₹66,000", tone: "pass" as const },
      { label: "APR", value: "25.07%", tone: "total" as const },
    ],
    checks: [{ label: "Rules", value: "10 pass · 1 flagged · 1 pending" }],
    seal: { hash: "7f3a91c2…e04b5d18", prev: "2b8d4a10…77fe03c9", signature: "ML-DSA-65 signature · 3,309 B" },
  };

  it("renders every line, the outcome and the seal", () => {
    render(<DecisionReceipt {...props} stampDate="12 Oct 2026" />);
    expect(screen.getByRole("article", { name: "Decision receipt for Rekha K., APP-2026-0142" })).toBeTruthy();
    for (const l of [...props.lines, ...props.checks]) {
      expect(screen.getByText(l.label)).toBeTruthy();
      expect(screen.getByText(l.value)).toBeTruthy();
    }
    expect(screen.getByText("Approve with modified amount")).toBeTruthy();
    expect(screen.getByText(/7f3a91c2…e04b5d18/)).toBeTruthy();
    expect(screen.getByRole("img", { name: /12 Oct 2026/ })).toBeTruthy();
  });

  it("colours values by tone", () => {
    render(<DecisionReceipt {...props} />);
    expect(screen.getByText("₹80,000").className).toContain("text-fail");
    expect(screen.getByText("₹66,000").className).toContain("text-pass");
    expect(screen.getByText("25.07%").className).toContain("type-mono-medium");
  });

  it("omits the stamp when the receipt is not signed", () => {
    render(<DecisionReceipt {...props} />);
    expect(screen.queryByRole("img", { name: /Signed/ })).toBeNull();
  });
});
