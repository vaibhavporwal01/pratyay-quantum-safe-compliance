import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DecisionReceipt, ReceiptLine, Stamp } from "@/components/trust";
import {
  AppShell,
  Avatar,
  Button,
  Card,
  Field,
  Figure,
  Figures,
  Icon,
  ICON_NAMES,
  LedgerRow,
  Logo,
  NavTab,
  PageHead,
  Status,
  STATUS_KINDS,
  Table,
  TableCount,
  Tag,
  type Column,
  type TagTone,
} from "@/components/ui";

export const metadata: Metadata = {
  title: "Style guide · Pratyay",
  robots: { index: false, follow: false },
};

const COLOURS = [
  ["paper", "#F4F1EA"],
  ["paper-2", "#FBF9F3"],
  ["white", "#FFFFFF"],
  ["ink", "#1A1814"],
  ["ink-2", "#5F584B"],
  ["muted", "#736C5C"],
  ["rule", "#CFC8B8"],
  ["rule-2", "#E3DDCF"],
  ["stamp", "#1F3A5F"],
  ["stamp-bg", "#E6EBF2"],
  ["pass", "#2E6B3F"],
  ["pass-bg", "#E4EBDF"],
  ["fail", "#A33A2A"],
  ["fail-bg", "#F3E1DC"],
  ["refer", "#8A5A00"],
  ["refer-bg", "#F2E6CC"],
] as const;

const TYPE_RAMP: Array<[string, string, string]> = [
  ["Display", "type-display", "Rekha asked for ₹80,000."],
  ["Title/XL", "type-title-xl", "We offered ₹66,000."],
  ["Title/L", "type-title-l", "Repayments stay within 50% of income"],
  ["Title/M", "type-title-m", "Key Facts Statement"],
  ["Title/S", "type-title-s", "Rules, in order of the journey"],
  ["Numeral/L", "type-numeral-l", "₹1,54,000"],
  ["Numeral/M", "type-numeral-m", "49.95%"],
  ["Body/L", "type-body-l", "Every loan decision, with the rule that made it."],
  ["Body", "type-body", "At ₹80,000 the EMI would be ₹4,230, taking repayments to 53.3% of income."],
  ["Body/Medium", "type-body-medium", "Repayments within 50% of household income"],
  ["Small", "type-small", "Lender A · 12 Oct 2026, 11:42"],
  ["Small/Medium", "type-small-medium", "CF Directions, para 55"],
  ["Caption", "type-caption", "Sample data. Not affiliated with RBI, NPCI or any lender."],
  ["Label", "type-label", "§ 03 · Decision · APP-2026-0142"],
  ["Mono", "type-mono whitespace-pre", "SHA3-256  7f3a91c2…e04b5d18"],
  ["Mono/Medium", "type-mono-medium whitespace-pre", "MF-02  v1"],
  ["Button", "type-button", "Issue KFS"],
];

const TAG_TONES: TagTone[] = ["neutral", "stamp", "pass", "fail", "refer", "ink"];

const TABS = [
  { href: "#colour", number: "01", label: "Colour" },
  { href: "#type", number: "02", label: "Type" },
  { href: "#icons", number: "03", label: "Icons" },
  { href: "#components", number: "04", label: "Components" },
  { href: "#patterns", number: "05", label: "Patterns" },
  { href: "#trust", number: "06", label: "Trust" },
] as const;

type Application = {
  id: string;
  borrower: string;
  amount: string;
  stage: string;
  rules: string;
  updated: string;
  status: "pass" | "fail" | "flagged" | "referred" | "pending";
};

const APPLICATIONS: Application[] = [
  {
    id: "APP-2026-0224",
    borrower: "Farida B.",
    amount: "₹60,000",
    stage: "Onboarding",
    rules: "waiting for bank consent",
    updated: "9 Nov, 10:41",
    status: "pending",
  },
  {
    id: "APP-2026-0221",
    borrower: "Kavita R.",
    amount: "₹35,000",
    stage: "Assessment",
    rules: "MF-03 expenses missing",
    updated: "9 Nov, 10:12",
    status: "flagged",
  },
  {
    id: "APP-2026-0219",
    borrower: "Sunita D.",
    amount: "₹50,000",
    stage: "With checker",
    rules: "BL-03 flagged",
    updated: "9 Nov, 09:58",
    status: "referred",
  },
  {
    id: "APP-2026-0216",
    borrower: "Meena P.",
    amount: "₹40,000",
    stage: "Decided",
    rules: "GR-03 overdue ₹6,200",
    updated: "9 Nov, 09:34",
    status: "fail",
  },
  {
    id: "APP-2026-0142",
    borrower: "Rekha K.",
    amount: "₹66,000",
    stage: "Decided",
    rules: "cut to fit MF-02",
    updated: "12 Oct, 11:42",
    status: "pass",
  },
];

