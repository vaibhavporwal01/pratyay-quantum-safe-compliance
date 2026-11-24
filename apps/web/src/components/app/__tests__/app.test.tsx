import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/ui";
import { MarkedText } from "../RuleParts";
import { ErrorState } from "../States";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));

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
