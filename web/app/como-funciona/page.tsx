import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Upload, ScanLine, Fingerprint, UserCheck, FileWarning, ClipboardCheck, ChartNoAxesCombined, FileCheck2 } from "lucide-react";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
export const metadata: Metadata = {
  title: "Como Funciona | DocRisk AI",
  description: "Acompanhe o fluxo do DocRisk AI: importação, identificação documental, conciliação, correção e revisão humana.",
};
const scenarios = [
  {
    icon: FileWarning,
    badge: "CORREÇÃO NA ORIGEM",
    title: "O arquivo está ilegível?",
    text: "A pendência identifica o documento que não pôde ser conferido. A fornecedora recebe a indicação e pode reenviar uma versão corrigida.",
    outcome: "Reenvio e rastreabilidade da pendência",
  },
  {
    icon: ClipboardCheck,
    badge: "CONFERÊNCIA DO ANALISTA",
    title: "A leitura ou a conciliação exige atenção?",
    text: "A fila reúne os itens que precisam de revisão. O analista consulta a evidência, corrige campos quando necessário e decide o encaminhamento.",
    outcome: "Revisão humana com justificativa",
  },
  {
    icon: ChartNoAxesCombined,
    badge: "VISÃO PARA DECISÃO",
    title: "Os documentos estão aptos?",
    text: "As informações podem sustentar conciliações e indicadores. A publicação de pareceres depende da aprovação por pessoa autorizada.",
    outcome: "Indicadores e parecer publicado após aprovação",
  },
];
export default function ComoFunciona() {
  return (
    <>
      <Header />
      <main id="conteudo">
        <section className="marketing-page-hero">
          <div className="container">
            <Link href="/" className="marketing-breadcrumb">Início <span aria-hidden="true">/</span> Como Funciona</Link>
            <span className="eyebrow">DO ARQUIVO À DECISÃO</span>
            <h1>Um fluxo conectado.<br /><em>As exceções não ficam escondidas.</em></h1>
            <p>O processamento organiza a informação. A fornecedora corrige os arquivos necessários, e a equipe de análise confere os indícios antes de publicar resultados.</p>
            <div className="marketing-hero-actions">
              <Link className="button" href="/modulos">Conhecer o módulo Trabalhista <ArrowUpRight size={17}/></Link>
              <Link className="button secondary" href="/solucao">Sobre a plataforma <ArrowRight size={17}/></Link>
            </div>
          </div>
        </section>
        <section  className="section container">
          <div className="section-heading">
            <div>
              <span className="eyebrow">COMO FUNCIONA</span>
              <h2>
                Do primeiro arquivo
                <br />à decisão fundamentada.
              </h2>
            </div>
            <p>
              Um fluxo proposto para transformar
              <br />
              volume documental em clareza.
            </p>
          </div>
          <div className="steps">
            {[
              {
                icon: Upload,
                title: "Receba os documentos",
                text: "O fluxo começa com o envio de lotes em PDF, imagens ou dados de jornada em AEJ.",
              },
              {
                icon: ScanLine,
                title: "Organize com inteligência",
                text: "A IA apoia a leitura; o processamento organiza e conecta as informações relevantes.",
              },
              {
                icon: Fingerprint,
                title: "Confira as evidências",
                text: "Indícios e pendências são apresentados com referência à origem documental.",
              },
              {
                icon: UserCheck,
                title: "Revise e decida",
                text: "A equipe responsável confere a análise e aprova o parecer antes da publicação.",
              },
            ].map(({ icon: Icon, title, text }, i) => (
              <article className="step" key={title}>
                <div className="step-top">
                  <span>0{i + 1}</span>
                  <Icon size={23} />
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="marketing-scenarios">
          <div className="container section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">TRÊS CAMINHOS DO PROCESSAMENTO</span>
                <h2>O resultado determina<br />o próximo passo.</h2>
              </div>
              <p>O mesmo lote pode reunir documentos aprovados, itens que exigem revisão e pendências que voltam à fornecedora.</p>
            </div>
            <div className="marketing-scenario-grid">
              {scenarios.map(({icon: Icon, badge, title, text, outcome}) => (
                <article className="marketing-scenario" key={title}>
                  <div className="marketing-scenario-top"><Icon size={28} aria-hidden="true"/><span>{badge}</span></div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <div className="marketing-scenario-outcome"><FileCheck2 size={16} aria-hidden="true"/>{outcome}</div>
                </article>
              ))}
            </div>
          </div>
        </section>
        <section className="section container marketing-responsibilities">
          <div className="section-heading">
            <div><span className="eyebrow">RESPONSABILIDADES CLARAS</span><h2>Cada participante no seu contexto.</h2></div>
            <p>O fluxo combina trabalho operacional com controles de acesso por organização e perfil.</p>
          </div>
          <div className="marketing-role-grid">
            <div><strong>Fornecedora</strong><p>Envia documentos e responde às correções solicitadas.</p></div>
            <div><strong>Analista da auditora</strong><p>Confere documentos, investiga divergências e aprova ou encaminha pendências.</p></div>
            <div><strong>Contratante</strong><p>Acompanha os resultados e pareceres publicados para seu contexto autorizado.</p></div>
          </div>
          <p className="marketing-subtle">Uma divergência é um indício para investigação, não uma irregularidade comprovada automaticamente.</p>
        </section>
        <section className="container marketing-next">
          <div><span className="eyebrow">FLUXO DO MVP</span><h2>Veja onde as análises se especializam.</h2><p>O módulo Trabalhista relaciona dados de jornada, folha e pagamento, incluindo arquivos AEJ.</p></div>
          <Link className="button" href="/modulos">Explorar módulos <ArrowUpRight size={17}/></Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
