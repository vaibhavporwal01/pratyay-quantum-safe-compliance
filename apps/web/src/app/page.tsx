import type { ReactNode } from "react";
import { PublicHeader } from "@/components/public/PublicHeader";
import { ExampleLedger, ExampleReceipt, ExampleStory, MonoBox, RulesInForce, StepLines } from "@/components/public/WorkedExample";
import { Button } from "@/components/ui/Button";
import { Icon, type IconName } from "@/components/ui/icons";
import { Logo } from "@/components/ui/Logo";
import { Tag } from "@/components/ui/Tag";

/* Copy is from the Dec v1 landing frame (75:10780). Every worked-example figure comes from the
   engine (components/public/WorkedExample); the cited industry figures below carry their source. */

const HERO_STATS: ReadonlyArray<readonly [ReactNode, string]> = [
  [<RulesInForce key="rules" />, "rules in force from two RBI Directions"],
  ["3", "stages: origination, servicing, recovery"],
  ["3,309 B", "ML-DSA-65 signature"],
] as const;

const FACTS = [
  {
    figure: "9,445",
    text: "circulars repealed or withdrawn by the RBI on 28 Nov 2025. Rules move, so the registry keeps dates.",
    source: "Source · RBI, 28 Nov 2025",
  },
  {
    figure: "4",
    text: "NBFCs stopped from lending by the RBI on 17 Oct 2024, with household income checks among the concerns.",
    source: "Source · RBI press release, 17 Oct 2024",
  },
  {
    figure: "16.2%",
    text: "of the microfinance portfolio was at risk beyond 180 days on 30 Sep 2025. A cited industry figure, not engine output.",
    source: "Source · Business Standard, 28 Nov 2025",
  },
  {
    figure: "2",
    text: "NIST post-quantum standards in the trust layer: FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA).",
    source: "Source · NIST, 13 Aug 2024",
  },
];

const STEPS: Array<{ n: string; title: string; text: string; mono: readonly string[] | "check" | "offer" }> = [
  {
    n: "01",
    title: "Read the rule",
    text: "Policy-to-Code drafts a machine rule from the RBI text. A checker who did not write it approves it, with a start date.",
    mono: ["MF-02  v1  from 28 Nov 2025", "existing_emi + new_emi", "  <= 0.50 x household_income", "exclude: expected_income"],
  },
  {
    n: "02",
    title: "Check the application",
    text: "Each rule in force is checked at its stage: origination now, servicing and recovery later. A failed limit always names its paragraph.",
    mono: "check",
  },
  {
    n: "03",
    title: "Size the offer",
    text: "The engine finds the largest loan that keeps repayments within the rule's limit, rounded down to the product's step.",
    mono: "offer",
  },
  {
    n: "04",
    title: "Sign the record",
    text: "The decision will be chained with SHA3-256 and signed with ML-DSA-65, so anyone with the lender's public key can check it.",
    mono: ["hash   SHA3-256, 32 B", "sig    ML-DSA-65, 3,309 B", "now    Signature pending"],
  },
];

const TRUST: Array<{ icon: IconName; title: string; text: string; mono: string[] }> = [
  {
    icon: "fingerprint",
    title: "Hash chain",
    text: "Each decision record holds the hash of the one before it. Change one rupee and every later hash stops matching.",
    mono: ["SHA3-256", "32-byte digest per record"],
  },
  {
    icon: "shield-check",
    title: "Signatures",
    text: "Records are signed with ML-DSA-65, so approvals stay provable even against a future quantum computer.",
    mono: ["FIPS 204 · ML-DSA-65", "key 1,952 B · signature 3,309 B"],
  },
];

