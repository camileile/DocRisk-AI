"use client";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight, ChevronRight, ClipboardList, FlaskConical, LockKeyhole, LogOut, Menu, ShieldCheck, X } from "lucide-react";
import { useSession } from "./demo-provider";
import { SessionGate } from "./workspace-shell";
import { roleLabels } from "@/lib/api";

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <SessionGate allowed={["ADMIN_BH"]}>
      <Admin>{children}</Admin>
    </SessionGate>
  );
}

function Admin({ children }: { children: ReactNode }) {
  const { me, logout } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  if (!me) return null;
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
          <small>Somente consulta</small>
        </div>
        <nav aria-label="Navegação administrativa">
          <Link href="/administracao" className="active" aria-current="page" onClick={() => setOpen(false)}>
            <ClipboardList size={19} /> Auditoria de ações
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p>
              <strong>Ambiente de demonstração</strong>
              <span>Somente dados sintéticos</span>
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
      {open && <button className="sidebar-backdrop" aria-label="Fechar navegação" onClick={() => setOpen(false)} />}
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
            <span className="avatar">
              <LockKeyhole size={17} />
            </span>
            <div>
              <strong>{me.nome}</strong>
              <small>{roleLabels[me.papel]}</small>
            </div>
          </div>
        </header>
        <main className="workspace-body" id="conteudo-admin">
          <div className="admin-context">
            <div>
              <ShieldCheck size={21} aria-hidden="true" />
              <span>Visão interna Bernhoeft</span>
            </div>
            <span className="admin-readonly">Somente consulta</span>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
