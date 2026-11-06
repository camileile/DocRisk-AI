"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowUpRight, FileCheck2, FlaskConical, LogOut } from "lucide-react";
import { useSession } from "./demo-provider";
import { SessionGate } from "./workspace-shell";
import { roleLabels } from "@/lib/api";

export function ContractorShell({ children }: { children: ReactNode }) {
  return (
    <SessionGate allowed={["GESTOR_CONTR"]}>
      <Contractor>{children}</Contractor>
    </SessionGate>
  );
}

function Contractor({ children }: { children: ReactNode }) {
  const { me, logout, isDemo } = useSession();
  const router = useRouter();
  if (!me) return null;
  return (
    <div className="workspace">
      <aside className="workspace-sidebar">
        <div className="sidebar-brand">
          <Link href="/" aria-label="DocRisk AI — início">
            <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="177" height="46" />
          </Link>
        </div>
        <span className="sidebar-caption">PORTAL DA CONTRATANTE</span>
        <nav aria-label="Navegação da contratante">
          <Link href="/contratante" className="active" aria-current="page">
            <FileCheck2 size={19} /> Pareceres publicados
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p>
              <strong>{isDemo ? "Demonstração offline" : "Ambiente conectado"}</strong>
              <span>{isDemo ? "Dados fictícios · somente consulta" : "API de testes"}</span>
            </p>
          </div>
          <button
            className="sidebar-link"
            onClick={() => {
              logout();
              router.push("/acesso");
            }}
          >
            <LogOut size={17} /> Sair
          </button>
          <Link href="/">
            Voltar ao site <ArrowUpRight size={15} />
          </Link>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <strong>Pareceres publicados</strong>
          </div>
          <div className="workspace-person">
            <span className="avatar">GC</span>
            <div>
              <strong>{me.nome}</strong>
              <small>{roleLabels[me.papel]}</small>
            </div>
          </div>
        </header>
        <main className="workspace-body">
          {isDemo && <div className="api-notice" role="status"><strong>Demonstração offline:</strong> parecer ilustrativo, não publicado de verdade.</div>}
          {children}
        </main>
      </div>
    </div>
  );
}
