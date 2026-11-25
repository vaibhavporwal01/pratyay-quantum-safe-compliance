"use client";

import { DataCard, Empty } from "@/components/app/States";
import { Card, PageHead, Status, Table, Tag, type Column } from "@/components/ui";
import type { Role } from "@/lib/api/auth";
import { formatDate } from "@/lib/api/rules";
import { ROLE_LABEL } from "@/lib/roles";
import { useApi } from "@/lib/useApi";

type StaffUser = { id: string; name: string; email: string; role: Role; active: boolean; created_at: string };

const CAN: Record<Role, string> = {
  borrower: "apply, read key facts and the receipt",
  officer: "submit applications, recommend",
  maker: "upload circulars, draft rules",
  checker: "decide loans, approve rules",
  auditor: "read, replay and verify only",
  admin: "see people and keys, not loans",
};

const columns: Column<StaffUser>[] = [
  { key: "name", header: "Name", width: 150, kind: "primary", render: (u) => u.name },
  { key: "role", header: "Role", width: 160, render: (u) => ROLE_LABEL[u.role] },
  { key: "can", header: "Can", width: 250, render: (u) => CAN[u.role] },
  { key: "email", header: "Email", width: 220, kind: "mono", render: (u) => u.email },
  { key: "since", header: "Since", width: 110, kind: "mono", render: (u) => formatDate(u.created_at) },
  { key: "active", header: "Active", kind: "node", render: (u) => <Status status={u.active ? "pass" : "pending"} label={u.active ? "Active" : "Inactive"} /> },
];

export function UsersView() {
  const users = useApi<StaffUser[]>("/admin/users");
  const active = users.data?.filter((u) => u.active).length ?? 0;
  return (
    <div className="flex flex-col gap-7">
      <PageHead
        eyebrow={`§ 01 · Admin${users.data ? ` · ${users.data.length} accounts` : ""}`}
        title="Who can do what at Lender A."
        subtitle="Read only. Accounts, invitations and sign-in arrive with the identity module."
      />
      <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
        <DataCard
          className="min-w-0 flex-1"
          eyebrow="Lender A"
          title="People and roles"
          tag={<Tag tone="pass">{`${active} active`}</Tag>}
          state={users}
          isEmpty={(d) => d.length === 0}
          empty={<Empty title="No accounts">Run the seed to create one account per role.</Empty>}
        >
          {(rows) => (
            <div className="overflow-x-auto">
              <Table className="min-w-[1000px]" caption="People and roles" columns={columns} rows={rows} rowKey={(u) => u.id} />
            </div>
          )}
        </DataCard>
        <Card eyebrow="Enforced in the database" title="Separation of duties" className="min-w-0 lg:w-[400px] lg:shrink-0">
          <ul className="flex flex-col">
            {[
              "The officer who recommends a loan cannot decide it.",
              "The maker who drafts a rule cannot approve it.",
              "Each role sees only its own pages; the API refuses the rest.",
              "Admins see people and keys, not loans.",
            ].map((t) => (
              <li key={t} className="border-b border-rule-2 py-3 type-small text-ink">
                {t}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
