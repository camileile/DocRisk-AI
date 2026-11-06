"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileCheck2,
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
  { href: "/painel/pareceres", label: "Pareceres", icon: FileCheck2 },
  { href: "/painel/pendencias", label: "Pendências", icon: CircleAlert },
  { href: "/painel/envio", label: "Prévia de envio", icon: Upload },
];
export function WorkspaceShell({ children }: { children: ReactNode }) {
  const path = usePathname().replace(/\/$/, "");
  const { role, setRole, contract, setContract, competence, setCompetence, apiSession } =
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
  if (role === "GESTOR_CONTR")
    return (
      <main className="demo-gate">
        <img
          src="/brand/logo-horizontal-claro.svg"
          alt="DocRisk AI"
          width="200"
          height="52"
        />
        <h1>Continue no portal da contratante.</h1>
        <p>
          Esta perspectiva consulta somente os exemplos de pareceres publicados
          do seu contrato.
        </p>
        <Link href="/contratante" className="button">
          Abrir portal da contratante <ArrowUpRight size={17} />
        </Link>
        <Link href="/acesso" className="text-link">
          Trocar perspectiva
        </Link>
      </main>
    );
  if (role === "ADMIN_BH")
    return (
      <main className="demo-gate">
        <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="200" height="52" />
        <h1>Continue na administração.</h1>
        <p>O perfil administrador consulta somente os exemplos de auditoria no seu ambiente separado.</p>
        <Link href="/administracao" className="button">
          Abrir auditoria administrativa <ArrowUpRight size={17} />
        </Link>
        <Link href="/acesso" className="text-link">Trocar perspectiva</Link>
      </main>
    );
  const title =
    (path.startsWith("/painel/lotes/")
      ? "Detalhes do lote"
      : path.startsWith("/painel/revisao/")
        ? "Conferência documental"
        : path.startsWith("/painel/conciliacoes/")
          ? "Detalhes da análise"
          : path.startsWith("/painel/pareceres/")
            ? "Detalhes do parecer"
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
        <span className="sidebar-caption">{apiSession ? "API DE TESTE · F1" : "ESPAÇO DE TRABALHO"}</span>
        <div className="workspace-module">
          <span>Trabalhista</span>
          <small>Módulo do MVP</small>
        </div>
        <nav aria-label="Navegação do painel">
          {navigation
            .filter((item) =>
              apiSession
                ? (item.href === "/painel" || item.href === "/painel/lotes" ||
                    (item.href === "/painel/envio" && apiSession.user.org_tipo === "FORNECEDORA"))
                : role === "ANALISTA_BH"
                ? item.href !== "/painel/envio"
                : item.href !== "/painel/revisao" &&
                  item.href !== "/painel/conciliacoes" &&
                  item.href !== "/painel/pareceres",
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
                {apiSession && href === "/painel/envio" ? "Enviar documentos" : label}
              </Link>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <p>
              <strong>{apiSession ? "API local conectada" : "Modo demonstração"}</strong>
              <span>{apiSession ? "Contratos e lotes da API" : "Somente dados sintéticos"}</span>
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
                {apiSession?.user.nome ?? (role === "ANALISTA_BH"
                  ? "Analista Bernhoeft"
                  : "Operador da fornecedora")}
              </strong>
              <small>{apiSession ? apiSession.user.papel + " · API de teste" : "Perfil de demonstração"}</small>
            </div>
          </div>
        </header>
        <div className="workspace-demo-bar">
          <FlaskConical size={15} />
          <span>
            {apiSession
              ? "API F1 conectada: identidade, contratos e lotes do banco. Outras áreas continuam indisponíveis nesta integração."
              : "Dados de exemplo. As ações destas telas ainda não estão conectadas à API."}
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
                  {apiSession
                    ? (apiSession.contracts.length
                        ? apiSession.contracts.map((c) => (
                            <option key={c.id} value={c.id}>{c.nome} · {c.id}</option>
                          ))
                        : <option value="">Nenhum contrato autorizado</option>)
                    : contracts
                        .filter((c) => role === "ANALISTA_BH" || c.id === "CTR-001")
                        .map((c) => (
                          <option key={c.id} value={c.id}>{c.name} · {c.id}</option>
                        ))}
                </select>
              </label>
              {!apiSession && <label>
                Competência
                <select
                  value={competence}
                  onChange={(e) => setCompetence(e.target.value)}
                >
                  <option>10/2026</option>
                  <option>09/2026</option>
                </select>
              </label>}
            </div>
          </div>
          {apiSession && path !== "/painel" && path !== "/painel/lotes" &&
            !(path === "/painel/envio" && apiSession.user.org_tipo === "FORNECEDORA") ? (
            <div className="workspace-card api-unavailable">
              <h2>Esta área ainda não está integrada à API.</h2>
              <p>Para evitar misturar informações do backend com exemplos sintéticos, consulte por enquanto a visão geral ou a lista de lotes.</p>
              <Link className="button secondary" href="/painel/lotes">Consultar lotes da API</Link>
            </div>
          ) : children}
        </main>
      </div>
    </div>
  );
}
