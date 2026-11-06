"use client";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import {
  ArrowUpRight, ChevronRight, ClipboardList, FlaskConical,
  LockKeyhole, LogOut, Menu, ShieldCheck, X,
} from "lucide-react";
import { useDemo } from "./demo-provider";

export function AdminShell({ children }: { children: ReactNode }) {
  const { role, setRole } = useDemo();
  const [open, setOpen] = useState(false);
  const path = usePathname();

  if (role !== "ADMIN_BH") {
    return (
      <main className="demo-gate">
        <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="200" height="52" />
        <span className="pill light">ESPAÇO ADMINISTRATIVO · DEMO</span>
        <h1>Escolha o perfil administrador.</h1>
        <p>Esta tela mostra registros de auditoria sintéticos. A seleção de perfil não concede acesso à API nem substitui autenticação.</p>
        <Link className="button" href="/acesso">
          Escolher perspectiva <ArrowUpRight size={17} />
        </Link>
      </main>
    );
  }

  return (
    <div className="workspace admin-workspace">
      <aside className={open ? "workspace-sidebar visible" : "workspace-sidebar"}>
        <div className="sidebar-brand">
          <Link href="/" aria-label="DocRisk AI — início">
            <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="177" height="46" />
          </Link>
          <button className="sidebar-close" aria-label="Fechar navegação" onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </div>
        <span className="sidebar-caption">ADMINISTRAÇÃO BERNHOEFT</span>
        <div className="workspace-module">
          <span>Governança e rastreabilidade</span>
          <small>Acesso administrativo · exemplo</small>
        </div>
        <nav aria-label="Navegação administrativa">
          <Link href="/administracao" className={path.startsWith("/administracao") ? "active" : ""} aria-current="page" onClick={() => setOpen(false)}>
            <ClipboardList size={19} /> Auditoria de ações
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p><strong>Modo demonstração</strong><span>Registros exclusivamente sintéticos</span></p>
          </div>
          <Link href="/acesso" onClick={() => setRole(null)}>
            <LogOut size={17} /> Trocar perspectiva
          </Link>
          <Link href="/">
            Voltar ao site <ArrowUpRight size={15} />
          </Link>
        </div>
      </aside>
      {open && (
        <button className="sidebar-backdrop" aria-label="Fechar navegação" onClick={() => setOpen(false)} />
      )}
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <button className="workspace-menu" aria-label="Abrir navegação" onClick={() => setOpen(true)}>
              <Menu size={22} />
            </button>
            <span>Administração</span>
            <ChevronRight size={14} />
            <strong>Auditoria</strong>
          </div>
          <div className="workspace-person">
            <span className="avatar"><LockKeyhole size={17} /></span>
            <div>
              <strong>Administrador Bernhoeft</strong>
              <small>Perfil de demonstração</small>
            </div>
          </div>
        </header>
        <div className="workspace-demo-bar">
          <FlaskConical size={15} />
          <span>Eventos fictícios para apresentação. Nenhum log real foi consultado ou alterado.</span>
        </div>
        <main className="workspace-body" id="conteudo-admin">
          <div className="admin-context">
            <div>
              <ShieldCheck size={21} aria-hidden="true" />
              <span>Visão interna Bernhoeft</span>
            </div>
            <span className="admin-readonly">Somente consulta · demonstração</span>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
