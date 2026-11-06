import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Layers3, Search, ShieldCheck, Fingerprint, UserCheck, GitMerge } from "lucide-react";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
export const metadata: Metadata = {
  title: "A Plataforma | DocRisk AI",
  description: "Conheça a arquitetura modular, a rastreabilidade e a revisão humana na proposta do DocRisk AI.",
};
export default function Solucao() {
  return (
    <>
      <Header />
      <main id="conteudo">
        <section className="marketing-page-hero">
          <div className="container">
            <Link href="/" className="marketing-breadcrumb">Início <span aria-hidden="true">/</span> A Plataforma</Link>
            <span className="eyebrow">O QUE CONECTA A PLATAFORMA</span>
            <h1>Uma base documental.<br /><em>Mais clareza em cada análise.</em></h1>
            <p>O DocRisk AI organiza o caminho entre o recebimento dos arquivos, as evidências identificadas e a decisão dos profissionais responsáveis.</p>
            <div className="marketing-hero-actions">
              <Link className="button" href="/como-funciona">Entender o fluxo <ArrowUpRight size={17}/></Link>
              <Link className="button secondary" href="/modulos">Ver os módulos <ArrowRight size={17}/></Link>
            </div>
          </div>
        </section>
        <section  className="section container platform">
          <div className="section-intro">
            <span className="eyebrow">A PLATAFORMA</span>
            <h2>
              Menos esforço para organizar.
              <br />
              Mais contexto para analisar.
            </h2>
          </div>
          <div className="platform-description">
            <p>
              Documentos chegam em formatos diferentes, misturados e com
              informações que precisam ser cruzadas. O DocRisk AI nasce para
              conectar essas etapas em um fluxo de análise mais claro.
            </p>
            <p>
              Uma base comum de inteligência documental, com módulos
              especializados para cada contexto de risco.
            </p>
          </div>
          <div className="benefit-grid">
            {[
              {
                icon: Layers3,
                title: "Documentos organizados",
                text: "Uma proposta de fluxo para separar, classificar e conectar documentos de um mesmo lote.",
              },
              {
                icon: Search,
                title: "Evidências acessíveis",
                text: "Informações vinculadas ao documento e à página de origem para facilitar a conferência.",
              },
              {
                icon: ShieldCheck,
                title: "Pessoas no controle",
                text: "Indícios seguem para revisão. O parecer só é publicado depois da aprovação humana.",
              },
            ].map(({ icon: Icon, title, text }) => (
              <article className="benefit" key={title}>
                <Icon size={25} />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="marketing-architecture section container" aria-labelledby="arquitetura-titulo">
          <div className="section-heading">
            <div><span className="eyebrow">ARQUITETURA MODULAR</span><h2 id="arquitetura-titulo">Uma estrutura comum.<br />Análises especializadas.</h2></div>
            <p>As funcionalidades de organização e rastreabilidade sustentam cada módulo de análise.</p>
          </div>
          <div className="marketing-architecture-chain">
            <div><Layers3 size={25}/><strong>DocRisk AI Core</strong><p>Recebimento, organização documental, evidências e rastreabilidade.</p></div>
            <GitMerge aria-hidden="true" size={26}/>
            <div><ShieldCheck size={25}/><strong>Módulo especializado</strong><p>Regras e verificações adequadas a cada tipo de documento e risco.</p></div>
            <GitMerge aria-hidden="true" size={26}/>
            <div><UserCheck size={25}/><strong>Decisão humana</strong><p>Conferência das exceções, justificativas e aprovação de pareceres.</p></div>
          </div>
          <p className="marketing-subtle">No MVP, o módulo especializado é o Trabalhista. Novos módulos são possibilidades de expansão, ainda não implementadas.</p>
        </section>
        <section className="trust-section">
          <div className="container trust-inner">
            <div>
              <span className="eyebrow">INTELIGÊNCIA COM RESPONSABILIDADE</span>
              <h2>
                A IA ajuda a encontrar.
                <br />
                Você tem contexto para decidir.
              </h2>
              <p>
                Uma divergência é um indício para conferir. O DocRisk AI foi
                pensado para apoiar a análise com rastreabilidade, transparência
                e revisão humana.
              </p>
              <Link href="/contato" className="text-link">
                Vamos conversar <ArrowRight size={18} />
              </Link>
            </div>
            <div className="trust-list">
              <article>
                <Fingerprint />
                <div>
                  <h3>Origem verificável</h3>
                  <p>
                    Documento, versão e página como referência de cada
                    evidência.
                  </p>
                </div>
              </article>
              <article>
                <UserCheck />
                <div>
                  <h3>Revisão antes da publicação</h3>
                  <p>
                    A análise passa pelas pessoas responsáveis por aprovar o
                    parecer.
                  </p>
                </div>
              </article>
              <article>
                <ShieldCheck />
                <div>
                  <h3>Acesso conforme o papel</h3>
                  <p>
                    Separação de responsabilidades prevista para cada
                    organização e perfil.
                  </p>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="container marketing-next">
          <div>
            <span className="eyebrow">PRÓXIMA ETAPA</span>
            <h2>Veja a plataforma em movimento.</h2>
            <p>Entenda como os arquivos percorrem o processamento, quando a equipe intervém e como os resultados chegam à decisão.</p>
          </div>
          <Link href="/como-funciona" className="button">Como funciona <ArrowUpRight size={17}/></Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
