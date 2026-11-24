import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Cell styles seen on the December tables:
 * - mono: IDs, amounts, times (Mono, ink-2)
 * - text: secondary text (Body, ink-2)
 * - primary: the row's subject, e.g. borrower name (Body, ink)
 * - node: anything else, e.g. a Status
 */
export type CellKind = "mono" | "text" | "primary" | "node";

export type Column<Row> = {
  key: string;
  header: string;
  /** Fixed width in px, as in Figma. Omit for the last, flexible column. */
  width?: number;
  kind?: CellKind;
  render: (row: Row) => ReactNode;
};

const cellKinds: Record<CellKind, string> = {
  mono: "type-mono text-ink-2",
  text: "type-body text-ink-2",
  primary: "type-body text-ink",
  node: "",
};

export function Table<Row>({
  columns,
  rows,
  rowKey,
  caption,
  footer,
  className,
}: {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  /** Read by screen readers; hidden visually because the Card head names the table. */
  caption: string;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <table className="w-full table-fixed border-collapse text-left">
        <caption className="sr-only">{caption}</caption>
        <colgroup>
          {columns.map((c) => (
            // 16px gap between columns, as in Figma, sits inside each fixed width.
            <col key={c.key} style={c.width ? { width: c.width + 16 } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr className="border-b border-rule">
            {columns.map((c) => (
              <th key={c.key} scope="col" className="py-3 pr-4 align-top type-label font-medium text-muted">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-rule-2">
              {columns.map((c) => (
                <td key={c.key} className={cn("py-[13px] pr-4 align-middle", cellKinds[c.kind ?? "text"])}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {footer ? <div className="flex items-center gap-3 pt-3.5">{footer}</div> : null}
    </div>
  );
}

/** "Showing 9 of 42" style footer text. */
export function TableCount({ children }: { children: ReactNode }) {
  return <p className="min-w-0 flex-1 type-caption text-muted">{children}</p>;
}
