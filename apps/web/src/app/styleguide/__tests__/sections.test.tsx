import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import StyleguidePage from "../page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

afterEach(cleanup);

describe("/styleguide sections", () => {
  it("numbers each section the same as its tab", () => {
    render(<StyleguidePage />);
    const tabs = within(screen.getByRole("navigation", { name: "Sections" })).getAllByRole("link");
    expect(tabs).toHaveLength(6);
    for (const tab of tabs) {
      const anchor = tab.getAttribute("href")!.slice(1);
      const section = document.getElementById(anchor);
      expect(section, `section #${anchor}`).not.toBeNull();
      const [number, label] = Array.from(tab.querySelectorAll("span")).map((s) => s.textContent);
      const head = section!.firstElementChild!;
      expect(head.querySelector("span")!.textContent).toBe(number);
      expect(head.querySelector("h2")!.textContent).toBe(label);
    }
  });
});
