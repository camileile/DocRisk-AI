"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowUpRight,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  FileCheck2,
  Files,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useSession } from "./demo-provider";
import { homeFor, roleLabels, type Papel } from "@/lib/api";
import { LoadingState } from "./workspace-parts";

const BH: Papel[] = ["ANALISTA_BH"];
const FORN: Papel[] = ["GESTOR_FORN", "OPERADOR_FORN"];
const navigation = [
  { href: "/painel", label: "Visão geral", icon: LayoutDashboard, roles: [...BH, ...FORN] },
  { href: "/painel/envio", label: "Enviar lote", icon: Upload, roles: FORN },
  { href: "/painel/lotes", label: "Lotes enviados", icon: Package, roles: [...BH, ...FORN] },
  { href: "/painel/documentos", label: "Documentos", icon: Files, roles: [...BH, ...FORN] },
  { href: "/painel/revisao", label: "Fila de revisão", icon: ClipboardCheck, roles: BH },
  { href: "/painel/pendencias", label: "Pendências", icon: CircleAlert, roles: [...BH, ...FORN] },
  { href: "/painel/conciliacoes", label: "Conciliações", icon: GitCompareArrows, roles: BH },
  { href: "/painel/pareceres", label: "Pareceres", icon: FileCheck2, roles: BH },
];

export function SessionGate({ allowed, children }: { allowed: Papel[]; children: ReactNode }) {
  const { me, loading, error } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (!loading && me && !allowed.includes(me.papel)) router.replace(homeFor(me.papel));
  }, [loading, me, allowed, router]);
  if (loading) return <main className="demo-gate"><LoadingState text="Verificando a sessão…" /></main>;
  if (!me || !allowed.includes(me.papel))
    return (
      <main className="demo-gate">
        <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="200" height="52" />
        <span className="pill light">ACESSO RESTRITO</span>
        <h1>{me ? "Redirecionando para a sua área…" : "Entre com um perfil para continuar."}</h1>
        {error && !me && <p>{error}</p>}
        {!me && (
          <Link className="button" href="/acesso">
            Entrar <ArrowUpRight size={18} />
          </Link>
        )}
      </main>
    );
  return <>{children}</>;
}

export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <SessionGate allowed={[...BH, ...FORN]}>
      <Workspace>{children}</Workspace>
    </SessionGate>
  );
}

function Workspace({ children }: { children: ReactNode }) {
  const path = usePathname().replace(/\/$/, "") || "/";
  const router = useRouter();
  const { me, logout, contracts, contract, setContract, isDemo } = useSession();
  const [open, setOpen] = useState(false);
  if (!me) return null;
  const items = navigation.filter((item) => item.roles.includes(me.papel));
  const current = items
    .filter((item) => path === item.href || (item.href !== "/painel" && path.startsWith(`${item.href}/`)))
    .sort((a, b) => b.href.length - a.href.length)[0];
  const initials = me.nome
    .split(/\s+/)
    .filter((w) => /^[A-ZÀ-Ú]/.test(w))
    .slice(0, 2)
    .map((w) => w[0])
    .join("");
  return (
    <div className="workspace">
      <aside className={open ? "workspace-sidebar visible" : "workspace-sidebar"}>
        <div className="sidebar-brand">
          <Link href="/" aria-label="DocRisk AI — início">
            <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="177" height="46" />
          </Link>
          <button className="sidebar-close" aria-label="Fechar navegação" onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </div>
        <span className="sidebar-caption">ESPAÇO DE TRABALHO</span>
        <div className="workspace-module">
          <span>Trabalhista</span>
          <small>{me.org_tipo === "BERNHOEFT" ? "Bernhoeft" : "Fornecedora"}</small>
        </div>
        <nav aria-label="Navegação do painel">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={current?.href === href ? "page" : undefined}
              className={current?.href === href ? "active" : ""}
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
      {open && <button className="sidebar-backdrop" aria-label="Fechar navegação" onClick={() => setOpen(false)} />}
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <button aria-label="Abrir navegação" className="workspace-menu" onClick={() => setOpen(true)}>
              <Menu size={22} />
            </button>
            <span>Trabalhista</span>
            <ChevronRight size={14} />
            <strong>{current?.label ?? "Visão geral"}</strong>
          </div>
          <div className="workspace-person">
            <span className="avatar">{initials || "U"}</span>
            <div>
              <strong>{me.nome}</strong>
              <small>{roleLabels[me.papel]}</small>
            </div>
          </div>
        </header>
        <main className="workspace-body" id="conteudo-painel">
          {isDemo && <div className="api-notice" role="status"><strong>Demonstração offline:</strong> informações e documentos são inteiramente fictícios. Nenhuma alteração é enviada à API.</div>}
          {contracts.length > 0 && (
            <div className="workspace-context">
              <span>CONTRATO</span>
              <div>
                <label>
                  <span className="sr-only">Contrato</span>
                  <select value={contract} onChange={(e) => setContract(e.target.value)}>
                    {contracts.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome} · {c.id}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
