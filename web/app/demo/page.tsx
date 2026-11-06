import type { Metadata } from "next";
import Access from "@/components/access-page";

export const metadata: Metadata = {
  title: "Demonstração fictícia | DocRisk AI",
  description: "Demonstração com dados sintéticos e conexão opcional à API local.",
  robots: { index: false, follow: false },
};

export default function Page() { return <Access />; }
