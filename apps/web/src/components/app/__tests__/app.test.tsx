import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/ui";
import { SourceCards } from "@/app/maker/sources/SourcesView";
import type { SourceDoc } from "@/lib/api/rules";
import { canAccess } from "@/lib/roles";
import { Forbidden } from "../RoleShell";
import { MarkedText, SectionHeading } from "../RuleParts";
import { ErrorState } from "../States";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
}));

afterEach(cleanup);

describe("AppShell on narrow screens", () => {
  it("opens and closes the menu with the tabs and the user", () => {
    render(
      <AppShell
        breadcrumb={["Lender A", "Rules"]}
        user={{ name: "Neha Verma", role: "Compliance maker" }}
        tabs={[{ href: "/maker/sources", number: "01", label: "Sources" }]}
        activeHref="/maker/sources"
      >
        <p>Body</p>
      </AppShell>,
    );
    const button = screen.getByRole("button", { name: "Open menu" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(button);
    expect(screen.getByRole("navigation", { name: "Sections, menu" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Close menu" }).getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Close menu" }));
    expect(screen.queryByRole("navigation", { name: "Sections, menu" })).toBeNull();
  });
});

describe("MarkedText", () => {
  it("marks each extracted value and keeps the text whole", () => {
    const text = "subject to a limit of maximum 50 per cent of income";
    const start = text.indexOf("50 per cent");
    const { container } = render(
      <p>
        <MarkedText text={text} values={[{ kind: "percent", value: "50", text: "50 per cent", start, end: start + 11, unit: "%" }]} />
      </p>,
    );
    expect(container.textContent).toBe(text);
    expect(container.querySelector("mark")?.textContent).toBe("50 per cent");
  });
});

describe("ErrorState", () => {
  it("lists problems and offers a retry", () => {
    const retry = vi.fn();
    render(<ErrorState message="Not valid" problems={["max_percent: 45 is not in the quoted text"]} onRetry={retry} />);
    expect(screen.getByRole("alert").textContent).toContain("45 is not in the quoted text");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });
});

describe("DevRoleSwitcher", () => {
  it("is hidden unless NEXT_PUBLIC_APP_ENV is development", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_APP_ENV", "production");
    const { DevRoleSwitcher } = await import("../DevRoleSwitcher");
    const { container } = render(<DevRoleSwitcher current="maker" />);
    expect(container.innerHTML).toBe("");
    vi.unstubAllEnvs();
  });

  it("sets the cookie when a role is picked", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_APP_ENV", "development");
    const { DevRoleSwitcher } = await import("../DevRoleSwitcher");
    render(<DevRoleSwitcher current="maker" />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "checker" } });
    expect(document.cookie).toContain("pratyay_dev_role=checker");
    vi.unstubAllEnvs();
  });
});

describe("page role guard", () => {
  it("matches the API: maker pages for makers, checker pages for checkers", () => {
    expect(canAccess("maker", "maker")).toBe(true);
    expect(canAccess("checker", "maker")).toBe(false);
    expect(canAccess("maker", "checker")).toBe(false);
    expect(canAccess("checker", "checker")).toBe(true);
    expect(canAccess("auditor", "reader")).toBe(true);
    expect(canAccess("officer", "reader")).toBe(false);
    expect(canAccess(undefined, "maker")).toBe(false);
  });

  it("says who the page is for", () => {
    render(<Forbidden role="maker" area="checker" />);
    expect(screen.getByRole("alert").textContent).toContain("This page is for the compliance checker");
    expect(screen.getByRole("alert").textContent).toContain("signed in as compliance maker");
  });
});

describe("SourceCards", () => {
  it("stacks title, reference, counts, hash and status", () => {
    const doc: SourceDoc = {
      id: "d1", title: "NBFC Credit Facilities Directions, 2025", short_code: "CF",
      ref_no: "RBI/DOR/2025-26/347", issued_on: "2025-11-28", url: null,
      sha3_256: "abcdef0123456789", pages: 54, uploaded_at: "2026-11-01T10:00:00Z",
      paragraphs: 120, labels: { requirement: 120 }, needs_review: 0, rules: {},
    };
    render(<SourceCards docs={[doc]} />);
    const card = screen.getByRole("listitem");
    expect(card.textContent).toContain("RBI/DOR/2025-26/347");
    expect(card.textContent).toContain("54 pages · 120 paragraphs");
    expect(card.textContent).toContain("SHA3-256 abcdef01…6789");
    expect(card.textContent).toContain("Classified");
  });
});

describe("SectionHeading", () => {
  it("shows the section as a heading, not a quote", () => {
    render(<SectionHeading section="H. Conduct towards Microfinance borrowers" />);
    expect(screen.getByRole("heading", { name: "H. Conduct towards Microfinance borrowers" })).toBeTruthy();
    expect(document.querySelector("blockquote")).toBeNull();
  });
});
