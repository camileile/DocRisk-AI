"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowUpRight, Building2, ChevronRight, ClipboardList, FlaskConical,
  LayoutDashboard, LockKeyhole, LogOut, Menu, ShieldCheck, Users, X,
} from "lucide-react";
import { useSession } from "./demo-provider";
import { SessionGate } from "./workspace-shell";
import { roleLabels } from "@/lib/api";

const navigation = [
  { href: "/administracao", title: "Visão Geral", Icon: LayoutDashboard },
  { href: "/administracao/empresas", title: "Empresas e Contratos", Icon: Building2 },
  { href: "/administracao/usuarios", title: "Gestão de Usuários", Icon: Users },
  { href: "/administracao/auditoria", title: "Auditoria", Icon: ClipboardList },
];

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <SessionGate allowed={["ADMIN_BH"]}>
      <Admin>{children}</Admin>
    </SessionGate>
  );
}

function Admin({ children }: { children: ReactNode }) {
  const { me, logout, isDemo } = useSession();
  const router = useRouter();
  const path = usePathname().replace(/\/$/, "") || "/";
  const [open, setOpen] = useState(false);
  if (!me) return null;
  const current = navigation.find((item) => item.href === path) ?? navigation[0];

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
          <span>Gestão da operação</span>
          <small>Empresas, contratos, usuários e indicadores</small>
        </div>
        <nav aria-label="Navegação administrativa">
          {navigation.map(({ href, title, Icon }) => (
            <Link
              href={href}
              key={href}
              className={current.href === href ? "active" : ""}
              aria-current={current.href === href ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} /> {title}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p>
              <strong>{isDemo ? "Demonstração offline" : "Ambiente conectado"}</strong>
              <span>{isDemo ? "Dados fictícios · somente consulta" : "API de testes · autenticação demo"}</span>
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
          <Link href="/">Voltar ao site <ArrowUpRight size={15} /></Link>
        </div>
      </aside>
      {open && <button className="sidebar-backdrop" aria-label="Fechar navegação" onClick={() => setOpen(false)} />}
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <button className="workspace-menu" aria-label="Abrir navegação" onClick={() => setOpen(true)}>
              <Menu size={22} />
            </button>
            <span>Administração Bernhoeft</span>
            <ChevronRight size={14} />
            <strong>{current.title}</strong>
          </div>
          <div className="workspace-person">
            <span className="avatar"><LockKeyhole size={17} /></span>
            <div>
              <strong>{me.nome}</strong>
              <small>{roleLabels[me.papel]}</small>
            </div>
          </div>
        </header>
        <main className="workspace-body" id="conteudo-admin">
          {isDemo && (
            <div className="api-notice" role="status">
              <strong>Demonstração offline:</strong> dados fictícios e sem cadastros reais.
            </div>
          )}
          <div className="admin-context">
            <div><ShieldCheck size={21} aria-hidden="true" /><span>Gestão interna da organização auditora</span></div>
            <span className="admin-readonly">{isDemo ? "Somente consulta" : "API de testes"}</span>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
