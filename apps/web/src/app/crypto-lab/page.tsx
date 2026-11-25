import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { CryptoLab } from "./CryptoLab";

export const metadata: Metadata = { title: "Crypto lab · Pratyay" };

export default function Page() {
  return (
    <RoleShell breadcrumb={["Crypto lab"]} area="cryptolab">
      <CryptoLab />
    </RoleShell>
  );
}
