import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-24">
      <p className="type-label text-muted">Pratyay</p>
      <h1 className="type-title-xl mt-3 text-ink">
        Quantum-safe, intelligent compliance and risk assessment for digital lending.
      </h1>
      <p className="type-body-l mt-4 text-ink-2">
        Pages from the December design come next. The component library is on the{" "}
        <Link href="/styleguide" className="text-stamp underline underline-offset-2">
          style guide
        </Link>
        .
      </p>
    </main>
  );
}
