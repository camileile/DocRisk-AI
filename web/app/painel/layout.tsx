import type { Metadata } from "next";
import { WorkspaceShell } from "@/components/workspace-shell";
export const metadata: Metadata = {
  title: "Demonstração Trabalhista | DocRisk AI",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <WorkspaceShell>{children}</WorkspaceShell>;
}
