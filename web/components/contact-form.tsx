"use client";
import { useState, type FormEvent } from "react";
import { ArrowUpRight, Check, Copy } from "lucide-react";
export function ContactForm() {
  const [brief, setBrief] = useState("");
  const [copied, setCopied] = useState(false);
  function prepare(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBrief(
      `Olá, equipe DocRisk AI!\n\nNome: ${data.get("nome")}\nE-mail: ${data.get("email")}\nOrganização: ${data.get("empresa") || "Não informada"}\nAssunto: ${data.get("assunto")}\n\n${data.get("mensagem")}`,
    );
    setCopied(false);
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(brief);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }
  return (
    <form className="contact-form" onSubmit={prepare}>
      <h2>Vamos começar uma conversa.</h2>
      <p>
        Prepare sua mensagem e copie o texto para compartilhar com a equipe pelo
        canal que vocês já utilizam.
      </p>
      <div className="form-row">
        <label>
          Seu nome
          <input
            name="nome"
            autoComplete="name"
            placeholder="Como podemos chamar você?"
            required
            maxLength={120}
          />
        </label>
        <label>
          E-mail
          <input
            name="email"
            type="email"
            autoComplete="email"
            placeholder="voce@empresa.com"
            required
            maxLength={180}
          />
        </label>
      </div>
      <label>
        Organização <span>(opcional)</span>
        <input
          name="empresa"
          autoComplete="organization"
          placeholder="Nome da sua organização"
          maxLength={180}
        />
      </label>
      <label>
        Sobre o que quer conversar?
        <select name="assunto" defaultValue="Conhecer o projeto">
          <option>Conhecer o projeto</option>
          <option>Demonstração do MVP</option>
          <option>Módulo Trabalhista</option>
          <option>Parcerias e colaboração</option>
          <option>Outro assunto</option>
        </select>
      </label>
      <label>
        Sua mensagem
        <textarea
          name="mensagem"
          placeholder="Conte um pouco sobre o seu interesse no DocRisk AI…"
          rows={5}
          required
          maxLength={3000}
        />
      </label>
      <p className="form-note">
        Este formulário apenas prepara o texto. Nenhuma informação é enviada ou
        armazenada.
      </p>
      <button className="button" type="submit">
        Preparar mensagem <ArrowUpRight size={18} />
      </button>
      {brief && (
        <div className="prepared-message" role="status">
          <h3>Mensagem preparada</h3>
          <textarea
            aria-label="Mensagem preparada para copiar"
            value={brief}
            readOnly
            rows={8}
          />
          <button className="button secondary" type="button" onClick={copy}>
            {copied ? <Check size={17} /> : <Copy size={17} />}{" "}
            {copied ? "Mensagem copiada" : "Copiar mensagem"}
          </button>
          <small>
            Se a cópia automática não estiver disponível, selecione e copie o
            texto acima.
          </small>
        </div>
      )}
    </form>
  );
}
