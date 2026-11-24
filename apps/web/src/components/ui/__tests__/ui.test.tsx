import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Avatar, initials } from "../Avatar";
import { Button, buttonClasses } from "../Button";
import { Field } from "../Field";
import { formatRemaining } from "../IdleTimer";
import { NavTab } from "../NavTab";
import { Status, STATUS_KINDS } from "../Status";
import { Table } from "../Table";
import { Tag } from "../Tag";

afterEach(cleanup);

describe("Button", () => {
  it("uses the Figma sizes and fills per variant", () => {
    expect(buttonClasses("primary", "m")).toContain("h-10 px-4");
    expect(buttonClasses("primary", "l")).toContain("h-12 px-5");
    expect(buttonClasses("primary")).toContain("bg-stamp");
    expect(buttonClasses("secondary")).toContain("border-ink");
    expect(buttonClasses("quiet", "m")).not.toContain("px-");
  });

  it("renders a button by default and a link with href", () => {
    render(
      <>
        <Button>Continue</Button>
        <Button href="/next" variant="secondary">
          Next
        </Button>
      </>,
    );
    const button = screen.getByRole("button", { name: "Continue" });
    expect(button.getAttribute("type")).toBe("button");
    expect(screen.getByRole("link", { name: "Next" }).getAttribute("href")).toBe("/next");
  });
});

describe("Status", () => {
  it("shows a visible label for every status", () => {
    render(
      <ul>
        {STATUS_KINDS.map((s) => (
          <li key={s}>
            <Status status={s} />
          </li>
        ))}
      </ul>,
    );
    for (const label of ["Pass", "Fail", "Flagged", "Referred", "Contested", "Pending"]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("draws contested and pending boxes dashed", () => {
    const { container } = render(<Status status="pending" />);
    expect(container.innerHTML).toContain("border-dashed");
  });
});

describe("Tag", () => {
  it("maps tones to token classes", () => {
    render(<Tag tone="fail">Hard limit</Tag>);
    expect(screen.getByText("Hard limit").className).toContain("text-fail");
  });
});

describe("Field", () => {
  it("links the label and hint to the input", () => {
    render(<Field label="1 · Work email" hint="Use the email your lender gave you." />);
    const input = screen.getByLabelText("1 · Work email");
    const hint = screen.getByText("Use the email your lender gave you.");
    expect(input.getAttribute("aria-describedby")).toBe(hint.id);
    expect(input.getAttribute("aria-invalid")).toBeNull();
  });

  it("marks the input invalid and shows the error", () => {
    render(<Field label="1 · Work email" hint="Hint" error="Enter a work email." />);
    const input = screen.getByLabelText("1 · Work email");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    const error = screen.getByText("Enter a work email.");
    expect(input.getAttribute("aria-describedby")).toBe(error.id);
    expect(screen.queryByText("Hint")).toBeNull();
  });
});

describe("NavTab", () => {
  it("marks only the active tab as the current page", () => {
    render(
      <nav>
        <NavTab href="/a" number="01" label="Overview" active />
        <NavTab href="/b" number="02" label="Applications" />
      </nav>,
    );
    const links = screen.getAllByRole("link");
    expect(links[0].getAttribute("aria-current")).toBe("page");
    expect(links[1].getAttribute("aria-current")).toBeNull();
  });
});

describe("Avatar", () => {
  it("takes first and last initials", () => {
    expect(initials("Anita Sharma")).toBe("AS");
    expect(initials("Rekha")).toBe("R");
    expect(initials("  ")).toBe("");
    render(<Avatar name="Anita Sharma" />);
    expect(screen.getByRole("img", { name: "Anita Sharma" }).textContent).toBe("AS");
  });
});

describe("formatRemaining", () => {
  it("formats seconds as mm:ss", () => {
    expect(formatRemaining(872)).toBe("14:32");
    expect(formatRemaining(900)).toBe("15:00");
    expect(formatRemaining(5)).toBe("00:05");
    expect(formatRemaining(0)).toBe("00:00");
    expect(formatRemaining(-3)).toBe("00:00");
  });
});

describe("Table", () => {
  it("renders a semantic table with column headers and rows", () => {
    render(
      <Table
        caption="Applications"
        columns={[
          { key: "id", header: "ID", width: 130, kind: "mono", render: (r: { id: string }) => r.id },
          { key: "s", header: "Status", kind: "node", render: () => <Status status="pass" /> },
        ]}
        rows={[{ id: "APP-1" }, { id: "APP-2" }]}
        rowKey={(r) => r.id}
      />,
    );
    expect(screen.getByRole("table", { name: "Applications" })).toBeTruthy();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["ID", "Status"]);
    expect(screen.getAllByRole("row")).toHaveLength(3);
  });
});
