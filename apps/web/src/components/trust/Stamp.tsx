import Image from "next/image";
import { cn } from "@/lib/cn";

/** Round signing stamp. Rings are the Figma vectors in /public/figma. */
export function Stamp({
  top = "Signed",
  middle = "ML-DSA-65",
  bottom,
  className,
}: {
  top?: string;
  middle?: string;
  /** Usually the signing date, e.g. "12 Oct 2026". */
  bottom: string;
  className?: string;
}) {
  return (
    <div
      role="img"
      aria-label={`${top}, ${middle}, ${bottom}`}
      className={cn(
        "relative flex size-28 shrink-0 flex-col items-center justify-center gap-[3px] overflow-hidden text-stamp opacity-[0.92]",
        className,
      )}
    >
      <Image
        src="/figma/stamp-ring-outer.svg"
        alt=""
        width={112}
        height={112}
        unoptimized
        className="absolute top-0 left-0"
      />
      <Image
        src="/figma/stamp-ring-inner.svg"
        alt=""
        width={98}
        height={98}
        unoptimized
        className="absolute top-[7px] left-[7px]"
      />
      <span aria-hidden className="relative type-label whitespace-nowrap">
        {top}
      </span>
      <span aria-hidden className="relative type-mono-medium whitespace-nowrap">
        {middle}
      </span>
      <span aria-hidden className="relative h-px w-9 border-t border-stamp" />
      <span aria-hidden className="relative type-label whitespace-nowrap">
        {bottom}
      </span>
    </div>
  );
}
