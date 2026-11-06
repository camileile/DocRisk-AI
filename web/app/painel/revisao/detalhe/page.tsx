"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Check, Merge, Scissors, Undo2 } from "lucide-react";
import {
  DocumentBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageImage,
  PageIntro,
} from "@/components/workspace-parts";
import { api, formatHours, pageList, typeLabels, type DocDetail } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { useSession } from "@/components/demo-provider";

const FOCO = ["ESPELHO_PONTO", "HOLERITE", "COMPROVANTE_PAGAMENTO"];

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ReviewDetail />
    </Suspense>
  );
}

function ReviewDetail() {
  const { isDemo } = useSession();
  const id = useSearchParams().get("id");
  const router = useRouter();
  const { data: d, error, loading, reload } = useApi<DocDetail>(id ? `/api/documents/${id}` : null);
  const workers = useApi<{ id: string; nome: string }[]>(d ? `/api/contracts/${d.contract_id}/workers` : null);
  const [tipo, setTipo] = useState("");
  const [worker, setWorker] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [splitAfter, setSplitAfter] = useState(1);
  const [motivo, setMotivo] = useState("");
  const [acao, setAcao] = useState("Reenviar o documento completo e legível.");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!d) return;
    setTipo(d.tipo === "DESCONHECIDO" ? "" : d.tipo);
    setWorker(d.worker_id ?? "");
    setCompetencia(d.competencia ?? "");
    setSplitAfter(1);
  }, [d]);

  if (!id) return <EmptyState title="Documento não informado." text="Abra um item da fila de revisão." />;
  if (loading) return <LoadingState />;
  if (error || !d) return <ErrorState message={error ?? "Documento não encontrado"} onRetry={reload} />;
  const reviewable = d.status === "REVISAO_HUMANA" || d.status === "PENDENTE_CORRECAO";
  const foco = FOCO.includes(tipo);

  async function act(payload: Record<string, unknown>, success: string, leave = false) {
    setBusy(true);
    setFeedback(null);
    try {
      await api(`/api/documents/${d!.id}/review`, { method: "PATCH", body: JSON.stringify(payload) });
      setFeedback({ tone: "success", text: success });
      if (leave) router.push("/painel/revisao");
      else void reload();
    } catch (err) {
      setFeedback({ tone: "error", text: err instanceof Error ? err.message : "Falha na ação" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Link href="/painel/revisao" className="batch-back">
        <ArrowLeft size={16} /> Fila de exceções
      </Link>
      <PageIntro
        eyebrow={`DOCUMENTO #${d.id} · LOTE #${d.batch_id} · ${pageList(d.paginas)}`}
        title={`Conferir: ${typeLabels[d.tipo] ?? d.tipo}`}
        description={(d.motivos_revisao ?? []).join("; ") || "Sem motivos de revisão registrados."}
        action={<DocumentBadge status={d.status} />}
      />
      {isDemo && <Notice>Esta é uma fila ilustrativa; alterações de classificação, divisão, união e correção estão desativadas.</Notice>}
      {feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}
      <div className="review-workspace">
        <div className="review-pages">
          {d.paginas_detalhe.map((p, i) => (
            <figure key={p.page_id} className="workspace-card">
              <figcaption>Página {i + 1} do documento · página {p.ordem} do lote</figcaption>
              <PageImage pageId={p.page_id} alt={`Página ${p.ordem} do lote`} />
              <details>
                <summary>Texto lido (OCR)</summary>
                <pre className="ocr-text">{p.texto || "Nenhum texto lido."}</pre>
              </details>
            </figure>
          ))}
        </div>
        <aside className="review-actions">
          <section className="workspace-card">
            <h2>Classificação</h2>
            <p className="muted">
              Campos lidos: horas extras {formatHours(d.campos.horas_extras_h)}
              {d.campos.horas_extras_valor != null ? " · valor de horas extras informado em R$" : ""}
            </p>
            <label className="filter-label">
              Tipo
              <select value={tipo} onChange={(e) => setTipo(e.target.value)} disabled={!reviewable}>
                <option value="">Selecione…</option>
                {Object.entries(typeLabels)
                  .filter(([k]) => k !== "DESCONHECIDO")
                  .map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
              </select>
            </label>
            <label className="filter-label">
              Trabalhador {foco && "*"}
              <select value={worker} onChange={(e) => setWorker(e.target.value)} disabled={!reviewable}>
                <option value="">{foco ? "Selecione…" : "Não se aplica"}</option>
                {(workers.data ?? []).map((w) => (
                  <option key={w.id} value={w.id}>{w.id} · {w.nome}</option>
                ))}
              </select>
            </label>
            <label className="filter-label">
              Competência (MM/AAAA) {foco && "*"}
              <input
                value={competencia}
                onChange={(e) => setCompetencia(e.target.value)}
                placeholder="10/2026"
                pattern="(0[1-9]|1[0-2])/\d{4}"
                disabled={!reviewable}
              />
            </label>
            <button
              className="button"
              disabled={isDemo || busy || !reviewable || !tipo || (foco && (!worker || !competencia))}
              onClick={() =>
                act(
                  { acao: "aprovar", tipo, trabalhador_id: worker || null, competencia: competencia || null },
                  "Documento aprovado. A conciliação do trabalhador foi recalculada.",
                  true,
                )
              }
            >
              <Check size={16} /> Aprovar classificação
            </button>
          </section>
          <section className="workspace-card">
            <h2>Agrupamento</h2>
            {d.paginas.length > 1 && (
              <div className="inline-form">
                <label className="filter-label">
                  Dividir após a página
                  <select value={splitAfter} onChange={(e) => setSplitAfter(Number(e.target.value))}>
                    {d.paginas.slice(0, -1).map((_, i) => (
                      <option key={i} value={i + 1}>{i + 1}</option>
                    ))}
                  </select>
                </label>
                <button
                  className="button secondary"
                  disabled={isDemo || busy}
                  onClick={() => act({ acao: "dividir", apos_pagina: splitAfter }, "Documento dividido em dois.", true)}
                >
                  <Scissors size={16} /> Dividir
                </button>
              </div>
            )}
            <button
              className="button secondary"
              disabled={isDemo || busy}
              onClick={() => act({ acao: "unir_proximo" }, "Documento unido ao seguinte do lote.")}
            >
              <Merge size={16} /> Unir ao próximo documento do lote
            </button>
          </section>
          <section className="workspace-card">
            <h2>Devolver à fornecedora</h2>
            <p className="muted">Use só para erro objetivo (ilegível, incompleto). Não descreva suspeita trabalhista.</p>
            <label className="filter-label">
              Motivo
              <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={2} maxLength={1000} />
            </label>
            <label className="filter-label">
              Ação solicitada
              <textarea value={acao} onChange={(e) => setAcao(e.target.value)} rows={2} maxLength={500} />
            </label>
            <button
              className="button secondary"
              disabled={isDemo || busy || !motivo.trim() || !acao.trim()}
              onClick={() =>
                act(
                  { acao: "solicitar_correcao", motivo: motivo.trim(), acao_solicitada: acao.trim() },
                  "Pendência criada e enviada à fornecedora.",
                  true,
                )
              }
            >
              <Undo2 size={16} /> Solicitar correção
            </button>
          </section>
        </aside>
      </div>
    </>
  );
}
