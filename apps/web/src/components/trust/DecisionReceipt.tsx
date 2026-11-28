import Image from "next/image";
import { Status } from "@/components/ui/Status";
import { Tag } from "@/components/ui/Tag";
import { cn } from "@/lib/cn";
import { ReceiptLine, type ReceiptLineData } from "./ReceiptLine";
import { Stamp } from "./Stamp";

const BAR_COUNT = 46;

/** Bar widths (1 to 3 px) derived from the hash, so each receipt has its own barcode. */
export function barcodeWidths(hash: string, count = BAR_COUNT): number[] {
  const hex = hash.toLowerCase().replace(/[^0-9a-f]/g, "") || "0";
  return Array.from({ length: count }, (_, i) => (parseInt(hex[i % hex.length], 16) % 3) + 1);
}

function Perforation({ edge }: { edge: "top" | "bottom" }) {
  return (
    <div aria-hidden className="relative h-1.5 w-full shrink-0 overflow-hidden">
      <Image
        src={`/figma/perforation-${edge}.svg`}
        alt=""
        width={1600}
        height={6}
        unoptimized
        className="absolute top-0 left-0 h-1.5 w-[1600px] max-w-none"
      />
    </div>
  );
}

function Divider() {
  return <hr className="h-px w-full border-0 border-t border-dashed border-rule" />;
}

export type DecisionReceiptProps = {
  name: string;
  applicationId: string;
  lender: string;
  /** e.g. "12 Oct 2026, 11:42 IST" */
  decidedAt: string;
  /** Outcome tag, e.g. "Approve with modified amount". */
  outcome: string;
  lines: ReceiptLineData[];
  checks?: ReceiptLineData[];
  /**
   * The ledger seal. Omit until the record is signed: the receipt then says "Signature pending"
   * and shows no hash or barcode. Never pass placeholder hashes.
   */
  verificationStatus?: "verified" | "failed" | "pending";
  seal?: {
    /** Short form shown on the receipt, e.g. "7f3a91c2…e04b5d18". */
    hash: string;
    prev: string;
    /** e.g. "ML-DSA-65 signature · 3,309 B" */
    signature: string;
  };
  /** Text on the bottom of the stamp, usually the signing date. Omit for an unsigned receipt. */
  stampDate?: string;
  className?: string;
};

export function DecisionReceipt({
  name,
  applicationId,
  lender,
  decidedAt,
  outcome,
  lines,
  checks,
  verificationStatus = "pending",
  seal,
  stampDate,
  className,
}: DecisionReceiptProps) {
  return (
    <article
      aria-label={`Decision receipt for ${name}, ${applicationId}`}
      className={cn("receipt-shadow relative flex w-[360px] max-w-full flex-col", className)}
    >
      <Perforation edge="top" />
      <div className="flex flex-col gap-4 bg-white px-6 pt-[18px] pb-[22px]">
        <div className="flex flex-col gap-1 whitespace-nowrap">
          <p className="type-label text-muted">Decision receipt</p>
          <h3 className="type-title-m text-ink">{name}</h3>
          <p className="type-small text-ink-2">{applicationId}</p>
          <p className="type-small text-ink-2">{lender}</p>
          <p className="type-small text-ink-2">{decidedAt}</p>
        </div>
        <Tag tone="stamp" className="self-start">
          {outcome}
        </Tag>
        <Divider />
        <dl className="flex flex-col gap-2">
          {lines.map((l) => (
            <ReceiptLine key={l.label} {...l} />
          ))}
        </dl>
        {checks && checks.length > 0 ? (
          <>
            <Divider />
            <dl className="flex flex-col gap-2">
              {checks.map((l) => (
                <ReceiptLine key={l.label} {...l} />
              ))}
            </dl>
          </>
        ) : null}
        <Divider />
        {seal ? (
          <>
            <div className="flex flex-col gap-[3px] type-mono text-muted">
              <p className="whitespace-pre">{`SHA3-256  ${seal.hash}`}</p>
              <p className="whitespace-pre">{`Prev      ${seal.prev}`}</p>
              <p className="whitespace-nowrap">{seal.signature}</p>
            </div>
            <div aria-hidden className="flex h-[30px] gap-0.5">
              {barcodeWidths(seal.hash).map((w, i) => (
                <span key={i} className="h-full shrink-0 bg-ink" style={{ width: w }} />
              ))}
            </div>
          </>
        ) : (
          <div className="flex flex-col gap-1">
            {verificationStatus === "failed" ? (
              <Status status="fail" label="Verification failed" />
            ) : (
              <Status status="pending" label="Signature pending" />
            )}
            <p className="type-caption text-muted">
              {verificationStatus === "failed"
                ? "The ledger entry or its application binding did not pass verification. Do not rely on this receipt as verified."
                : "This decision has not yet been signed in the verification ledger."}
            </p>
          </div>
        )}
      </div>
      <Perforation edge="bottom" />
      {stampDate ? (
        <div className="absolute top-1 right-[10px] flex size-[133px] items-center justify-center">
          <Stamp bottom={stampDate} className="rotate-12" />
        </div>
      ) : null}
    </article>
  );
}
