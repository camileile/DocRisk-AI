import type { Metadata } from "next";
import { AdminShell } from "@/components/admin-shell";
import "./admin.css";

export const metadata: Metadata = {
  title: "Auditoria administrativa | DocRisk AI",
  robots: { index: false, follow: false },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
