"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  FileCheck2,
  Building2,
  ChevronRight,
  Menu,
  X,
  FlaskConical,
  LogOut,
  ArrowUpRight,
} from "lucide-react";
import { useDemo } from "./demo-provider";
export function ContractorShell({ children }: { children: ReactNode }) {
  const { role, setRole, competence, setCompetence } = useDemo();
  const [open, setOpen] = useState(false);
  const path = usePathname();
  if (role !== "GESTOR_CONTR")
    return (
      <main className="demo-gate">
        <img
          src="/brand/logo-horizontal-claro.svg"
          alt="DocRisk AI"
          width="200"
          height="52"
        />
        <span className="pill light">PORTAL DA CONTRATANTE</span>
        <h1>Escolha a perspectiva da contratante.</h1>
        <p>
          Esta área demonstra a consulta dos pareceres publicados. Selecione o
          perfil correspondente para explorar.
        </p>
        <Link className="button" href="/acesso">
          Escolher perspectiva <ArrowUpRight size={17} />
        </Link>
      </main>
    );
  return (
    <div className="workspace contractor-workspace">
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
        <span className="sidebar-caption">PORTAL DA CONTRATANTE</span>
        <div className="workspace-module">
          <span>Contratante Alfa</span>
          <small>Organização de demonstração</small>
        </div>
        <nav aria-label="Navegação da contratante">
          <Link
            className="active"
            href="/contratante"
            aria-current={
              path.replace(/\/$/, "") === "/contratante" ? "page" : undefined
            }
            onClick={() => setOpen(false)}
          >
            <FileCheck2 size={19} /> Pareceres publicados
          </Link>
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
              className="workspace-menu"
              aria-label="Abrir navegação"
              onClick={() => setOpen(true)}
            >
              <Menu size={22} />
            </button>
            <span>Contratante</span>
            <ChevronRight size={14} />
            <strong>
              {path.replace(/\/$/, "") === "/contratante"
                ? "Pareceres publicados"
                : "Consultar parecer"}
            </strong>
          </div>
          <div className="workspace-person">
            <span className="avatar">
              <Building2 size={17} />
            </span>
            <div>
              <strong>Gestor da contratante</strong>
              <small>Perfil de demonstração</small>
            </div>
          </div>
        </header>
        <div className="workspace-demo-bar">
          <FlaskConical size={15} />
          <span>
            Exemplos de versões previamente aprovadas. Nenhuma publicação real
            foi executada.
          </span>
        </div>
        <main className="workspace-body">
          <div className="workspace-context">
            <span>CONTEXTO DA CONSULTA</span>
            <div>
              <label>
                Contrato
                <select
                  aria-label="Contrato da contratante"
                  value="CTR-001"
                  onChange={() => {}}
                >
                  <option value="CTR-001">Contrato Alfa · CTR-001</option>
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
