"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowUpRight, Download, RotateCcw } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import {
  BatchBadge,
  DocumentBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageImage,
  PageIntro,
} from "@/components/workspace-parts";
import { api, downloadBatchSource, formatDate, pageList, typeLabels, type Batch, type Doc } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <BatchDetail />
    </Suspense>
  );
}

function BatchDetail() {
  const id = useSearchParams().get("id");
  const { me } = useSession();
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [sourceBusy, setSourceBusy] = useState(false);
  const running = (b: Batch) => b.status === "RECEBIDO" || b.status === "PROCESSANDO";
  const batch = useApi<Batch>(id ? `/api/batches/${id}` : null, { pollMs: 2500, shouldPoll: running });
  const done = batch.data?.status === "CONCLUIDO";
  const docs = useApi<Doc[]>(id && done ? `/api/batches/${id}/documents` : null);

  if (!id) return <EmptyState title="Lote não informado." text="Abra um lote a partir da lista." />;
  if (batch.loading) return <LoadingState />;
  if (batch.error || !batch.data) return <ErrorState message={batch.error ?? "Lote não encontrado"} onRetry={batch.reload} />;
  const b = batch.data;
  const canReprocess = b.status === "FALHA_PROCESSAMENTO" && (me?.org_tipo === "BERNHOEFT" || me?.id === b.uploaded_by);

  async function reprocess() {
    try {
      await api(`/api/batches/${b.id}/reprocess`, { method: "POST" });
      setNotice({ tone: "success", text: "Lote reenfileirado. Páginas já lidas são reaproveitadas do cache." });
      void batch.reload();
    } catch (err) {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Falha ao reprocessar" });
    }
  }

  async function downloadSource() {
    setSourceBusy(true);
    try {
      await downloadBatchSource(b.id);
    } catch (err) {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Falha ao baixar arquivo original" });
    } finally {
      setSourceBusy(false);
    }
  }

  return (
    <>
      <Link href="/painel/lotes" className="batch-back">
        <ArrowLeft size={16} /> Lotes enviados
      </Link>
      <PageIntro
        eyebrow={`LOTE #${b.id}`}
        title={b.filename}
        description={b.tipo_arquivo === "AEJ"
          ? `AEJ estruturado · arquivo original preservado · recebido em ${formatDate(b.created_at)}${b.finished_at ? ` · concluído em ${formatDate(b.finished_at)}` : ""}`
          : `${b.total_pages} página(s) · ${b.tipo_arquivo} · recebido em ${formatDate(b.created_at)}${b.finished_at ? ` · concluído em ${formatDate(b.finished_at)}` : ""}`}
        action={<BatchBadge status={b.status} />}
      />
      {notice && <Notice tone={notice.tone}>{notice.text}</Notice>}
      {b.tipo_arquivo === "AEJ" && (me?.org_tipo === "BERNHOEFT" || me?.org_tipo === "FORNECEDORA") && (
        <button className="button secondary" disabled={sourceBusy} onClick={() => void downloadSource()}>
          <Download size={16} /> {sourceBusy ? "Baixando…" : "Baixar AEJ original"}
        </button>
      )}
      {running(b) && <Notice>Processando o lote… esta tela atualiza sozinha.</Notice>}
      {b.status === "FALHA_PROCESSAMENTO" && (
        <div className="batch-failure">
          <p>
            <strong>Falha técnica no processamento.</strong> {b.erro} A falha não é atribuída à fornecedora.
          </p>
          {canReprocess && (
            <button className="button secondary" onClick={reprocess}>
              <RotateCcw size={16} /> Reprocessar lote
            </button>
          )}
        </div>
      )}
      {done &&
        (docs.loading ? (
          <LoadingState text="Carregando documentos separados…" />
        ) : docs.error ? (
          <ErrorState message={docs.error} onRetry={docs.reload} />
        ) : (
          <section className="workspace-card">
            <div className="card-title">
              <h2>{docs.data?.length ?? 0} documento(s) separados</h2>
            </div>
            <div className="doc-grid">
              {(docs.data ?? []).map((d) => (
                <article key={d.id} className="doc-card">
                  {d.paginas[0] && <PageImage pageId={d.paginas[0].page_id} alt={`Primeira página do documento ${d.id}`} />}
                  <div>
                    <strong>{typeLabels[d.tipo] ?? d.tipo}</strong>
                    <small>
                      {d.aej ? `AEJ vínculo ${d.aej.worker_link_id} · ${d.aej.calculation_status} · assinatura não validada`
                        : `${pageList(d.paginas)} · ${d.worker_id ?? "sem trabalhador"} · ${d.competencia ?? "sem competência"}`}
                      {d.versao > 1 ? ` · versão ${d.versao}` : ""}
                    </small>
                    <DocumentBadge status={d.status} />
                    {d.motivos_pendencia.length > 0 && <small className="muted">{d.motivos_pendencia.join("; ")}</small>}
                    {d.motivos_revisao && d.motivos_revisao.length > 0 && (
                      <small className="muted">{d.motivos_revisao.join("; ")}</small>
                    )}
                    <Link className="table-action" href={`/painel/documentos/detalhe?id=${d.id}`}>
                      {d.aej ? "Ver cálculo e origem" : "Ver páginas e texto"} <ArrowUpRight size={14} />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
    </>
  );
}
