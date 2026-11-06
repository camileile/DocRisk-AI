"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  FileCheck2,
  KeyRound,
  PlugZap,
  Layers3,
  LockKeyhole,
  ShieldCheck,
  UserCog,
  type LucideIcon,
} from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { roleLabels, type Papel } from "@/lib/api";
import { DEMO_ROLES } from "@/lib/offline-demo";

const icons: Record<Papel, LucideIcon> = {
  ANALISTA_BH: ShieldCheck,
  ADMIN_BH: LockKeyhole,
  GESTOR_FORN: UserCog,
  OPERADOR_FORN: Building2,
  GESTOR_CONTR: FileCheck2,
};
const descriptions: Record<Papel, string> = {
  ANALISTA_BH: "Revisar documentos, conciliações, pendências e publicar pareceres.",
  ADMIN_BH: "Consultar a trilha de auditoria e os indicadores da operação.",
  GESTOR_FORN: "Enviar lotes, acompanhar processamento e responder pendências.",
  OPERADOR_FORN: "Enviar lotes e reenviar documentos corrigidos.",
  GESTOR_CONTR: "Consultar somente os pareceres publicados do contrato.",
};

function destinationFor(role: Papel): string {
  if (role === "GESTOR_CONTR") return "/contratante";
  if (role === "ADMIN_BH") return "/administracao";
  return "/painel";
}

export default function Access() {
  const [selected, setSelected] = useState<Papel>("ANALISTA_BH");
  const [entering, setEntering] = useState(false);
  const [token, setTokenInput] = useState("");
  const [tokenError, setTokenError] = useState("");
  const { login, enterDemo } = useSession();
  const router = useRouter();

  function enter() {
    if (entering) return;
    setEntering(true);
    const user = enterDemo(selected);
    router.push(destinationFor(user.papel));
  }

  async function enterWithToken() {
    if (entering || !token.trim()) return;
    setEntering(true);
    setTokenError("");
    try {
      const me = await login(token.trim());
      setTokenInput("");
      router.push(destinationFor(me.papel));
    } catch (err) {
      setTokenError(err instanceof Error ? err.message : "Não foi possível conectar à API.");
      setEntering(false);
    }
  }

  return (
    <main className="access-page">
      <div className="access-story">
        <Link href="/" aria-label="DocRisk AI — início">
          <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="200" height="52" />
        </Link>
        <div>
          <span className="eyebrow">DO DOCUMENTO À DECISÃO</span>
          <h1>
            Mais contexto.
            <br />
            Menos incerteza.
            <br />
            <em>Pessoas no controle.</em>
          </h1>
          <p>Na demonstração, cada perfil visualiza apenas dados ilustrativos; o modo operacional tem permissões verificadas pela API.</p>
          <div className="access-principle">
            <Layers3 size={28} />
            <span>
              Uma base de inteligência.
              <br />
              <strong>Um fluxo para cada responsabilidade.</strong>
            </span>
          </div>
        </div>
        <small>Hack Garanhuns Tech 2026 · MVP com dados sintéticos</small>
      </div>
      <div className="access-content">
        <Link href="/" className="back-link">
          <ArrowLeft size={16} /> Voltar ao site
        </Link>
        <div className="access-form">
          <span className="pill light">AMBIENTE DE DEMONSTRAÇÃO</span>
          <h2>Entrar na plataforma.</h2>
          <p>Escolha um dos cinco perfis para explorar a plataforma com dados fictícios, sem token e sem conexão com a API.</p>
          <fieldset className="persona-options">
            <legend>Perfil de acesso fictício</legend>
            {DEMO_ROLES.map((role) => {
              const Icon = icons[role];
              return (
                <label key={role} className={selected === role ? "persona selected" : "persona"}>
                  <input
                    type="radio"
                    name="perfil"
                    value={role}
                    checked={selected === role}
                    onChange={() => setSelected(role)}
                  />
                  <Icon size={25} />
                  <span>
                    <strong>{roleLabels[role]}</strong>
                    <small>{descriptions[role]}</small>
                  </span>
                  <span className="persona-check">{selected === role && <Check size={14} />}</span>
                </label>
              );
            })}
          </fieldset>
          <button className="button access-enter" onClick={enter} disabled={entering}>
            {entering ? "Entrando…" : "Explorar demonstração"} <ArrowRight size={18} />
          </button>
          <p className="demo-disclosure">
            Perfis, documentos e indicadores são fictícios. A navegação funciona sem backend; envios, aprovações e publicações
            não são realizados neste modo.
          </p>
          <section className="api-access" aria-labelledby="api-access-title">
            <span className="eyebrow">
              <PlugZap size={15} /> ENTRAR COM TOKEN
            </span>
            <h3 id="api-access-title">Conectar à API de testes</h3>
            <p>Uso exclusivo em ambiente de desenvolvimento local com FastAPI iniciado. Aqui o backend determina o perfil e os contratos.</p>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void enterWithToken();
              }}
            >
              <label htmlFor="api-test-token">Token Bearer de teste</label>
              <div className="api-access-input">
                <KeyRound size={18} aria-hidden="true" />
                <input
                  id="api-test-token"
                  type="password"
                  value={token}
                  onChange={(event) => {
                    setTokenInput(event.target.value);
                    setTokenError("");
                  }}
                  placeholder="Cole o token do backend local"
                  autoComplete="off"
                  spellCheck={false}
                  required
                  disabled={entering}
                />
              </div>
              <button type="submit" className="button api-access-submit" disabled={entering || !token.trim()}>
                <PlugZap size={17} /> {entering ? "Conectando…" : "Conectar API de testes"}
              </button>
              {tokenError && (
                <p className="api-access-error" role="alert">
                  {tokenError}
                </p>
              )}
            </form>
            <small>Não utilize tokens de produção. O token fica só nesta aba (sessionStorage) e é apagado ao sair.</small>
          </section>
        </div>
      </div>
    </main>
  );
}
