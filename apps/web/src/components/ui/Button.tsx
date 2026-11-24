import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "quiet";
export type ButtonSize = "m" | "l";

const base =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-[4px] whitespace-nowrap type-button transition-colors disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-stamp text-white hover:bg-ink",
  secondary: "border border-ink text-ink hover:bg-paper-2",
  quiet: "text-stamp hover:underline underline-offset-2",
};

const sizes: Record<ButtonSize, Record<ButtonVariant, string>> = {
  m: { primary: "h-10 px-4", secondary: "h-10 px-4", quiet: "h-10" },
  l: { primary: "h-12 px-5", secondary: "h-12 px-5", quiet: "h-12" },
};

export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "m") {
  return cn(base, variants[variant], sizes[size][variant]);
}

type Common = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Trailing 16px icon, as in Figma. */
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
};

type AsButton = Common & Omit<ComponentPropsWithoutRef<"button">, keyof Common> & { href?: undefined };
type AsLink = Common & Omit<ComponentPropsWithoutRef<typeof Link>, keyof Common> & { href: string };

export function Button(props: AsButton | AsLink) {
  const { variant = "primary", size = "m", icon, children, className, ...rest } = props;
  const classes = cn(buttonClasses(variant, size), className);
  const content = (
    <>
      <span>{children}</span>
      {icon}
    </>
  );
  if (typeof rest.href === "string") {
    return (
      <Link {...(rest as Omit<AsLink, keyof Common>)} className={classes}>
        {content}
      </Link>
    );
  }
  const { type = "button", ...buttonRest } = rest as Omit<AsButton, keyof Common>;
  return (
    <button type={type} {...buttonRest} className={classes}>
      {content}
    </button>
  );
}