const ROLES: Array<{ icon: IconName; title: string; text: string; tag: string }> = [
  {
    icon: "user",
    title: "Credit officer",
    text: "Runs the checks, sees why an amount changed, issues the Key Facts Statement.",
    tag: "Email, password, authenticator",
  },
  {
    icon: "scale",
    title: "Compliance maker and checker",
    text: "Turns a new circular into a dated rule. The maker drafts, a different checker approves.",
    tag: "Email, password, authenticator",
  },
  {
    icon: "history",
    title: "Auditor",
    text: "Read-only. Picks an organisation and replays any decision with the rules of its day.",
    tag: "Email, authenticator, read-only",
  },
  {
    icon: "device-mobile",
    title: "Borrower",
    text: "Sees the KFS, the reason for the amount and the repayment plan. Can ask questions or apply by chatting.",
    tag: "Mobile number and OTP",
  },
];

const TEAM = [
  ["Vaibhav Porwal", "235/UCS/122"],
  ["Vishnukant Yadav", "235/UCS/127"],
  ["Lokesh Singh", "235/UCS/077"],
  ["Pulkit Kumar Talan", "235/UCS/098"],
] as const;

const STANDARDS = [
  "RBI (NBFC – Credit Facilities) Directions, 2025",
  "RBI (NBFC – Responsible Business Conduct) Directions, 2025",
  "NIST FIPS 203 and FIPS 204, 13 Aug 2024",
  "Digital Personal Data Protection Act, 2023",
];

function SectionHead({ id, number, title, intro }: { id: string; number: string; title: string; intro: string }) {
  return (
    <div className="flex flex-col gap-3 border-b-2 border-ink pb-5 lg:flex-row lg:items-end lg:gap-16">
      <div className="flex shrink-0 flex-col gap-2.5">
        <p className="type-label text-muted">{number}</p>
        <h2 id={id} className="type-title-l md:type-title-xl text-ink">
          {title}
        </h2>
      </div>
      <p className="flex-1 type-body md:type-body-l text-ink-2">{intro}</p>
    </div>
  );
}

/**
 * Classes for item i of n columns divided by hairlines:
 * one column on phones, two from 768px, all n from 1280px.
 */
function columnClass(i: number, n: number): string {
  const phone = i < n - 1 ? "border-b pb-6" : "";
  const phoneTop = i > 0 ? "pt-6" : "";
  const left = i % 2 === 0;
  const firstRow = i < 2;
  const tablet = [
    left ? "md:pr-7 md:border-l-0" : "md:border-l md:pl-7",
    firstRow && n > 2 ? "md:border-b md:pb-6" : "md:border-b-0 md:pb-0",
    firstRow ? "md:pt-0" : "md:pt-6",
  ];
  const desktop = [
    "xl:border-b-0 xl:py-1",
    i > 0 ? "xl:border-l xl:pl-7" : "xl:pl-0",
    i < n - 1 ? "xl:pr-7" : "xl:pr-0",
  ];
  return ["min-w-0 border-rule", phone, phoneTop, ...tablet, ...desktop].filter(Boolean).join(" ");
}

