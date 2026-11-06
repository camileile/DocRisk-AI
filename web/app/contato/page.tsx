import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight, ArrowLeft, MessageSquare, Code2 } from "lucide-react";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { ContactForm } from "@/components/contact-form";
export const metadata: Metadata = {
  title: "Contato | DocRisk AI",
  description:
    "Converse sobre a proposta do DocRisk AI, o módulo Trabalhista e possibilidades de colaboração.",
};
export default function Contato() {
  return (
    <>
      <Header />
      <main className="container contact-page">
        <Link href="/" className="back-link">
          <ArrowLeft size={16} /> Voltar para o início
        </Link>
        <div className="contact-layout">
          <div className="contact-copy">
            <span className="eyebrow">CONTATO</span>
            <h1>
              Boas conexões.
              <br />
              <em>Novas possibilidades.</em>
            </h1>
            <p className="lead">
              Quer conhecer a proposta, conversar sobre o módulo Trabalhista ou
              colaborar com o projeto? Vamos nos conectar.
            </p>
            <div className="contact-info">
              <MessageSquare />
              <div>
                <h3>Um projeto em construção</h3>
                <p>
                  O DocRisk AI está em desenvolvimento para o Hack Garanhuns
                  Tech 2026. O canal comercial de contato será divulgado nesta
                  página.
                </p>
              </div>
            </div>
            <a
              href="https://github.com/camileile/DocRisk-AI"
              className="contact-info github-link"
              target="_blank"
              rel="noreferrer"
            >
              <Code2 />
              <div>
                <h3>
                  Acompanhe no GitHub <ArrowUpRight size={16} />
                </h3>
                <p>Conheça o repositório e a evolução do projeto.</p>
              </div>
            </a>
          </div>
          <ContactForm />
        </div>
      </main>
      <Footer />
    </>
  );
}
