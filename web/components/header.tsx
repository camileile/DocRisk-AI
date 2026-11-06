"use client";
import Link from "next/link";
import { authEntry } from "@/lib/auth-mode";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { useState } from "react";
export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="header">
      <div className="container header-inner">
        <Link href="/" aria-label="DocRisk AI — início" className="brand">
          <img
            src="/brand/logo-horizontal-claro.svg"
            alt="DocRisk AI"
            width="188"
            height="48"
          />
        </Link>
        <button
          className="menu-toggle"
          type="button"
          aria-label={open ? "Fechar menu" : "Abrir menu"}
          aria-expanded={open}
          aria-controls="navigation"
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </button>
        <nav
          id="navigation"
          aria-label="Navegação principal"
          className={open ? "navigation open" : "navigation"}
          onClick={() => setOpen(false)}
        >
          <Link href="/#plataforma">A plataforma</Link>
          <Link href="/#como-funciona">Como funciona</Link>
          <Link href="/#modulos">Módulos</Link>
          <Link href="/contato">Contato</Link>
          <Link href={authEntry()} className="button small">
            Acesso <ArrowUpRight size={16} />
          </Link>
        </nav>
      </div>
    </header>
  );
}
