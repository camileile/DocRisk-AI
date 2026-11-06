"use client";
import { useEffect, useState } from "react";
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
import { demoApiEnabled, demoApiToken } from "@/lib/demo-api";
import { publicDemoOnly } from "@/lib/auth-mode";

const icons: Record<Papel, LucideIcon> = {
  ADMIN_PLATAFORMA: Layers3,
  ANALISTA_BH: ShieldCheck,
  ADMIN_BH: LockKeyhole,
  GESTOR_FORN: UserCog,
  OPERADOR_FORN: Building2,
  GESTOR_CONTR: FileCheck2,
};
const descriptions: Record<Papel, string> = {
  ADMIN_PLATAFORMA: "Gerenciar organizações auditoras e dados institucionais da plataforma.",
  ANALISTA_BH: "Revisar documentos, conciliações, pendências e publicar pareceres.",
  ADMIN_BH: "Gerenciar empresas, contratos e usuários; consultar indicadores e auditoria.",
  GESTOR_FORN: "Enviar lotes, acompanhar processamento e responder pendências.",
  OPERADOR_FORN: "Enviar lotes e reenviar documentos corrigidos.",
  GESTOR_CONTR: "Consultar somente os pareceres publicados do contrato.",
};

function destinationFor(role: Papel): string {
  if (role === "ADMIN_PLATAFORMA") return "/plataforma";
  if (role === "GESTOR_CONTR") return "/contratante";
  if (role === "ADMIN_BH") return "/administracao";
  return "/painel";
}

export default function Access({ operational = false }: { operational?: boolean }) {
  const [selected, setSelected] = useState<Papel>("ANALISTA_BH");
  const [entering, setEntering] = useState(false);
  const [token, setTokenInput] = useState("");
  const [tokenError, setTokenError] = useState("");
  // O HTML pré-renderizado chega antes do React. Até a hidratação, o que fosse
  // digitado ou clicado seria descartado (o campo controlado voltaria a vazio).
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  const { login, enterDemo } = useSession();
  const router = useRouter();

  async function enter() {
    if (entering || !hydrated) return;
    setEntering(true);
    setTokenError("");
    try {
      const user = demoApiEnabled ? await login(await demoApiToken(selected)) : enterDemo(selected);
      router.push(destinationFor(user.papel));
    } catch (err) {
      setTokenError(err instanceof TypeError ? "Não foi possível conectar à API local. Confira se ela está rodando e se CORS_ORIGINS permite este site."
        : err instanceof Error ? err.message : "Não foi possível conectar à API local.");
      setEntering(false);
    }
  }

  async function enterWithToken() {
    if (entering || !hydrated || !token.trim()) return;
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
          <p>{operational ? "Acesso ao ambiente operacional, com perfil e permissões verificados pela API." : "A demonstração apresenta dados ilustrativos; o ambiente operacional utiliza permissões verificadas pela API."}</p>
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
          <span className="pill light">{operational ? "API DE TESTES" : "AMBIENTE DE DEMONSTRAÇÃO"}</span>
          <h2>{operational ? "Conectar ao ambiente de testes." : "Explorar a demonstração."}</h2>
          {!operational && <>
          <p>{demoApiEnabled ? "Escolha um perfil de teste. A API local permite enviar arquivos e acompanhar os resultados com dados sintéticos." : "Escolha um dos seis perfis para explorar a plataforma com dados fictícios, sem token e sem conexão com a API."}</p>
          <fieldset className="persona-options" disabled={!hydrated}>
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
          <button className="button access-enter" onClick={() => { void enter(); }} disabled={entering || !hydrated}>
            {entering ? "Entrando…" : demoApiEnabled ? "Entrar na demo com API" : "Explorar demonstração"} <ArrowRight size={18} />
          </button>
          {tokenError && <p className="api-access-error" role="alert">{tokenError}</p>}
          <p className="demo-disclosure">
            {demoApiEnabled ? "Ambiente local de testes. Envios e alterações são gravados na API. Utilize somente documentos sintéticos."
              : "Perfis, documentos e indicadores são fictícios. A navegação funciona sem backend; envios, aprovações e publicações não são realizados neste modo."}
          </p>
          {!publicDemoOnly && <Link className="text-link" href="/operacao">Conectar à API de testes <ArrowRight size={16} /></Link>}
          </>}
          {operational && <section className="api-access" aria-labelledby="api-access-title">
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
                  disabled={entering || !hydrated}
                />
              </div>
              <button type="submit" className="button api-access-submit" disabled={entering || !hydrated || !token.trim()}>
                <PlugZap size={17} /> {entering ? "Conectando…" : "Conectar API de testes"}
              </button>
              {tokenError && (
                <p className="api-access-error" role="alert">
                  {tokenError}
                </p>
              )}
            </form>
            <small>Não utilize tokens de produção. O token fica só nesta aba (sessionStorage) e é apagado ao sair.</small>
          </section>}
        </div>
      </div>
    </main>
  );
}
