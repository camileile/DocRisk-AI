import type { Metadata } from "next";
import Access from "@/components/access-page";

export const metadata: Metadata = {
  title: "Demonstração fictícia | DocRisk AI",
  description: "Ambiente ilustrativo de demonstração, com dados sintéticos e sem operações de escrita.",
  robots: { index: false, follow: false },
};

export default function Page() { return <Access />; }
