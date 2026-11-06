import Link from "next/link";
import { authEntry } from "@/lib/auth-mode";
export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-main">
        <div>
          <Link href="/" aria-label="DocRisk AI — início">
            <img
              src="/brand/logo-horizontal-claro.svg"
              alt="DocRisk AI"
              width="175"
              height="44"
            />
          </Link>
          <p>
            Inteligência documental.
            <br />
            Clareza para cada decisão.
          </p>
        </div>
        <div>
          <span>Explore</span>
          <Link href="/#plataforma">A plataforma</Link>
          <Link href="/#modulos">Nossos módulos</Link>
          <Link href="/#como-funciona">Como funciona</Link>
        </div>
        <div>
          <span>Vamos conversar</span>
          <Link href="/contato">Contato com a equipe</Link>
          <Link href={authEntry()}>Acesso à plataforma</Link>
          <a
            href="https://github.com/camileile/DocRisk-AI"
            target="_blank"
            rel="noreferrer"
          >
            Projeto no GitHub ↗
          </a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© 2026 DocRisk AI</span>
        <span>Projeto em desenvolvimento · Hack Garanhuns Tech 2026</span>
      </div>
    </footer>
  );
}