const COLUMNS: Column<Application>[] = [
  { key: "id", header: "ID", width: 130, kind: "mono", render: (r) => r.id },
  { key: "borrower", header: "Borrower", width: 170, kind: "primary", render: (r) => r.borrower },
  { key: "amount", header: "Amount", width: 110, kind: "mono", render: (r) => r.amount },
  { key: "stage", header: "Stage", width: 150, render: (r) => r.stage },
  { key: "rules", header: "Rules", width: 230, render: (r) => r.rules },
  { key: "updated", header: "Updated", width: 150, kind: "mono", render: (r) => r.updated },
  { key: "status", header: "Status", kind: "node", render: (r) => <Status status={r.status} /> },
];

function SectionHead({ id, number, title, note }: { id: string; number: string; title: string; note: string }) {
  return (
    <div className="flex items-baseline gap-4 border-b-2 border-ink pb-3">
      <span className="type-label text-muted">{number}</span>
      <h2 id={id} className="type-title-l text-ink">
        {title}
      </h2>
      <p className="type-small text-ink-2">{note}</p>
    </div>
  );
}

type SectionHref = (typeof TABS)[number]["href"];

/** Number and title come from TABS, so the sections always match the tabs. */
function Section({ href, note, children }: { href: SectionHref; note: string; children: ReactNode }) {
  const tab = TABS.find((t) => t.href === href)!;
  const anchor = href.slice(1);
  const headingId = `${anchor}-title`;
  return (
    <section aria-labelledby={headingId} className="flex scroll-mt-6 flex-col gap-7" id={anchor}>
      <SectionHead id={headingId} number={tab.number} title={tab.label} note={note} />
      {children}
    </section>
  );
}

/** A labelled white panel, like the component frames on the Foundations page. */
function Specimen({ label, children, bare = false }: { label: string; children: ReactNode; bare?: boolean }) {
  return (
    <div className="flex flex-col gap-2.5">
      <p className="type-label text-muted">{label}</p>
      <div className={bare ? "" : "bg-white p-5"}>{children}</div>
    </div>
  );
}

