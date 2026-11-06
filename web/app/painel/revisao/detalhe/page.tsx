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

const FOCO = ["ESPELHO_PONTO", "HOLERITE", "COMPROVANTE_PAGAMENTO"];

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ReviewDetail />
    </Suspense>
  );
}

function ReviewDetail() {
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
  const [aejHours, setAejHours] = useState("");
  const [aejJustification, setAejJustification] = useState("");

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

  async function approveAej() {
    setBusy(true);
    setFeedback(null);
    try {
      await api(`/api/documents/${d!.id}/aej-review`, {
        method: "PATCH",
        body: JSON.stringify({ horas_extras_h: Number(aejHours), justificativa: aejJustification.trim() }),
      });
      setFeedback({ tone: "success", text: "Horas confirmadas. A conciliação do trabalhador foi recalculada." });
      router.push("/painel/revisao");
    } catch (err) {
      setFeedback({ tone: "error", text: err instanceof Error ? err.message : "Falha ao revisar AEJ" });
    } finally {
      setBusy(false);
    }
  }

  async function mapAejWorker() {
    if (!worker) return;
    setBusy(true);
    setFeedback(null);
    try {
      await api(`/api/contracts/${d!.contract_id}/aej-mappings/${d!.aej!.worker_link_id}`, {
        method: "PUT", body: JSON.stringify({ worker_id: worker }),
      });
      setFeedback({ tone: "success", text: "Vínculo associado. Documentos AEJ pendentes foram recalculados." });
      void reload();
    } catch (err) {
      setFeedback({ tone: "error", text: err instanceof Error ? err.message : "Falha ao mapear vínculo" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Link href="/painel/revisao" className="batch-back">
        <ArrowLeft size={16} /> Fila de revisão
      </Link>
      <PageIntro
        eyebrow={`DOCUMENTO #${d.id} · LOTE #${d.batch_id} · ${d.aej ? `AEJ vínculo ${d.aej.worker_link_id}` : pageList(d.paginas)}`}
        title={`Conferir: ${typeLabels[d.tipo] ?? d.tipo}`}
        description={(d.motivos_revisao ?? []).join("; ") || "Sem motivos de revisão registrados."}
        action={<DocumentBadge status={d.status} />}
      />
      {feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}
      {d.aej ? (
        <div className="dashboard-grid">
          <section className="workspace-card">
            <h2>Origem e cálculo AEJ</h2>
            <dl className="detail-list">
              <dt>Vínculo no AEJ</dt><dd>{d.aej.worker_link_id}</dd>
              <dt>Estado do cálculo</dt><dd>{d.aej.calculation_status}</dd>
              <dt>Método</dt><dd>{d.aej.method}</dd>
              <dt>Assinatura P7S</dt><dd>Não validada</dd>
            </dl>
            {d.aej.validation_warnings.length > 0 && (
              <details>
                <summary>Avisos de validação do arquivo</summary>
                <ul>{d.aej.validation_warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>
              </details>
            )}
            {!d.worker_id && (
              <>
                <label className="filter-label">
                  Trabalhador correspondente
                  <select value={worker} onChange={(event) => setWorker(event.target.value)}>
                    <option value="">Selecione o trabalhador…</option>
                    {(workers.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.id} · {item.nome}</option>)}
                  </select>
                </label>
                <button className="button secondary" disabled={busy || !worker} onClick={mapAejWorker}>
                  Associar vínculo AEJ
                </button>
              </>
            )}
            {d.aej.warnings.length > 0 && <ul>{d.aej.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>}
            {d.status === "REVISAO_HUMANA" && d.worker_id ? (
              <>
                <label className="filter-label">
                  Horas extras observadas após conferência manual
                  <input type="number" min="0" step="0.01" value={aejHours}
                    onChange={(event) => setAejHours(event.target.value)} />
                </label>
                <label className="filter-label">
                  Justificativa da conferência
                  <textarea rows={3} maxLength={500} value={aejJustification}
                    onChange={(event) => setAejJustification(event.target.value)} />
                </label>
                <button className="button" disabled={busy || !aejHours || !aejJustification.trim()} onClick={approveAej}>
                  <Check size={16} /> Confirmar horas conferidas
                </button>
              </>
            ) : d.status === "APTO" ? (
              <p className="muted">Horas derivadas confirmadas: {formatHours(d.campos.horas_extras_h)}.</p>
            ) : null}
            <p className="muted">O arquivo AEJ original e todas as linhas permanecem preservados no lote.</p>
          </section>
          <section className="workspace-card">
            <h2>Marcações e origem</h2>
            {d.aej.days.map((day) => (
              <div key={day.date} className="aej-day">
                <h3>{day.date} · horário {day.schedule_code ?? "não identificado"}</h3>
                <p className="muted">
                  Jornada contratual: {day.contract_minutes ?? "—"} min · observada: {day.worked_minutes ?? "—"} min ·
                  excedente diário: {day.observed_daily_excess_minutes ?? "não calculado"} min
                </p>
                <ul className="plain-list">
                  {[...day.markings, ...day.excluded_markings].sort((a, b) => a.line_number - b.line_number).map((mark) => (
                    <li key={mark.line_number}>
                      Linha {mark.line_number} · {mark.at} · {mark.type === "D" ? "desconsiderada" : mark.type === "E" ? "entrada" : "saída"}
                      {mark.type !== "D" ? ` · fonte ${mark.source} · par ${mark.sequence}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
        </div>
      ) : <div className="review-workspace">
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
              disabled={busy || !reviewable || !tipo || (foco && (!worker || !competencia))}
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
                  disabled={busy}
                  onClick={() => act({ acao: "dividir", apos_pagina: splitAfter }, "Documento dividido em dois.", true)}
                >
                  <Scissors size={16} /> Dividir
                </button>
              </div>
            )}
            <button
              className="button secondary"
              disabled={busy}
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
              disabled={busy || !motivo.trim() || !acao.trim()}
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
      </div>}
    </>
  );
}