function Columns({ items }: { items: ReactNode[] }) {
  const n = items.length;
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 ${n === 4 ? "xl:grid-cols-4" : ""}`}>
      {items.map((item, i) => (
        <div key={i} className={columnClass(i, n)}>
          {item}
        </div>
      ))}
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-col bg-paper">
      <PublicHeader />

      <main id="main" className="flex flex-col">
        {/* Hero */}
        <section
          aria-labelledby="hero-title"
          className="flex flex-col gap-10 px-5 pt-10 pb-12 md:px-10 md:pt-16 md:pb-16 xl:flex-row xl:items-center xl:gap-16 xl:pt-[72px] xl:pb-20"
        >
          <div className="flex min-w-0 flex-1 flex-col gap-6">
            <p className="type-label text-muted">§ 00 · A compliance engine for digital lending</p>
            <h1 id="hero-title" className="type-title-xl md:type-display text-ink">
              Every loan decision, with the rule that made it.
            </h1>
            <p className="type-body md:type-body-l text-ink-2">
              Pratyay reads RBI Directions, turns each requirement into a rule with its paragraph, checks every
              microfinance application against the rules that apply, and signs the record with post-quantum keys so
              anyone can check it later.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
              <Button href="#how" size="l" className="w-full sm:w-auto" icon={<Icon name="arrow-right" />}>
                See how it decides
              </Button>
              <Button
                href="#example"
                variant="quiet"
                size="l"
                className="w-full max-sm:border max-sm:border-ink max-sm:px-5 max-sm:text-ink sm:w-auto"
                icon={<Icon name="arrow-right" />}
              >
                See the worked example
              </Button>
            </div>
            <dl className="grid grid-cols-3 border-t border-rule pt-4">
              {HERO_STATS.map(([figure, label], i) => (
                <div
                  key={label}
                  className={`flex flex-col-reverse gap-0.5 ${i > 0 ? "border-l border-rule pl-3 sm:pl-6" : ""} pr-3 sm:pr-6`}
                >
                  <dt className="type-small text-ink-2">{label}</dt>
                  <dd className="type-numeral-m whitespace-nowrap text-ink">{figure}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="flex flex-col gap-7 sm:flex-row sm:border sm:border-rule sm:bg-paper-2 sm:py-9 sm:pr-8 sm:pl-9 xl:shrink-0">
            <ExampleReceipt />
          </div>
        </section>

        {/* Facts */}
        <section aria-label="Why it matters" className="grid grid-cols-2 border-y border-ink xl:grid-cols-4">
          {FACTS.map((f, i) => (
            <div
              key={f.figure}
              className={[
                "flex min-w-0 flex-col gap-2 border-rule px-5 py-6 md:px-8 md:py-7",
                i % 2 === 0 ? "border-r md:pl-10" : "md:pr-10",
                i < 2 ? "border-b xl:border-b-0" : "",
                "xl:border-r xl:px-8 xl:last:border-r-0",
                i === 0 ? "xl:pl-10" : "",
                i === 3 ? "xl:pr-10" : "",
              ].join(" ")}
            >
              <p className="type-numeral-m md:type-numeral-l whitespace-nowrap text-ink">{f.figure}</p>
              <p className="type-small text-ink-2">{f.text}</p>
              <p className="type-caption text-muted">{f.source}</p>
            </div>
          ))}
        </section>

        {/* 01 How it decides */}
        <section
          id="how"
          aria-labelledby="how-title"
          className="flex scroll-mt-4 flex-col gap-9 px-5 pt-12 pb-12 md:px-10 md:pt-20 md:pb-[72px]"
        >
          <SectionHead
            id="how-title"
            number="§ 01"
            title="How it decides"
            intro="Four steps, in the same order every time. Each step leaves a line in the record, so the reason for an offer is never a guess."
          />
          <Columns
            items={STEPS.map((s) => (
              <div key={s.n} className="flex flex-col gap-3.5">
                <p className="type-numeral-l text-stamp">{s.n}</p>
                <h3 className="type-title-m text-ink">{s.title}</h3>
                <p className="type-small text-ink-2">{s.text}</p>
                {typeof s.mono === "string" ? <StepLines step={s.mono} /> : <MonoBox lines={s.mono} />}
              </div>
            ))}
          />
        </section>

        {/* 02 Worked example */}
        <section
          id="example"
          aria-labelledby="example-title"
          className="flex scroll-mt-4 flex-col gap-10 border-y border-rule bg-paper-2 px-5 py-12 md:px-10 md:py-[72px] xl:flex-row xl:items-start xl:gap-16"
        >
          <div className="flex flex-col gap-5 xl:w-[470px] xl:shrink-0">
            <p className="type-label text-muted">§ 02 · Worked example</p>
            <ExampleStory />
            <p className="flex items-start gap-2.5 rounded-[2px] border border-rule bg-white px-3.5 py-3 type-small text-ink-2">
              <Icon name="info-circle" size={16} className="mt-px shrink-0 text-ink-2" />
              A worked case from the project report. Names are fictional; every figure is computed.
            </p>
          </div>

          <div className="flex min-w-0 flex-1 flex-col border border-rule bg-white px-4 pt-2 pb-5 sm:px-7">
            <ExampleLedger />
          </div>
        </section>

        {/* 03 Built to be checked */}
        <section
          id="trust"
          aria-labelledby="trust-title"
          className="flex scroll-mt-4 flex-col gap-9 px-5 pt-12 pb-12 md:px-10 md:pt-20 md:pb-[72px]"
        >
          <SectionHead
            id="trust-title"
            number="§ 03"
            title="Built to be checked"
            intro="The trust layer is post-quantum from day one, because a loan record has to stay provable for the life of the loan and long after."
          />
          <Columns
            items={TRUST.map((t) => (
              <div key={t.title} className="flex flex-col gap-3">
                <Icon name={t.icon} size={24} className="text-stamp" />
                <h3 className="type-title-m text-ink">{t.title}</h3>
                <p className="type-small text-ink-2">{t.text}</p>
                <MonoBox lines={t.mono} />
              </div>
            ))}
          />
        </section>

        {/* 04 Who uses it */}
        <section
          id="roles"
          aria-labelledby="roles-title"
          className="flex scroll-mt-4 flex-col gap-9 border-t border-rule bg-paper-2 px-5 pt-12 pb-14 md:px-10 md:pt-[72px] md:pb-20"
        >
          <SectionHead
            id="roles-title"
            number="§ 04"
            title="Who uses it"
            intro="Four roles, four sign-ins. Nobody switches roles inside a session, and nobody approves their own work."
          />
          <Columns
            items={ROLES.map((r) => (
              <div key={r.title} className="flex flex-col items-start gap-3">
                <Icon name={r.icon} size={24} className="text-stamp" />
                <h3 className="type-title-m text-ink">{r.title}</h3>
                <p className="type-small text-ink-2">{r.text}</p>
                <Tag>{r.tag}</Tag>
              </div>
            ))}
          />
        </section>
      </main>

      {/* Colophon */}
      <footer id="team" className="flex scroll-mt-4 flex-col gap-10 bg-ink px-5 pt-14 pb-7 md:px-10">
        <div className="flex flex-col gap-10 xl:flex-row xl:gap-14">
          <div className="flex flex-col gap-4 xl:w-[440px] xl:shrink-0">
            <Logo tone="inverse" className="-ml-3 self-start" />
            <p className="type-body md:type-body-l text-paper">
              Intelligent and Secure Framework for Automated Regulatory Compliance and Risk Assessment in Digital
              Financial Systems
            </p>
            <p className="type-small text-rule">
              B.Tech CSE minor project · Department of CSE, University School of ICT, Gautam Buddha University
            </p>
          </div>
          <div className="flex flex-col gap-2.5 xl:flex-1">
            <h2 className="type-label text-rule">Team</h2>
            <ul className="flex flex-col gap-2.5">
              {TEAM.map(([name, roll]) => (
                <li key={roll} className="flex flex-wrap items-baseline gap-x-3">
                  <span className="type-body text-paper">{name}</span>
                  <span className="type-mono text-rule">{roll}</span>
                </li>
              ))}
            </ul>
            <h2 className="type-label text-rule">Supervisor</h2>
            <p className="type-body text-paper">Dr. Isha, Department of CSE</p>
          </div>
          <div className="flex flex-col gap-2.5 xl:flex-1">
            <h2 className="type-label text-rule">Rules and standards used</h2>
            <ul className="flex flex-col gap-2.5">
              {STANDARDS.map((s) => (
                <li key={s} className="type-small text-paper">
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="flex flex-col gap-2 border-t border-ink-2 pt-4 type-caption text-rule md:flex-row md:items-center md:justify-between">
          <p>
            Academic prototype. Not affiliated with RBI, NPCI, MFIN or any lender. All borrower and lender data is
            fictional.
          </p>
          <p className="type-mono whitespace-nowrap">Pratyay v1 · December 2026</p>
        </div>
      </footer>
    </div>
  );
}
