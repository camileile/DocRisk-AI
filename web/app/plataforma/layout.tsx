import type { Metadata } from "next";
import { PlatformShell } from "@/components/admin-shell";
import "../administracao/admin.css";
export const metadata: Metadata = { title: "Administração Geral | DocRisk AI", robots: { index: false, follow: false } };
export default function Layout({ children }: { children: React.ReactNode }) { return <PlatformShell>{children}</PlatformShell>; }
