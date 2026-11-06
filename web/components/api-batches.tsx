"use client";

import { useEffect, useState } from "react";
import { CircleAlert, Clock3, CheckCheck, Package, RefreshCw, Search, FileText, ChevronDown } from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { PageIntro, EmptyState } from "@/components/workspace-parts";
import { BatchBadge } from "@/components/batch-badge";
import { batchLabels } from "@/lib/batches";
import { fetchApiBatch, fetchApiBatchDocuments, formatApiDate, type ApiBatch, type ApiDocument, type ApiBatchStatus } from "@/lib/api-client";
import { useApiBatches } from "@/hooks/use-api-batches";

function ApiBatchDetails({ batchId, contractId, token, analyst }: {
  batchId: number; contractId: string; token: string; analyst: boolean;
}) {
  const [detail, setDetail] = useState<{ batch: ApiBatch; documents: ApiDocument[] } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setDetail(null);
    setError("");
    setLoading(true);
    Promise.all([
      fetchApiBatch(token, batchId, controller.signal),
      fetchApiBatchDocuments(token, batchId, controller.signal),
    ]).then(([batch, documents]) => {
      if (active) setDetail({ batch, documents });
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Não foi possível consultar o lote.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [batchId, token]);

  if (loading) return <p role="status" className="api-status">Consultando lote e documentos…</p>;
  if (error) return <p role="alert" className="api-error">{error}</p>;
  if (!detail || detail.batch.contract_id !== contractId) return null;

  return (
    <section className="api-batch-detail" aria-label={"Detalhes do lote " + batchId}>
      <div className="api-detail-summary">
        <div>
          <strong>Lote #{detail.batch.id} · {detail.batch.filename}</strong>
          <p>Contrato {detail.batch.contract_id} · {detail.batch.tipo_arquivo} · {detail.batch.total_pages} página(s)</p>
        </div>
        <BatchBadge status={detail.batch.status} />
      </div>
      {detail.batch.erro && (
        <p className="api-error"><CircleAlert size={15} /> Falha registrada pelo processamento: {detail.batch.erro}</p>
      )}
      {detail.batch.status !== "CONCLUIDO" && (
        <p className="api-status">Os documentos podem ainda não estar consolidados enquanto o processamento não termina.</p>
      )}
      <div className="api-document-heading">
        <FileText size={17} />
        <h3>Documentos vinculados ({detail.documents.length})</h3>
      </div>
      {detail.documents.length ? (
        <div className="api-document-list">
          {detail.documents.map((document) => (
            <article className="api-document-row" key={document.id}>
              <div>
                <strong>Documento #{document.id} · {document.tipo}</strong>
                <small>{document.worker_id ? "Trabalhador " + document.worker_id : "Trabalhador não identificado"} · {document.competencia ?? "Competência não identificada"} · versão {document.versao}</small>
                {document.motivos_pendencia?.length > 0 && (
                  <p>Orientação: {document.motivos_pendencia.join("; ")}</p>
                )}
                {analyst && document.motivos_revisao?.length ? (
                  <p className="api-internal-note">Revisão interna: {document.motivos_revisao.join("; ")}</p>
                ) : null}
              </div>
              <span className="api-doc-status">{document.status === "EM_ANALISE" ? "Em análise" : document.status.replaceAll("_", " ")}</span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="Nenhum documento consolidado" text="O backend ainda não retornou documentos vinculados a este lote." />
      )}
    </section>
  );
}

export function ApiBatches() {
  const { apiSession, contract } = useDemo();
  // Este componente só é montado quando existe uma sessão F1.
  const token = apiSession?.token ?? "";
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  const [selected, setSelected] = useState<number | null>(null);
  const { items, loading, error, refresh } = useApiBatches(token);
  const allowed = new Set(apiSession?.contracts.map((item) => item.id) ?? []);
  // Dupla proteção visual: autorização obrigatória continua no backend.
  const context = items.filter((batch) => batch.contract_id === contract && allowed.has(batch.contract_id));
  const rows = context.filter((batch) =>
    (status === "todos" || batch.status === status) &&
    (("#" + batch.id + " " + batch.filename + " " + batch.tipo_arquivo)
      .toLocaleLowerCase("pt-BR").includes(query.trim().toLocaleLowerCase("pt-BR")))
  );

  if (!apiSession) return null;

  return (
    <>
      <PageIntro
        eyebrow="API F1 · LOTES REAIS DE TESTE"
        title="Envios consultados no backend."
        description="Consulte os lotes autorizados pela API. Os dados abaixo são recebidos do SQLite de testes e não dos exemplos fixos do frontend."
        action={
          <button type="button" className="button secondary" onClick={() => { setSelected(null); refresh(); }} disabled={loading}>
            <RefreshCw size={16} /> {loading ? "Atualizando…" : "Atualizar lotes"}
          </button>
        }
      />
      <div className="stat-grid">
        {[
          { icon: Package, label: "Lotes no contrato", value: context.length, tone: "purple" },
          { icon: Clock3, label: "Recebidos ou processando", value: context.filter(b => b.status === "RECEBIDO" || b.status === "PROCESSANDO").length, tone: "purple" },
          { icon: CheckCheck, label: "Processamento concluído", value: context.filter(b => b.status === "CONCLUIDO").length, tone: "green" },
          { icon: CircleAlert, label: "Falha técnica", value: context.filter(b => b.status === "FALHA_PROCESSAMENTO").length, tone: "amber" },
        ].map(({ icon: Icon, label, value, tone }) => (
          <article className="stat-card" key={label}>
            <div className={"stat-icon " + tone}><Icon size={20} /></div>
            <strong>{loading ? "—" : value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <div className="inline-info">
        <CircleAlert size={18} />
        <p>“Concluído” significa apenas que o processamento documental terminou. A conciliação trabalhista da F3 pode ainda não existir. Clique em “Atualizar lotes” para obter os estados mais recentes; não existe atualização automática neste estágio.</p>
      </div>
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input aria-label="Buscar lotes da API" placeholder="ID, nome do arquivo ou tipo…"
              value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <label className="filter-label">
            Processamento
            <select aria-label="Filtrar processamento da API" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="todos">Todas as situações</option>
              {(Object.keys(batchLabels) as ApiBatchStatus[]).map((key) => <option key={key} value={key}>{batchLabels[key]}</option>)}
            </select>
          </label>
        </div>
        {loading && <p className="api-status" role="status">Consultando lotes na API…</p>}
        {error && <p className="api-error" role="alert">{error}</p>}
        {!loading && !error && (
          <>
            <div className="list-summary" aria-live="polite">{rows.length} lote(s) encontrado(s) na API</div>
            {rows.length ? (
              <div className="table-scroll">
                <table className="data-table">
                  <thead><tr><th scope="col">Lote / arquivo</th><th scope="col">Recebimento (servidor)</th><th scope="col">Processamento</th><th scope="col">Páginas</th><th scope="col">Ação</th></tr></thead>
                  <tbody>
                    {rows.map((batch) => (
                      <tr key={batch.id}>
                        <td><strong>#{batch.id}</strong><small>{batch.filename}</small><small>{batch.tipo_arquivo}</small></td>
                        <td>{formatApiDate(batch.created_at)}</td>
                        <td><BatchBadge status={batch.status} /></td>
                        <td>{batch.total_pages}</td>
                        <td>
                          <button type="button" className="table-action" aria-expanded={selected === batch.id}
                            onClick={() => setSelected(selected === batch.id ? null : batch.id)}>
                            {selected === batch.id ? "Fechar" : "Ver documentos"} <ChevronDown size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="Nenhum lote neste contrato" text="O backend não retornou lotes para o contrato autorizado ou os filtros selecionados." />
            )}
            {selected !== null && rows.some(batch => batch.id === selected) && (
              <ApiBatchDetails key={selected} token={token} batchId={selected} contractId={contract}
                analyst={apiSession.user.papel === "ANALISTA_BH"} />
            )}
          </>
        )}
      </section>
    </>
  );
}
