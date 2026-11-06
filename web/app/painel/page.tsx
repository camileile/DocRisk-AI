"use client";
import Link from "next/link";
import {
  Files,
  ShieldCheck,
  CircleAlert,
  UserCheck,
  ArrowRight,
  Upload,
  Check,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { documents, issues } from "@/lib/demo";
import {
  DocumentBadge,
  IssueBadge,
  PageIntro,
  EmptyState,
} from "@/components/workspace-parts";
export default function Dashboard() {
  const { role, contract, competence } = useDemo();
  const supplier = role === "OPERADOR_FORN";
  const docs = documents.filter(
    (d) => d.contract === contract && d.competence === competence,
  );
  const list = issues.filter(
    (d) => d.contract === contract && d.competence === competence,
  );
  const apt = docs.filter((d) => d.status === "APTO").length;
  const review = docs.filter((d) => d.status === "REVISAO_HUMANA").length;
  const correction = docs.filter(
    (d) => d.status === "PENDENTE_CORRECAO",
  ).length;
  return (
    <>
      <PageIntro
        eyebrow="SEU ESPAÇO DE TRABALHO"
        title="Clareza para o próximo passo."
        description={
          supplier
            ? "Acompanhe os documentos enviados e as correções do seu contrato."
            : "Acompanhe a situação documental e encontre o que precisa de atenção."
        }
        action={
          supplier ? (
            <Link className="button" href="/painel/envio">
              <Upload size={17} /> Preparar envio
            </Link>
          ) : (
            <Link className="button" href="/painel/documentos">
              Conferir documentos <ArrowRight size={17} />
            </Link>
          )
        }
      />
      <div className="stat-grid">
        {[
          {
            icon: Files,
            value: docs.length,
            label: "Documentos no contexto",
            tone: "purple",
          },
          {
            icon: ShieldCheck,
            value: apt,
            label: "Aptos documentalmente",
            tone: "green",
          },
          {
            icon: UserCheck,
            value: review,
            label: supplier ? "Em análise" : "Aguardando revisão",
            tone: "purple",
          },
          {
            icon: CircleAlert,
            value: list.filter((i) => i.status === "ABERTA").length,
            label: "Pendências abertas",
            tone: "amber",
          },
        ].map(({ icon: Icon, value, label, tone }) => (
          <article key={label} className="stat-card">
            <div className={`stat-icon ${tone}`}>
              <Icon size={20} />
            </div>
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="workspace-card">
          <div className="card-title">
            <h2>Situação documental</h2>
            <span>{docs.length} documentos</span>
          </div>
          {docs.length ? (
            <>
              <div
                className="document-bar"
                aria-label={`${apt} aptos, ${review} em ${supplier ? "análise" : "revisão"} e ${correction} pendentes de correção`}
              >
                <span
                  className="bar-success"
                  style={{ width: `${(apt / docs.length) * 100}%` }}
                />
                <span
                  className="bar-review"
                  style={{ width: `${(review / docs.length) * 100}%` }}
                />
                <span
                  className="bar-warning"
                  style={{ width: `${(correction / docs.length) * 100}%` }}
                />
              </div>
              <div className="chart-legend">
                <span>
                  <i className="bar-success" />
                  Aptos <b>{apt}</b>
                </span>
                <span>
                  <i className="bar-review" />
                  {supplier ? "Em análise" : "Revisão"} <b>{review}</b>
                </span>
                <span>
                  <i className="bar-warning" />
                  Correção <b>{correction}</b>
                </span>
              </div>
              <p className="card-footnote">
                Aptidão documental não equivale à conclusão da conciliação
                trabalhista.
              </p>
            </>
          ) : (
            <EmptyState
              title="Nenhum documento nesta competência"
              text="Selecione outra competência para explorar os exemplos."
            />
          )}
        </section>
        <section className="workspace-card next-step-card">
          <span className="eyebrow">CONTINUE POR AQUI</span>
          <h2>
            {supplier
              ? "Uma correção bem orientada."
              : "Cada evidência merece contexto."}
          </h2>
          <p>
            {supplier
              ? "Consulte a instrução da pendência antes de preparar o documento substituto."
              : "Confira a identificação do trabalhador e a competência antes de analisar os dados."}
          </p>
          <Link
            href={supplier ? "/painel/pendencias" : "/painel/documentos"}
            className="text-link"
          >
            {supplier ? "Ver pendências" : "Explorar documentos"}{" "}
            <ArrowRight size={16} />
          </Link>
        </section>
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Documentos do contexto</h2>
          <Link href="/painel/documentos">
            Ver todos <ArrowRight size={14} />
          </Link>
        </div>
        {docs.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Trabalhador</th>
                  <th>Competência</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {docs.slice(0, 4).map((d) => (
                  <tr key={d.id}>
                    <td>
                      <Link href="/painel/documentos">
                        <strong>{d.type}</strong>
                        <small>
                          {d.id} · {d.batch}
                        </small>
                      </Link>
                    </td>
                    <td>{d.worker}</td>
                    <td>{d.competence}</td>
                    <td>
                      <DocumentBadge status={d.status} supplier={supplier} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Ainda não há documentos"
            text="Os dados demonstrativos variam conforme o contrato e a competência."
          />
        )}
      </section>
      <section className="workspace-card attention-card">
        <div className="card-title">
          <h2>Pendências em acompanhamento</h2>
          <Link href="/painel/pendencias">
            Ver pendências <ArrowRight size={14} />
          </Link>
        </div>
        {list.length ? (
          list.map((issue) => (
            <div className="attention-row" key={issue.id}>
              <div className="attention-icon">
                {issue.status === "RESOLVIDA" ? (
                  <Check size={18} />
                ) : (
                  <CircleAlert size={18} />
                )}
              </div>
              <div>
                <strong>{issue.title}</strong>
                <span>
                  {issue.worker} · {issue.id}
                </span>
              </div>
              <IssueBadge status={issue.status} />
            </div>
          ))
        ) : (
          <EmptyState
            title="Sem pendências neste contexto"
            text="Selecione outro contrato ou competência para consultar os exemplos."
          />
        )}
      </section>
    </>
  );
}
