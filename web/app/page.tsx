import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  FileText,
  ScanLine,
  Layers3,
  ShieldCheck,
  Clock3,
  Building2,
  Leaf,
  HeartPulse,
  GitMerge,
  Fingerprint,
  Search,
  Upload,
  UserCheck,
} from "lucide-react";
import { Header } from "@/components/header";
import { authEntry } from "@/lib/auth-mode";
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
export default function Home() {
  return (
    <>
      <Header />
      <main id="conteudo">
        <section className="hero container">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="status-dot" /> INTELIGÊNCIA DOCUMENTAL MODULAR
            </span>
            <h1>
              Documentos complexos.
              <br />
              Decisões <em>mais claras.</em>
            </h1>
            <p className="lead">
              Transforme documentos dispersos em informações conectadas.
              Inteligência artificial para organizar, evidências para conferir e
              pessoas para decidir.
            </p>
            <div className="actions">
              <Link href={authEntry()} className="button">
                Acessar plataforma <ArrowUpRight size={18} />
              </Link>
              <Link href="#modulos" className="button secondary">
                Explorar módulos <ArrowRight size={18} />
              </Link>
            </div>
            <div className="hero-notes">
              <span>
                <Check size={15} /> Evidências rastreáveis
              </span>
              <span>
                <Check size={15} /> Revisão humana
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="visual-orbit orbit-one" />
            <div className="visual-orbit orbit-two" />
            <div className="demo-window">
              <div className="window-top">
                <div className="window-dots">
                  <i />
                  <i />
                  <i />
                </div>
                <span>DocRisk AI · Visão documental</span>
                <span className="demo-tag">PRÉVIA</span>
              </div>
              <div className="window-body">
                <div className="demo-heading">
                  <div>
                    <span className="overline">MÓDULO TRABALHISTA</span>
                    <h3>De documentos a evidências.</h3>
                  </div>
                  <div className="icon-square">
                    <Layers3 size={23} />
                  </div>
                </div>
                <div className="demo-file">
                  <span className="file-icon">
                    <FileText size={22} />
                  </span>
                  <div>
                    <strong>Lote de documentos</strong>
                    <small>PDF, imagem e AEJ</small>
                  </div>
                  <span className="mini-badge">Recebido</span>
                </div>
                <div className="demo-connector">
                  <span />
                  <ScanLine size={16} />
                  <span />
                </div>
                <div className="extraction">
                  <div>
                    <span className="purple-dot" />
                    <strong>Informações organizadas</strong>
                    <CheckCheck size={18} />
                  </div>
                  <div className="data-row">
                    <span>Trabalhador</span>
                    <b>Pessoa exemplo 001</b>
                  </div>
                  <div className="data-row">
                    <span>Competência</span>
                    <b>Outubro / 2026</b>
                  </div>
                  <div className="data-row">
                    <span>Documentos vinculados</span>
                    <b>Ponto + folha</b>
                  </div>
                </div>
                <div className="review-note">
                  <ShieldCheck size={20} />
                  <div>
                    <strong>A decisão continua humana.</strong>
                    <small>Evidências prontas para conferência.</small>
                  </div>
                </div>
              </div>
            </div>
            <div className="floating-label">
              <span className="icon-square">
                <GitMerge size={19} />
              </span>
              <div>
                <strong>Informação conectada</strong>
                <small>Da origem à revisão.</small>
              </div>
            </div>
            <p className="visual-caption">
              Visão ilustrativa do fluxo proposto · dados sintéticos
            </p>
          </div>
        </section>
        <div className="format-band">
          <div className="container format-inner">
            <span>
              Uma base documental.
              <br />
              <strong>Múltiplas possibilidades.</strong>
            </span>
            <div>
              <FileText size={20} /> PDF & imagens
            </div>
            <div>
              <ScanLine size={20} /> Leitura com IA
            </div>
            <div>
              <GitMerge size={20} /> Dados conectados
            </div>
            <div>
              <UserCheck size={20} /> Revisão humana
            </div>
          </div>
        </div>
        <section id="plataforma" className="section container platform">
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
        <section id="modulos" className="module-section">
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
                  <span className="status-dot" /> FOCO DO MVP · EM
                  DESENVOLVIMENTO
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
                <Link href="/contato?assunto=trabalhista" className="text-link">
                  Conhecer o módulo <ArrowUpRight size={18} />
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
                  Escopo planejado do MVP. Funcionalidades em implementação.
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
        <section id="como-funciona" className="section container">
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
        <section className="container cta">
          <span className="eyebrow">VAMOS CONSTRUIR ESSA VISÃO</span>
          <h2>
            Mais clareza começa
            <br />
            com uma conversa.
          </h2>
          <p>
            Conheça a proposta do DocRisk AI e acompanhe os próximos passos do
            projeto.
          </p>
          <Link href="/contato" className="button">
            Falar sobre o projeto <ArrowUpRight size={18} />
          </Link>
          <span className="cta-note">
            Em desenvolvimento no Hack Garanhuns Tech 2026
          </span>
        </section>
      </main>
      <Footer />
    </>
  );
}
