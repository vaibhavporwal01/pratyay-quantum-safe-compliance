import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..", "..", "..");

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return name === "__tests__" ? [] : files(p);
    return /\.(tsx?|css)$/.test(name) ? [p] : [];
  });
}

describe("UI copy rules", () => {
  const sources = files(SRC).map((p) => [p, readFileSync(p, "utf8")] as const);

  it("never uses the word demo", () => {
    const hits = sources.filter(([, text]) => /\bdemo\b/i.test(text)).map(([p]) => p);
    expect(hits).toEqual([]);
  });

  it("never uses an em dash", () => {
    const hits = sources.filter(([, text]) => text.includes("—")).map(([p]) => p);
    expect(hits).toEqual([]);
  });

  it("uses no raw hex colours outside globals.css and the style guide swatches", () => {
    const hits = sources
      .filter(([p]) => !p.endsWith("globals.css") && !p.endsWith(join("styleguide", "page.tsx")))
      .filter(([, text]) => /#[0-9a-fA-F]{6}\b/.test(text))
      .map(([p]) => p);
    expect(hits).toEqual([]);
  });
});
