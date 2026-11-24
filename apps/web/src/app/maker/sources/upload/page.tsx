import type { Metadata } from "next";
import { RoleShell } from "@/components/app/RoleShell";
import { UploadForm } from "./UploadForm";

export const metadata: Metadata = { title: "Upload a circular · Pratyay" };

export default function UploadPage() {
  return (
    <RoleShell breadcrumb={["Rules", "Upload"]}>
      <UploadForm />
    </RoleShell>
  );
}
