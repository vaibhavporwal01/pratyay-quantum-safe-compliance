"use client";

import Link from "next/link";
import { DataCard, Empty } from "@/components/app/States";
import { Button, PageHead, Table, TableCount, Tag, type Column } from "@/components/ui";
import { formatDate, shortDocName, shortHash, type SourceDoc } from "@/lib/api/rules";
import { useApi } from "@/lib/useApi";

const columns: Column<SourceDoc>[] = [
  {
    key: "doc",
    header: "Document",
    width: 340,
    kind: "primary",
    render: (d) => (
      <Link href={`/maker/sources/${d.id}`} className="type-body-medium text-ink underline-offset-2 hover:underline">
        {shortDocName(d.title)}
      </Link>
    ),
  },
  { key: "ref", header: "RBI reference", width: 190, kind: "mono", render: (d) => d.ref_no ?? "Not recorded" },
  { key: "pages", header: "Pages", width: 60, render: (d) => d.pages ?? "Not recorded" },
  { key: "paras", header: "Paragraphs", width: 90, render: (d) => d.paragraphs },
  { key: "hash", header: "SHA3-256", width: 140, kind: "mono", render: (d) => shortHash(d.sha3_256) },
  { key: "uploaded", header: "Uploaded", width: 110, kind: "mono", render: (d) => formatDate(d.uploaded_at) },
  {
    key: "status",
    header: "Status",
    kind: "node",
    render: (d) =>
      d.paragraphs === 0 ? (
        <Tag tone="fail">No paragraphs</Tag>
      ) : d.labels.unlabelled === d.paragraphs ? (
        <Tag tone="stamp">Parsed</Tag>
      ) : (
        <Tag tone="pass">Classified</Tag>
      ),
  },
];

export function SourcesView() {
  const docs = useApi<SourceDoc[]>("/rules/sources");
  const n = docs.data?.length;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 01 · Rules${n !== undefined ? ` · ${n} source document${n === 1 ? "" : "s"}` : ""}`}
        title="Source documents"
        subtitle="Every regulation the rules come from, stored with its hash so anyone can prove which version a rule was drawn from."
        actions={<Button href="/maker/sources/upload">Upload a circular</Button>}
      />
      <DataCard
        eyebrow="Stored originals"
        title="Regulations on file"
        tag={<Tag tone="stamp">{`${n} document${n === 1 ? "" : "s"}`}</Tag>}
        state={docs}
        isEmpty={(d) => d.length === 0}
        empty={
          <Empty title="No documents yet" action={<Button href="/maker/sources/upload" variant="secondary">Upload a circular</Button>}>
            Upload an RBI Direction to start drafting rules from it.
          </Empty>
        }
      >
        {(data) => (
          <div className="overflow-x-auto">
            <Table
              className="min-w-[1080px]"
              caption="Regulations on file"
              columns={columns}
              rows={data}
              rowKey={(d) => d.id}
              footer={<TableCount>Uploading the same file again returns the stored copy; the hash is unique. Open a document to draft rules from it.</TableCount>}
            />
          </div>
        )}
      </DataCard>
    </div>
  );
}
