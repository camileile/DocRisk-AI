"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ArrowUpRight, FileCheck2, FlaskConical, LayoutDashboard, LogOut, Menu, X } from "lucide-react";
import { authEntry } from "@/lib/auth-mode";
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
  const path = usePathname().replace(/\/$/, "");
  const [open, setOpen] = useState(false);
  const onReports = path === "/contratante/pareceres";
  if (!me) return null;
  return (
    <div className="workspace contractor-workspace">
      <aside className={open ? "workspace-sidebar visible" : "workspace-sidebar"}>
        <div className="sidebar-brand">
          <Link href="/" aria-label="DocRisk AI — início">
            <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="177" height="46" />
          </Link>
          <button className="sidebar-close" aria-label="Fechar navegação" onClick={() => setOpen(false)}><X size={20} /></button>
        </div>
        <span className="sidebar-caption">PORTAL DA CONTRATANTE</span>
        <nav aria-label="Navegação da contratante">
          <Link href="/contratante" className={!onReports ? "active" : ""} aria-current={!onReports ? "page" : undefined} onClick={() => setOpen(false)}>
            <LayoutDashboard size={19} /> Visão geral
          </Link>
          <Link href="/contratante/pareceres" className={onReports ? "active" : ""} aria-current={onReports ? "page" : undefined} onClick={() => setOpen(false)}>
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
              router.push(authEntry());
            }}
          >
            <LogOut size={17} /> Sair
          </button>
          <Link href="/">
            Voltar ao site <ArrowUpRight size={15} />
          </Link>
        </div>
      </aside>
      {open && <button className="sidebar-backdrop" aria-label="Fechar navegação" onClick={() => setOpen(false)} />}
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <button aria-label="Abrir navegação" className="workspace-menu" onClick={() => setOpen(true)}><Menu size={22} /></button>
            <strong>{onReports ? "Pareceres publicados" : "Visão geral"}</strong>
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
          {isDemo && <div className="api-notice" role="status"><strong>Demonstração offline:</strong> resultados e pareceres inteiramente fictícios, somente para consulta.</div>}
          {children}
        </main>
      </div>
    </div>
  );
}
