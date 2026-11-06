import type { Metadata } from "next";
import "./globals.css";
import "./workspace.css";
import "./api-integration.css";
import "./document-viewer.css";
import { DemoProvider } from "@/components/demo-provider";
import { SessionToolbar } from "@/components/session-toolbar";
export const metadata: Metadata = {
  title: "DocRisk AI | Inteligência documental, decisões mais claras",
  description:
    "Conheça o DocRisk AI: inteligência documental modular para organizar documentos, conectar evidências e apoiar a revisão humana.",
  icons: { icon: "/brand/favicon.svg", apple: "/brand/apple-touch-icon.png" },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <DemoProvider><SessionToolbar />{children}</DemoProvider>
      </body>
    </html>
  );
}
