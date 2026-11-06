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
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import type { DemoRole } from "@/lib/demo";
export default function Access() {
  const [selected, setSelected] = useState<DemoRole>("ANALISTA_BH");
  const { setRole } = useDemo();
  const router = useRouter();
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
                selected === "GESTOR_CONTR" ? "/contratante" : "/painel",
              );
            }}
          >
            Explorar demonstração <ArrowRight size={18} />
          </button>
          <p className="demo-disclosure">
            Esta é uma navegação demonstrativa, sem autenticação. Nenhum
            documento real é enviado. O perfil de administrador será
            desenvolvido em uma próxima etapa.
          </p>
        </div>
      </div>
    </main>
  );
}
