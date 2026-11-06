"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  FileCheck2,
  ShieldCheck,
  Check,
  Layers3,
  LockKeyhole,
  KeyRound,
  PlugZap,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import type { DemoRole } from "@/lib/demo";
import { apiIsConfigured } from "@/lib/api-client";
export default function Access() {
  const [selected, setSelected] = useState<DemoRole>("ANALISTA_BH");
  const { setRole, connectApi } = useDemo();
  const [token, setToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const router = useRouter();
  async function enterApi() {
    if (connecting || !token.trim()) return;
    setConnecting(true);
    setConnectionError("");
    try {
      await connectApi(token);
      setToken("");
      router.push("/painel");
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : "Não foi possível conectar à API.");
    } finally {
      setConnecting(false);
    }
  }
  return (
    <main className="access-page">
      <div className="access-story">
        <Link href="/" aria-label="DocRisk AI — início">
          <img
            src="/brand/logo-horizontal-claro.svg"
            alt="DocRisk AI"
            width="200"
            height="52"
          />
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
          <p>
            Explore o fluxo do módulo Trabalhista e veja como documentos,
            evidências e pendências se conectam.
          </p>
          <div className="access-principle">
            <Layers3 size={28} />
            <span>
              Uma base de inteligência.
              <br />
              <strong>Um fluxo para cada responsabilidade.</strong>
            </span>
          </div>
        </div>
        <small>Hack Garanhuns Tech 2026 · Protótipo em desenvolvimento</small>
      </div>
      <div className="access-content">
        <Link href="/" className="back-link">
          <ArrowLeft size={16} /> Voltar ao site
        </Link>
        <div className="access-form">
          <span className="pill light">AMBIENTE DEMONSTRATIVO</span>
          <h2>Conheça a plataforma.</h2>
          <p>
            Escolha uma perspectiva para explorar as telas com dados sintéticos.
          </p>
          <fieldset className="persona-options">
            <legend>Como deseja explorar?</legend>
            {[
              {
                value: "ANALISTA_BH" as const,
                icon: ShieldCheck,
                name: "Analista Bernhoeft",
                text: "Acompanhar documentos, revisões e pendências.",
              },
              {
                value: "OPERADOR_FORN" as const,
                icon: Building2,
                name: "Operador da fornecedora",
                text: "Conferir envios e correções do Contrato Alfa.",
              },
              {
                value: "GESTOR_CONTR" as const,
                icon: FileCheck2,
                name: "Gestor da contratante",
                text: "Consultar os pareceres publicados do Contrato Alfa.",
              },
              {
                value: "ADMIN_BH" as const,
                icon: LockKeyhole,
                name: "Administrador Bernhoeft",
                text: "Explorar eventos sintéticos de auditoria e acessos negados.",
              },
            ].map(({ value, icon: Icon, name, text }) => (
              <label
                key={value}
                className={selected === value ? "persona selected" : "persona"}
              >
                <input
                  type="radio"
                  name="perfil"
                  value={value}
                  checked={selected === value}
                  onChange={() => setSelected(value)}
                />
                <Icon size={25} />
                <span>
                  <strong>{name}</strong>
                  <small>{text}</small>
                </span>
                <span className="persona-check">
                  {selected === value && <Check size={14} />}
                </span>
              </label>
            ))}
          </fieldset>
          <button
            className="button access-enter"
            onClick={() => {
              setRole(selected);
              router.push(
                selected === "GESTOR_CONTR"
                  ? "/contratante"
                  : selected === "ADMIN_BH"
                    ? "/administracao"
                    : "/painel",
              );
            }}
          >
            Explorar demonstração <ArrowRight size={18} />
          </button>
          <p className="demo-disclosure">
            Esta é uma navegação demonstrativa, sem autenticação. Nenhum
            documento real é enviado. A área administrativa exibe apenas eventos
            sintéticos, sem acesso a logs reais.
          </p>
          {apiIsConfigured() && (
            <section className="api-access" aria-labelledby="api-access-title">
              <span className="eyebrow"><PlugZap size={15} /> INTEGRAÇÃO LOCAL · F1</span>
              <h3 id="api-access-title">Conectar à API de testes</h3>
              <p>Use um token de usuário de teste gerado pelo backend local. O perfil e os contratos serão obtidos da API, não da seleção acima.</p>
              <form onSubmit={(event) => { event.preventDefault(); void enterApi(); }}>
                <label htmlFor="api-test-token">Token Bearer de teste</label>
                <div className="api-access-input">
                  <KeyRound size={18} aria-hidden="true" />
                  <input id="api-test-token" type="password" value={token}
                    onChange={(event) => { setToken(event.target.value); setConnectionError(""); }}
                    placeholder="Cole o token do backend local" autoComplete="off"
                    spellCheck={false} required disabled={connecting} />
                </div>
                <button type="submit" className="button api-access-submit" disabled={connecting || !token.trim()}>
                  <PlugZap size={17} /> {connecting ? "Conectando…" : "Conectar API de testes"}
                </button>
                {connectionError && <p className="api-access-error" role="alert">{connectionError}</p>}
              </form>
              <small>Credencial somente em memória, apagada ao trocar de perspectiva ou recarregar. Não utilize tokens de produção. Integração limitada a analista e fornecedora.</small>
            </section>
          )}
        </div>
      </div>
    </main>
  );
}
