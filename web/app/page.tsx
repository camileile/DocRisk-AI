import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, CheckCheck, FileText, ScanLine, Layers3, ShieldCheck, GitMerge, UserCheck, Clock3, Search } from "lucide-react";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { authEntry } from "@/lib/auth-mode";
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
              <Link href="/modulos" className="button secondary">
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

        <section className="section container marketing-preview" aria-labelledby="explorar-plataforma">
          <div className="section-heading">
            <div>
              <span className="eyebrow">CONHEÇA O DOCRISK AI</span>
              <h2 id="explorar-plataforma">Uma visão clara. Caminhos para aprofundar.</h2>
            </div>
            <p>Conheça a proposta, acompanhe o fluxo e veja como os módulos se conectam à base documental.</p>
          </div>
          <div className="marketing-preview-grid">
            <Link className="marketing-preview-card" href="/solucao">
              <span className="marketing-card-number">01 / PLATAFORMA</span>
              <Layers3 size={30} aria-hidden="true" />
              <h3>Inteligência que conecta documentos</h3>
              <p>Uma base para organizar evidências, apoiar a conferência e separar responsabilidades.</p>
              <span className="marketing-card-link">Conhecer a plataforma <ArrowUpRight size={16} /></span>
            </Link>
            <Link className="marketing-preview-card" href="/como-funciona">
              <span className="marketing-card-number">02 / FLUXO</span>
              <ScanLine size={30} aria-hidden="true" />
              <h3>Do envio à decisão humana</h3>
              <p>Entenda os caminhos de processamento, correção de arquivos e revisão de divergências.</p>
              <span className="marketing-card-link">Ver como funciona <ArrowUpRight size={16} /></span>
            </Link>
            <Link className="marketing-preview-card" href="/modulos">
              <span className="marketing-card-number">03 / ECOSSISTEMA</span>
              <Clock3 size={30} aria-hidden="true" />
              <h3>Um núcleo, diferentes especialidades</h3>
              <p>Trabalhista é o foco do MVP. Outros contextos mostram a capacidade de expansão.</p>
              <span className="marketing-card-link">Explorar módulos <ArrowUpRight size={16} /></span>
            </Link>
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
            Conheça o fluxo do DocRisk AI e acompanhe os próximos passos do
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
