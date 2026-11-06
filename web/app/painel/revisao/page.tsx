"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import {
  AnalysisBadge,
  DocumentBadge,
  EmptyState,
  ErrorState,
  IssueBadge,
  LoadingState,
  PageIntro,
} from "@/components/workspace-parts";
import {
  formatDate,
  formatHours,
  issueCategoryLabels,
  pageList,
  typeLabels,
  type Analysis,
  type Doc,
  type Issue,
} from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Filtro = "todas" | "documentos" | "divergencias" | "pendencias";

const PENDENCIAS_ABERTAS = ["ABERTA", "NOTIFICADA", "REENVIADA", "REABERTA"];

function exigeAtencao(a: Analysis): boolean {
  return a.status === "REVISAO_HUMANA" ||
    a.status === "BLOQUEADA_PENDENCIA" ||
    (a.status === "ANALISADA" && (
      a.resultado.tipo === "DIVERGENCIA_A_VERIFICAR" ||
      a.resultado.tipo === "DADOS_INSUFICIENTES"
    ));
}

/**
 * Uma fila por contrato que reúne revisão documental, achados das conciliações
 * e pendências, sem alterar os endpoints nem inventar ações de aprovação.
 */
export default function ExceptionsQueue() {
  const { contract } = useSession();
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const revisoes = useApi<Doc[]>("/api/review-queue");
  const conciliacoes = useApi<Analysis[]>("/api/analyses");
  const issues = useApi<Issue[]>("/api/issues");

  const loading = revisoes.loading || conciliacoes.loading || issues.loading;
  const error = revisoes.error ?? conciliacoes.error ?? issues.error;

  const docs = (revisoes.data ?? []).filter((d) => !contract || d.contract_id === contract);
  const analises = (conciliacoes.data ?? [])
    .filter((a) => (!contract || a.contract_id === contract) && exigeAtencao(a));
  const pendencias = (issues.data ?? [])
    .filter((i) => (!contract || i.contract_id === contract) && PENDENCIAS_ABERTAS.includes(i.status));
  const total = docs.length + analises.length + pendencias.length;

  const mostrar = (categoria: Filtro) => filtro === "todas" || filtro === categoria;
  const recarregar = () => {
    void revisoes.reload();
    void conciliacoes.reload();
    void issues.reload();
  };

  return (
    <>
      <PageIntro
        eyebrow="TRATAMENTO DE EXCEÇÕES"
        title="Fila de Exceções"
        description="Revise documentos incertos, confira divergências de horas extras e acompanhe pendências da fornecedora. Uma divergência é um indício a verificar, não uma irregularidade comprovada."
      />
      <div className="list-toolbar">
        <div className="segmented" role="group" aria-label="Filtrar tipos de exceção">
          {([
            ["todas", "Todas", total],
            ["documentos", "Revisão documental", docs.length],
            ["divergencias", "Conciliações", analises.length],
            ["pendencias", "Pendências", pendencias.length],
          ] as const).map(([chave, rotulo, quantidade]) => (
            <button
              key={chave}
              type="button"
              aria-pressed={filtro === chave}
              className={filtro === chave ? "selected" : ""}
              onClick={() => setFiltro(chave)}
            >
              {rotulo} ({quantidade})
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={recarregar} />
      ) : total === 0 ? (
        <EmptyState
          title="Nenhuma exceção neste contrato."
          text="As situações que exigirem acompanhamento humano serão exibidas aqui."
        />
      ) : (
        <>
          {mostrar("documentos") && (
            <section className="workspace-card">
              <div className="card-title"><h2>Revisão documental ({docs.length})</h2></div>
              {docs.length === 0 ? (
                <p className="muted">Nenhum documento aguardando revisão.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Documento</th>
                        <th>Identificação</th>
                        <th>Motivo da revisão</th>
                        <th>Situação</th>
                        <th><span className="sr-only">Ações</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {docs.map((d) => (
                        <tr key={d.id}>
                          <td>#{d.id}<small className="muted block">Lote #{d.batch_id} · {pageList(d.paginas)}</small></td>
                          <td>
                            {typeLabels[d.tipo] ?? d.tipo}
                            <small className="muted block">{d.worker_id ?? "Sem trabalhador"} · {d.competencia ?? "Sem competência"}</small>
                            <small className="muted block">Confiança: {d.confianca == null ? "—" : Math.round(d.confianca * 100) + "%"}</small>
                          </td>
                          <td className="review-reason-cell">{(d.motivos_revisao ?? []).join("; ") || "Conferência necessária"}</td>
                          <td><DocumentBadge status={d.status} /></td>
                          <td>
                            <Link className="table-action" href={"/painel/revisao/detalhe?id=" + d.id}>
                              Conferir <ArrowUpRight size={14} />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
          {mostrar("divergencias") && (
            <section aria-label="Exceções das conciliações">
              <h2>Conciliações que exigem atenção ({analises.length})</h2>
              {analises.length === 0 ? (
                <p className="muted">Nenhuma divergência ou análise bloqueada encontrada.</p>
              ) : (
                <div className="analysis-list">
                  {analises.map((a) => (
                    <article key={a.id} className="workspace-card analysis-card">
                      <header>
                        <div>
                          <span className="eyebrow">{a.contract_id} · COMPETÊNCIA {a.competencia}</span>
                          <h2>Trabalhador {a.worker_id}</h2>
                        </div>
                        <AnalysisBadge status={a.status} result={a.resultado.tipo} />
                      </header>
                      {a.status === "ANALISADA" && (
                        <div className="hours-comparison">
                          <div><span>Ponto</span><strong>{formatHours(a.resultado.horas_ponto)}</strong></div>
                          <div><span>Holerite</span><strong>{formatHours(a.resultado.horas_folha)}</strong></div>
                          <div><span>Diferença</span><strong>{formatHours(a.resultado.diferenca_h)}</strong></div>
                        </div>
                      )}
                      <p>{a.resultado.detalhe}</p>
                      <p className="muted">{a.resultado.comprovante.observacao}</p>
                      <details>
                        <summary>Evidências utilizadas ({a.insumos.length})</summary>
                        <ul className="plain-list">
                          {a.insumos.map((i) => (
                            <li key={i.doc_id}>
                              <Link href={"/painel/documentos/detalhe?id=" + i.doc_id}>
                                {typeLabels[i.tipo] ?? i.tipo} #{i.doc_id}
                              </Link>
                              {" · versão " + i.versao + " · lote #" + i.batch_id + " · páginas " + i.paginas.join(", ")}
                            </li>
                          ))}
                        </ul>
                      </details>
                      <small className="muted">Regra {a.regra_versao} · calculada em {formatDate(a.created_at)}</small>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
          {mostrar("pendencias") && (
            <section aria-label="Pendências documentais" className="workspace-card">
              <div className="card-title"><h2>Pendências da fornecedora ({pendencias.length})</h2></div>
              {pendencias.length === 0 ? (
                <p className="muted">Nenhuma pendência documental em aberto.</p>
              ) : (
                <div className="issue-list">
                  {pendencias.map((i) => (
                    <article key={i.id} className="workspace-card issue-card">
                      <header>
                        <div>
                          <span className="eyebrow">PENDÊNCIA #{i.id} · {issueCategoryLabels[i.categoria] ?? i.categoria}</span>
                          <h2>{i.worker_id ?? "Trabalhador não identificado"} · {i.competencia ?? "Sem competência"}</h2>
                        </div>
                        <IssueBadge status={i.status} />
                      </header>
                      <dl className="detail-list">
                        <dt>Motivo</dt><dd>{i.motivo}</dd>
                        <dt>Ação solicitada</dt><dd>{i.acao}</dd>
                        <dt>Evidência</dt><dd>{i.evidencia ?? "—"}</dd>
                        <dt>Prazo</dt><dd>{i.prazo ? new Date(i.prazo.slice(0, 10) + "T12:00:00").toLocaleDateString("pt-BR") : "—"}</dd>
                      </dl>
                      {i.document_id != null && (
                        <Link className="text-link" href={"/painel/documentos/detalhe?id=" + i.document_id}>
                          Consultar documento <ArrowUpRight size={14} />
                        </Link>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
