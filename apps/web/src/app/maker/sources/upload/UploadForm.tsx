"use client";

import { useRef, useState, type FormEvent } from "react";
import { ErrorState } from "@/components/app/States";
import { Button, Card, Field, PageHead, Status, Tag, type StatusKind } from "@/components/ui";
import { api, ApiFailure, failureMessage } from "@/lib/api/client";
import { shortHash, type IngestResult } from "@/lib/api/rules";

const MAX_BYTES = 20 * 1024 * 1024;

type Step = { title: string; detail: string; status: StatusKind; label?: string };

function steps(result: IngestResult | null, busy: boolean): Step[] {
  if (!result) {
    const waiting: StatusKind = "pending";
    const label = busy ? "Running" : "Waiting";
    return [
      { title: "Stored", detail: "SHA3-256 of the original", status: waiting, label },
      { title: "Text extracted", detail: "pages read", status: waiting, label },
      { title: "Paragraphs found", detail: "numbered paragraphs", status: waiting, label },
      { title: "Lines outside a paragraph", detail: "contents, headings, footnotes", status: waiting, label },
      { title: "Classifier", detail: "runs next", status: waiting, label },
    ];
  }
  const r = result.report;
  const outside = r.unmatched.length + r.removed.length;
  return [
    { title: result.duplicate ? "Already stored" : "Stored", detail: `SHA3-256 ${shortHash(result.sha3_256)}`, status: "pass" },
    { title: "Text extracted", detail: `${r.pages} pages`, status: "pass" },
    { title: "Paragraphs found", detail: `${r.paragraphs}`, status: r.paragraphs ? "pass" : "fail" },
    {
      title: "Lines outside a paragraph",
      detail: `${outside} · contents, headings, footnotes · listed for review`,
      status: outside ? "pending" : "pass",
    },
    {
      title: "Classifier",
      detail: result.classified ? "every paragraph labelled" : result.duplicate ? "labels kept from the stored copy" : "model not available; labels left empty",
      status: result.classified || result.duplicate ? "pass" : "pending",
    },
  ];
}

export function UploadForm() {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string>();
  const [title, setTitle] = useState("");
  const [titleError, setTitleError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<IngestResult | null>(null);

  function pick(f: File | undefined) {
    setResult(null);
    setError(undefined);
    if (!f) return;
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
      setFile(null);
      setFileError("Not a PDF. Choose the original PDF from rbi.org.in.");
    } else if (f.size > MAX_BYTES) {
      setFile(null);
      setFileError("Over 20 MB. Upload a smaller original.");
    } else {
      setFile(f);
      setFileError(undefined);
    }
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) setFileError("Choose a PDF first.");
    if (!title.trim()) setTitleError("Enter the document title.");
    if (!file || !title.trim()) return;
    const form = new FormData(e.currentTarget);
    form.set("file", file);
    for (const k of ["ref_no", "issued_on", "url"]) if (!form.get(k)) form.delete(k);
    setBusy(true);
    setError(undefined);
    try {
      setResult(await api.upload<IngestResult>("/rules/sources", form));
    } catch (err) {
      setError(err instanceof ApiFailure && err.status === 403 ? "Only a compliance maker can upload." : failureMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow="§ 01 · Rules · Upload"
        title="Upload an RBI circular or Direction."
        subtitle="Upload the original PDF from rbi.org.in. Pratyay stores it with its hash, then splits it into numbered paragraphs ready for the classifier."
        actions={<Button href="/maker/sources" variant="secondary">Cancel</Button>}
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <form onSubmit={submit} noValidate className="flex min-w-0 flex-1 flex-col gap-7">
          <Card eyebrow="Step 1 of 2" title="The document">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                pick(e.dataTransfer.files[0]);
              }}
              className="mt-3 flex flex-col items-center gap-2.5 border border-dashed border-rule bg-paper px-6 py-9 text-center"
            >
              <p className="type-body-medium text-ink">Drop the PDF here, or choose a file</p>
              <p className="type-small text-muted">PDF only · up to 20 MB · the original from rbi.org.in</p>
              <input
                ref={input}
                id="pdf"
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                onChange={(e) => pick(e.target.files?.[0])}
              />
              <Button variant="secondary" onClick={() => input.current?.click()}>
                Choose file
              </Button>
            </div>
            {file ? (
              <div className="flex flex-wrap items-center gap-3 pt-3.5 pb-1">
                <p className="min-w-0 flex-1 type-mono-medium break-all text-ink">{file.name}</p>
                <p className="type-mono text-muted">{Math.round(file.size / 1024)} KB</p>
                <Status status={result ? "pass" : "pending"} label={result ? "Pass" : "Ready"} />
              </div>
            ) : null}
            {fileError ? <p role="alert" className="pt-3 type-caption text-fail">{fileError}</p> : null}
          </Card>
          <Card eyebrow="Step 2 of 2" title="About the document">
            <div className="flex flex-col gap-4 pt-4">
              <Field
                label="Title"
                name="title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setTitleError(undefined);
                }}
                error={titleError}
                placeholder="Reserve Bank of India (Non-Banking Financial Companies – …) Directions, 2025"
              />
              <div className="flex flex-col gap-4 sm:flex-row">
                <Field label="RBI reference" name="ref_no" placeholder="RBI/DOR/2025-26/347" />
                <Field label="Issued on" name="issued_on" type="date" />
              </div>
              <Field
                label="Source page"
                name="url"
                type="url"
                placeholder="https://rbi.org.in/…"
                hint="Kept with the document so anyone can check the original."
              />
              <div>
                <Button type="submit" disabled={busy}>
                  {busy ? "Uploading" : "Upload and parse"}
                </Button>
              </div>
              {error ? <ErrorState title="Upload failed" message={error} /> : null}
            </div>
          </Card>
        </form>
        <div className="flex w-full flex-col gap-7 lg:w-[440px] lg:shrink-0">
          <Card
            eyebrow="While it runs"
            title="What happens next"
            tag={<Tag tone={result ? "pass" : "stamp"}>{result ? (result.duplicate ? "Stored copy" : "Parsed") : busy ? "Parsing" : "Waiting"}</Tag>}
          >
            <ul className="flex flex-col">
              {steps(result, busy).map((s) => (
                <li key={s.title} className="flex items-center gap-3 border-b border-rule-2 py-3">
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <p className="type-body-medium text-ink">{s.title}</p>
                    <p className="type-small text-ink-2">{s.detail}</p>
                  </div>
                  <Status status={s.status} label={s.label} />
                </li>
              ))}
            </ul>
            {result ? (
              <div className="flex flex-wrap gap-3 pt-4">
                <Button href={`/maker/sources/${result.doc_id}`}>Draft rules from it</Button>
                <Button href="/maker/sources" variant="secondary">All documents</Button>
              </div>
            ) : null}
          </Card>
          <Card eyebrow="If something is wrong" title="Upload checks">
            <dl className="flex flex-col">
              {[
                ["Not a PDF", "Rejected before anything is stored."],
                ["Over 20 MB", "Rejected; upload a smaller original."],
                ["Already uploaded", "Same hash found: opens the stored copy instead."],
              ].map(([t, d]) => (
                <div key={t} className="flex flex-col gap-0.5 border-b border-rule-2 py-2.5">
                  <dt className="type-body-medium text-ink">{t}</dt>
                  <dd className="type-small text-ink-2">{d}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      </div>
    </div>
  );
}
