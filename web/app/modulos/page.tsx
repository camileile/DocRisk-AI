import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, Clock3, Layers3, Building2, HeartPulse, Leaf } from "lucide-react";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
const futureModules = [
  {
    icon: Building2,
    name: "Homologação de Fornecedores",
    description:
      "Certidões, requisitos de contratação e evidências de regularidade em um só lugar.",
  },
  {
    icon: HeartPulse,
    name: "Saúde e Segurança Ocupacional",
    description:
      "Organização de ASOs, treinamentos obrigatórios e documentos de conformidade.",
  },
  {
    icon: Leaf,
    name: "Conformidade Ambiental",
    description:
      "Acompanhamento documental de licenças, autorizações, validades e pendências.",
  },
];

export const metadata: Metadata = {
  title: "Módulos | DocRisk AI",
  description: "Conheça o módulo Trabalhista do MVP DocRisk AI e as possibilidades futuras de expansão modular.",
};
export default function Modulos() {
  return (
    <>
      <Header />
      <main id="conteudo">
        <section className="marketing-page-hero">
          <div className="container">
            <Link href="/" className="marketing-breadcrumb">Início <span aria-hidden="true">/</span> Módulos</Link>
            <span className="eyebrow">ECOSSISTEMA DOCRISK AI</span>
            <h1>Uma plataforma.<br /><em>Especialidades que se conectam.</em></h1>
            <p>O módulo Trabalhista é o foco do MVP. A arquitetura modular permite apresentar outras frentes de risco como possibilidades futuras, sem confundi-las com funcionalidades disponíveis.</p>
            <div className="marketing-hero-actions">
              <Link href="/como-funciona" className="button">Conhecer o fluxo <ArrowUpRight size={17}/></Link>
              <Link href="/solucao" className="button secondary">Sobre a plataforma <ArrowRight size={17}/></Link>
            </div>
          </div>
        </section>
        <section  className="module-section">
          <div className="container section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">ECOSSISTEMA DOCRISK AI</span>
                <h2>
                  Uma plataforma que cresce
                  <br />
                  com cada desafio.
                </h2>
              </div>
              <p>
                O mesmo núcleo de inteligência.
                <br />
                Diferentes perspectivas de análise.
              </p>
            </div>
            <div className="core-strip">
              <div className="icon-square">
                <Layers3 size={25} />
              </div>
              <div>
                <strong>DocRisk AI Core</strong>
                <span>
                  A base que conecta entrada, organização e evidências
                  documentais.
                </span>
              </div>
              <span className="core-label">NÚCLEO DA PLATAFORMA</span>
            </div>
            <article className="featured-module">
              <div className="module-main">
                <span className="pill">
                  <span className="status-dot" /> MÓDULO DO MVP · EM
                  VALIDAÇÃO
                </span>
                <div className="module-title">
                  <Clock3 size={32} />
                  <h3>Trabalhista</h3>
                </div>
                <p>
                  Ponto, horas extras e pagamentos conectados por trabalhador e
                  competência. Uma visão organizada para conferir divergências e
                  acompanhar pendências.
                </p>
                <div className="module-chips">
                  <span>Ponto & AEJ</span>
                  <span>Folha de pagamento</span>
                  <span>Conciliação</span>
                </div>
                <Link href="/como-funciona" className="text-link">
                  Entender o fluxo <ArrowUpRight size={18} />
                </Link>
              </div>
              <div className="module-detail">
                <span className="overline">UM FLUXO COM CONTEXTO</span>
                <div>
                  <Check size={17} />
                  <span>Conectar jornada e pagamento</span>
                </div>
                <div>
                  <Check size={17} />
                  <span>Apontar indícios com evidências</span>
                </div>
                <div>
                  <Check size={17} />
                  <span>Encaminhar pendências para conferência</span>
                </div>
                <div>
                  <Check size={17} />
                  <span>Apoiar a revisão e o parecer humano</span>
                </div>
                <small>
                  Funcionalidades do MVP em desenvolvimento e validação.
                </small>
              </div>
            </article>
            <div className="future-grid">
              {futureModules.map(({ icon: Icon, name, description }) => (
                <article className="future-module" key={name}>
                  <div className="future-top">
                    <Icon size={25} />
                    <span className="planned">PLANEJADO</span>
                  </div>
                  <h3>{name}</h3>
                  <p>{description}</p>
                  <span className="future-caption">
                    Visão de expansão <ArrowUpRight size={16} />
                  </span>
                </article>
              ))}
            </div>
            <p className="module-disclaimer">
              Os três módulos planejados representam a visão de expansão do
              produto e não integram o desenvolvimento do MVP.
            </p>
          </div>
        </section>

        <section className="container marketing-next">
          <div><span className="eyebrow">PRÓXIMA ETAPA</span><h2>Aprofunde o módulo em operação.</h2><p>Conheça o percurso dos documentos no fluxo Trabalhista, das inconsistências ao parecer humano.</p></div>
          <Link className="button" href="/como-funciona">Como funciona <ArrowUpRight size={17}/></Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
