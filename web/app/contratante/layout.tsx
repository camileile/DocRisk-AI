import type { Metadata } from "next";
import "./contractor.css";
import { ContractorShell } from "@/components/contractor-shell";
export const metadata: Metadata = {
  title: "Portal da contratante | DocRisk AI",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <ContractorShell>{children}</ContractorShell>;
}
