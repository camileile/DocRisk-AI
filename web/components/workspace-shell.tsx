"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitCompareArrows,
  ClipboardCheck,
  Package,
  Files,
  CircleAlert,
  Upload,
  LogOut,
  ArrowUpRight,
  ChevronRight,
  FlaskConical,
  Menu,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { useDemo } from "./demo-provider";
import { contracts } from "@/lib/demo";
const navigation = [
  { href: "/painel", label: "Visão geral", icon: LayoutDashboard },
  { href: "/painel/lotes", label: "Lotes enviados", icon: Package },
  { href: "/painel/documentos", label: "Documentos", icon: Files },
  { href: "/painel/revisao", label: "Fila de revisão", icon: ClipboardCheck },
  {
    href: "/painel/conciliacoes",
    label: "Conciliações",
    icon: GitCompareArrows,
  },
  { href: "/painel/pendencias", label: "Pendências", icon: CircleAlert },
  { href: "/painel/envio", label: "Prévia de envio", icon: Upload },
];
export function WorkspaceShell({ children }: { children: ReactNode }) {
  const path = usePathname().replace(/\/$/, "");
  const { role, setRole, contract, setContract, competence, setCompetence } =
    useDemo();
  const [open, setOpen] = useState(false);
  if (!role)
    return (
      <main className="demo-gate">
        <img
          src="/brand/logo-horizontal-claro.svg"
          alt="DocRisk AI"
          width="200"
          height="52"
        />
        <span className="pill light">AMBIENTE DEMONSTRATIVO</span>
        <h1>Escolha uma perspectiva.</h1>
        <p>
          Inicie a demonstração para explorar as páginas. Ao recarregar,
          selecione o perfil novamente.
        </p>
        <Link className="button" href="/acesso">
          Escolher perfil <ArrowUpRight size={18} />
        </Link>
      </main>
    );
  const title =
    (path.startsWith("/painel/lotes/")
      ? "Detalhes do lote"
      : path.startsWith("/painel/revisao/")
        ? "Conferência documental"
        : path.startsWith("/painel/conciliacoes/")
          ? "Detalhes da análise"
          : navigation.find((item) => item.href === path)?.label) ??
    "Visão geral";
  return (
    <div className="workspace">
      <aside
        className={open ? "workspace-sidebar visible" : "workspace-sidebar"}
      >
        <div className="sidebar-brand">
          <Link href="/" aria-label="DocRisk AI — início">
            <img
              src="/brand/logo-horizontal-claro.svg"
              alt="DocRisk AI"
              width="177"
              height="46"
            />
          </Link>
          <button
            className="sidebar-close"
            aria-label="Fechar navegação"
            onClick={() => setOpen(false)}
          >
            <X size={20} />
          </button>
        </div>
        <span className="sidebar-caption">ESPAÇO DE TRABALHO</span>
        <div className="workspace-module">
          <span>Trabalhista</span>
          <small>Módulo do MVP</small>
        </div>
        <nav aria-label="Navegação do painel">
          {navigation
            .filter((item) =>
              role === "ANALISTA_BH"
                ? item.href !== "/painel/envio"
                : item.href !== "/painel/revisao" &&
                  item.href !== "/painel/conciliacoes",
            )
            .map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                aria-current={path === href ? "page" : undefined}
                className={
                  path === href ||
                  (href !== "/painel" && path.startsWith(`${href}/`))
                    ? "active"
                    : ""
                }
                onClick={() => setOpen(false)}
              >
                <Icon size={19} />
                {label}
              </Link>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p>
              <strong>Modo demonstração</strong>
              <span>Somente dados sintéticos</span>
            </p>
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
        <button
          className="sidebar-backdrop"
          aria-label="Fechar navegação"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <button
              aria-label="Abrir navegação"
              className="workspace-menu"
              onClick={() => setOpen(true)}
            >
              <Menu size={22} />
            </button>
            <span>Trabalhista</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <div className="workspace-person">
            <span className="avatar">
              {role === "ANALISTA_BH" ? "AB" : "OF"}
            </span>
            <div>
              <strong>
                {role === "ANALISTA_BH"
                  ? "Analista Bernhoeft"
                  : "Operador da fornecedora"}
              </strong>
              <small>Perfil de demonstração</small>
            </div>
          </div>
        </header>
        <div className="workspace-demo-bar">
          <FlaskConical size={15} />
          <span>
            Dados de exemplo. As ações destas telas ainda não estão conectadas à
            API.
          </span>
        </div>
        <main className="workspace-body" id="conteudo-painel">
          <div className="workspace-context">
            <span>CONTEXTO DA ANÁLISE</span>
            <div>
              <label>
                Contrato
                <select
                  value={contract}
                  onChange={(e) => setContract(e.target.value)}
                >
                  {contracts
                    .filter((c) => role === "ANALISTA_BH" || c.id === "CTR-001")
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} · {c.id}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Competência
                <select
                  value={competence}
                  onChange={(e) => setCompetence(e.target.value)}
                >
                  <option>10/2026</option>
                  <option>09/2026</option>
                </select>
              </label>
            </div>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
