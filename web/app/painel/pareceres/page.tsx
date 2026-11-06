"use client";
import { useEffect, useRef, useState } from "react";
import { FilePlus2, Send } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { ReportPdfButton } from "@/components/report-pdf-button";
import { ReportView } from "@/components/report-view";
import { EmptyState, ErrorState, LoadingState, Notice, PageIntro } from "@/components/workspace-parts";
import { api, formatDate, reportStatusLabels, type Report, type ReportContent, type ReportCreateInput } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function ReportsPage() {
  const { contract, contracts, isDemo } = useSession();
  const { data, error, loading, reload } = useApi<Report[]>("/api/reports");
  const [competencia, setCompetencia] = useState("10/2026");
  const [observacoes, setObservacoes] = useState("");
  const [recomendacoes, setRecomendacoes] = useState("");
  const creating = useRef(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const rows = (data ?? []).filter((r) => !contract || r.contract_id === contract);

  async function create() {
    if (creating.current) return;
    creating.current = true;
    setBusy(true);
    setFeedback(null);
    try {
      const payload: ReportCreateInput = { contract_id: contract, competencia, observacoes, recomendacoes };
      const r = await api<Report>("/api/reports", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSelected(r.id);
      setFeedback({ tone: "success", text: `Rascunho v${r.versao} criado. Confira a prévia antes de publicar.` });
      await reload();
    } catch (err) {
      setFeedback({ tone: "error", text: err instanceof Error ? err.message : "Falha ao criar rascunho" });
    } finally {
      creating.current = false;
      setBusy(false);
    }
  }

  return (
    <>
      <PageIntro
        eyebrow="PARECERES"
        title="Revisado por pessoas, publicado com versão."
        description="O rascunho usa as análises atuais. A publicação grava um retrato imutável; correções geram nova versão e a anterior fica marcada como substituída. A contratante só vê o publicado."
      />
      {isDemo && <Notice>Exemplo fictício: criar ou publicar pareceres exige um ambiente operacional e aprovação humana.</Notice>}
      {feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}
      <section className="workspace-card">
        <h2>Novo rascunho</h2>
        <div className="inline-form">
          <label className="filter-label">
            Contrato
            <input value={contracts.find((c) => c.id === contract)?.nome ?? contract} disabled />
          </label>
          <label className="filter-label">
            Competência
            <input value={competencia} onChange={(e) => setCompetencia(e.target.value)} pattern="(0[1-9]|1[0-2])/\d{4}" />
          </label>
          <label className="filter-label grow">
            Observações internas
            <input value={observacoes} onChange={(e) => setObservacoes(e.target.value)} maxLength={2000} />
          </label>
          <label className="filter-label grow">
            Recomendações ao cliente
            <textarea value={recomendacoes} onChange={event => setRecomendacoes(event.target.value)} maxLength={4000} rows={3} placeholder="Uma orientação por linha. Se vazio, confira as sugestões na prévia." />
          </label>
          <button className="button" disabled={isDemo || busy || !contract || !/^(0[1-9]|1[0-2])\/\d{4}$/.test(competencia)} onClick={create}>
            <FilePlus2 size={16} /> Criar rascunho
          </button>
        </div>
      </section>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhum parecer." text="Crie um rascunho para a competência desejada." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Parecer</th>
                <th>Competência</th>
                <th>Situação</th>
                <th>Publicado em</th>
                <th><span className="sr-only">Ações</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={selected === r.id ? "selected" : ""}>
                  <td>#{r.id} · versão {r.versao}</td>
                  <td>{r.competencia}</td>
                  <td>{reportStatusLabels[r.status]}</td>
                  <td>{formatDate(r.publicado_em)}</td>
                  <td>
                    <button className="table-action" onClick={() => setSelected(r.id)}>
                      {r.status === "RASCUNHO" ? "Ver prévia" : "Ver parecer"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selected !== null && rows.some(row => row.id === selected) && (
        <ReportPanel
          key={selected}
          id={selected}
          onPublished={() => {
            setFeedback({ tone: "success", text: "Parecer publicado. A contratante já pode consultá-lo." });
            void reload();
          }}
        />
      )}
    </>
  );
}

function ReportPanel({ id, onPublished }: { id: number; onPublished: () => void }) {
  const { isDemo } = useSession();
  const { data, error, loading, reload } = useApi<Report>(`/api/reports/${id}/preview`);
  const [busy, setBusy] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [recommendations, setRecommendations] = useState("");
  const acting = useRef(false);
  useEffect(() => { setConfirmed(false); setRecommendations(data?.recomendacoes ?? ""); }, [data?.conteudo_sha256,data?.recomendacoes]);
  if (loading) return <LoadingState text="Montando a prévia…" />;
  if (error || !data) return <ErrorState message={error ?? "Parecer não encontrado"} onRetry={reload} />;
  const content = data.conteudo_json as ReportContent;
  const draft = data.status === "RASCUNHO";
  const previewHash = data.conteudo_sha256;
  const dirty = recommendations.trim() !== (data.recomendacoes ?? "").trim();
  async function act(kind: "publish" | "edit") {
    if (acting.current || (kind === "publish" && (!confirmed || dirty))) return;
    acting.current = true; setBusy(true); setPublishError(null);
    try {
      if (!previewHash) throw new Error("Atualize a prévia antes de continuar.");
      await api(`/api/reports/${id}${kind === "publish" ? "/publish" : ""}`, {
        method: kind === "publish" ? "POST" : "PATCH",
        body: JSON.stringify({ conteudo_sha256: previewHash,...(kind === "edit" ? { recomendacoes: recommendations } : {}) }),
      });
      setConfirmed(false);
      if (kind === "publish") onPublished();
      await reload();
    } catch (reason) { setConfirmed(false); setPublishError(reason instanceof Error ? reason.message : "Falha ao atualizar parecer"); }
    finally { acting.current = false; setBusy(false); }
  }
  return <section className="workspace-card">
    <div className="card-title"><h2>Parecer #{data.id} · versão {data.versao} · {reportStatusLabels[data.status]}</h2>
      <ReportPdfButton report={data} disabled={busy || dirty} />
    </div>
    {draft && <section className="report-editorial">
      <label className="filter-label">Recomendações ao cliente (visíveis no parecer)
        <textarea rows={4} maxLength={4000} value={recommendations} disabled={isDemo || busy} placeholder="Uma orientação por linha. Se vazio, use as sugestões exibidas na prévia." onChange={event => { setRecommendations(event.target.value); setConfirmed(false); }} />
      </label>
      <button type="button" className="button secondary" disabled={isDemo || busy || !dirty} onClick={() => void act("edit")}>Atualizar recomendações</button>
    </section>}
    {publishError && <Notice tone="error">{publishError} <button type="button" className="table-action" disabled={busy} onClick={() => { setConfirmed(false); void reload(); }}>Atualizar prévia</button></Notice>}
    {content && "resumo" in content ? <ReportView content={content} draft={draft} report={data} /> : <EmptyState title="Sem conteúdo." text="Este parecer não possui conteúdo gravado." />}
    {draft && <div className="report-publish-check">
      <label><input type="checkbox" checked={confirmed} disabled={isDemo || busy || dirty} onChange={event => setConfirmed(event.target.checked)} /> Conferi autoria, responsável, recomendações, resultados e limitações desta prévia.</label>
      {dirty && <p role="status">Atualize as recomendações e confira a nova prévia antes de publicar.</p>}
      <button type="button" className="button" disabled={isDemo || busy || dirty || !confirmed || !previewHash} onClick={() => void act("publish")}><Send size={16} />{busy ? "Atualizando…" : "Publicar"}</button>
    </div>}
  </section>;
}