export default function StyleguidePage() {
  return (
    <AppShell
      breadcrumb={["Pratyay", "Style guide"]}
      user={{ name: "Anita Sharma", role: "Credit officer" }}
      tabs={TABS}
      activeHref="#colour"
      searchAction="/styleguide"
    >
      <div className="flex flex-col gap-16">
        <div className="flex max-w-[860px] flex-col gap-3">
          <p className="type-label text-muted">Pratyay · Ledger system · v2</p>
          <h1 className="type-display text-ink">Foundations</h1>
          <p className="type-body-l text-ink-2">
            Ink on paper. Every number carries its source, every decision gets a receipt, every record gets a
            stamp. Each block below matches a frame on the Figma page &quot;0 Foundations&quot; so the two can be
            compared side by side.
          </p>
        </div>

        <Section href="#colour" note="Paper and ink, one blue for the stamp, three verdict colours. Nothing else.">
          <ul className="flex flex-wrap gap-x-4 gap-y-5">
            {COLOURS.map(([name, hex]) => (
              <li key={name} className="flex w-[172px] flex-col gap-1.5">
                <span
                  aria-hidden
                  className="h-14 w-full rounded-[2px] border border-rule-2"
                  style={{ background: `var(--${name})` }}
                />
                <span className="type-mono-medium text-ink">{name}</span>
                <span className="type-mono text-muted">{hex}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section href="#type" note="Newsreader for titles and numerals, IBM Plex Sans for reading, IBM Plex Mono for labels and codes.">
          <div className="flex flex-col">
            {TYPE_RAMP.map(([name, cls, sample]) => (
              <div key={name} className="flex items-center gap-6 overflow-hidden border-b border-rule-2 py-3">
                <span className="w-40 shrink-0 type-mono text-muted">{name}</span>
                <span className={`${cls} whitespace-nowrap text-ink`}>{sample}</span>
              </div>
            ))}
          </div>
        </Section>

        <Section href="#icons" note="Tabler, 1.75 stroke. Only icons used on the December screens.">
          <ul className="flex flex-wrap gap-x-7 gap-y-6">
            {ICON_NAMES.map((name) => (
              <li key={name} className="flex w-24 flex-col items-center gap-2 text-ink">
                <Icon name={name} size={24} />
                <span className="type-caption text-muted">{name}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section href="#components" note="Built once here, used as instances on every screen.">
          <div className="flex flex-wrap items-start gap-10">
            <Specimen label="Button · Primary, Secondary, Quiet × M 40, L 48">
              <div className="grid grid-cols-[auto_auto] items-center gap-x-4 gap-y-6">
                <Button icon={<Icon name="arrow-right" />}>Continue</Button>
                <Button size="l" icon={<Icon name="arrow-right" />}>
                  Continue
                </Button>
                <Button variant="secondary" icon={<Icon name="arrow-right" />}>
                  Continue
                </Button>
                <Button variant="secondary" size="l" icon={<Icon name="arrow-right" />}>
                  Continue
                </Button>
                <Button variant="quiet" icon={<Icon name="arrow-right" />}>
                  Continue
                </Button>
                <Button variant="quiet" size="l" icon={<Icon name="arrow-right" />}>
                  Continue
                </Button>
                <Button disabled>Disabled</Button>
                <Button variant="secondary" href="#components">
                  As a link
                </Button>
              </div>
            </Specimen>

            <Specimen label="Status mark">
              <ul className="flex flex-col gap-3">
                {STATUS_KINDS.map((s) => (
                  <li key={s}>
                    <Status status={s} />
                  </li>
                ))}
              </ul>
            </Specimen>

            <Specimen label="Tag">
              <ul className="flex flex-col items-start gap-3">
                {TAG_TONES.map((t) => (
                  <li key={t}>
                    <Tag tone={t}>Hard limit</Tag>
                  </li>
                ))}
              </ul>
            </Specimen>

            <div className="flex flex-col gap-6">
              <Specimen label="Logo">
                <div className="flex flex-col items-start gap-4">
                  <Logo />
                  <Logo tone="inverse" />
                </div>
              </Specimen>
              <Specimen label="Avatar" bare>
                <Avatar name="Anita Sharma" />
              </Specimen>
            </div>

            <Specimen label="Nav tab · numbered sections, no sidebar">
              <div className="flex gap-8">
                <NavTab href="#components" number="01" label="Overview" />
                <NavTab href="#components" number="01" label="Overview" active />
              </div>
            </Specimen>
          </div>

          <div className="flex flex-wrap items-start gap-10">
            <Specimen label="Field · numbered like a paper form">
              <div className="grid grid-cols-[repeat(4,300px)] gap-6">
                <Field label="1 · Work email" type="email" placeholder="name@lender-a.in" hint="Use the email your lender gave you." />
                <Field
                  label="1 · Work email"
                  type="email"
                  defaultValue="anita.sharma@lender-a.in"
                  hint="Use the email your lender gave you."
                />
                <Field
                  label="1 · Work email"
                  type="email"
                  defaultValue="anita.sharma@lender-a.in"
                  hint="Use the email your lender gave you."
                  showFocus
                />
                <Field
                  label="1 · Work email"
                  type="email"
                  defaultValue="anita.sharma@lender-a.in"
                  error="Use the email your lender gave you."
                />
              </div>
            </Specimen>

            <Specimen label="Figure" bare>
              <Figure label="Offered" value="₹66,000" note="Rounded down to ₹1,000" className="w-[220px] bg-white" />
            </Specimen>
          </div>

          <div className="flex flex-wrap items-start gap-10">
            <Specimen label="Ledger row · ID, rule, source, dotted leader, value, verdict" bare>
              <div className="w-[720px]">
                <LedgerRow
                  id="MF-02"
                  title="Repayments within 50% of income"
                  source="CF Directions, paras 55 and 56"
                  value="49.95% ≤ 50%"
                  status="pass"
                />
              </div>
            </Specimen>

            <Specimen label="Receipt line">
              <dl className="flex w-[312px] flex-col gap-3">
                <ReceiptLine label="Offered" value="₹66,000" />
                <ReceiptLine label="Offered" value="₹66,000" tone="muted" />
                <ReceiptLine label="Offered" value="₹66,000" tone="pass" />
                <ReceiptLine label="Offered" value="₹66,000" tone="fail" />
                <ReceiptLine label="Offered" value="₹66,000" tone="total" />
              </dl>
            </Specimen>
          </div>
        </Section>

        <Section href="#patterns" note="Page head, figures, cards and tables as they appear on the December screens.">
          <PageHead
            eyebrow="§ 01 · Overview · Monday 9 Nov 2026"
            title="Anita, three applications are waiting for you."
            subtitle="Every line opens a signed record. Figures are for Lender A."
            actions={
              <>
                <Button variant="secondary" icon={<Icon name="download" />}>
                  Export day sheet
                </Button>
                <Button icon={<Icon name="plus" />}>New application</Button>
              </>
            }
          />

          <Figures>
            <Figure label="This week" value="42" note="applications decided" />
            <Figure label="Approved as asked" value="27" note="all rules pass" />
            <Figure label="Approved, modified" value="8" note="amount cut to fit a rule" />
            <Figure label="Declined" value="5" note="each names its rule" />
            <Figure label="Referred" value="2" note="a rule asked for a person" />
          </Figures>

          <Card eyebrow="APP-2026-0142" title="Rules, in order of the journey" tag={<Tag tone="stamp">3 shown</Tag>}>
            <LedgerRow
              id="MF-02"
              title="Repayments within 50% of income"
              source="CF Directions, paras 55 and 56"
              value="49.95% ≤ 50%"
              status="pass"
            />
            <LedgerRow
              id="MF-03"
              title="Household expenses are missing from the income profile"
              value="missing"
              status="flagged"
            />
            <LedgerRow
              id="GR-03"
              title="Overdue with ₹6,200 outstanding"
              value="74 days"
              status="fail"
              className="border-b-0"
            />
          </Card>

          <Card eyebrow="Lender A" title="All applications" tag={<Tag>Sorted by last update</Tag>}>
            <Table
              caption="All applications for Lender A"
              columns={COLUMNS}
              rows={APPLICATIONS}
              rowKey={(r) => r.id}
              footer={
                <>
                  <TableCount>Showing 5 of 42</TableCount>
                  <Button variant="quiet">Previous</Button>
                  <Button variant="secondary">Next</Button>
                </>
              }
            />
          </Card>
        </Section>

        <Section href="#trust" note="Every decision gets a receipt, every record gets a stamp.">
          <div className="flex flex-wrap items-start gap-10">
            <Specimen label="Decision receipt · with stamp" bare>
              <DecisionReceipt
                name="Rekha K."
                applicationId="APP-2026-0142"
                lender="Lender A"
                decidedAt="12 Oct 2026, 11:42 IST"
                outcome="Approve with modified amount"
                lines={[
                  { label: "Requested", value: "₹80,000", tone: "fail" },
                  { label: "Offered", value: "₹66,000", tone: "pass" },
                  { label: "Interest", value: "2% a month, 24 months" },
                  { label: "Monthly EMI", value: "₹3,489" },
                  { label: "Repayments to income", value: "49.95% of 50%" },
                  { label: "Processing fee", value: "₹660" },
                  { label: "Paid to her account", value: "₹65,340" },
                  { label: "Total repayment", value: "₹83,736" },
                  { label: "APR", value: "25.07%", tone: "total" },
                ]}
                checks={[{ label: "Rules", value: "10 pass · 1 flagged · 1 pending" }]}
                seal={{
                  hash: "7f3a91c2…e04b5d18",
                  prev: "2b8d4a10…77fe03c9",
                  signature: "ML-DSA-65 signature · 3,309 B",
                }}
                stampDate="12 Oct 2026"
              />
            </Specimen>
            <Specimen label="Stamp" bare>
              <Stamp bottom="12 Oct 2026" />
            </Specimen>
          </div>
        </Section>
      </div>
    </AppShell>
  );
}
