"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ReportPdfButton } from "./report-pdf-button";
import { ReportView } from "./report-view";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "./workspace-parts";
import { api, formatDate, type Report, type ReportContent } from "@/lib/api";
import type { ClientOverview } from "@/lib/client-portal";

const percent = (n: number | null) => n === null ? "—" : n.toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 });

// Cada consulta pertence ao seu filtro. Uma resposta atrasada não pode
// substituir os resultados da seleção mais recente.
function useClientQuery<T>(path: string) {
  const [state, setState] = useState<{ path: string; data?: T; error?: string }>({ path: "" });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ path });
    api<T>(path).then(
      (data) => { if (active) setState({ path, data }); },
      (err: unknown) => { if (active) setState({ path, error: err instanceof Error ? err.message : "Falha ao carregar." }); },
    );
    return () => { active = false; };
  }, [path, retry]);
  return {
    data: state.path === path ? state.data : undefined,
    error: state.path === path ? state.error : undefined,
    loading: state.path !== path || (!state.data && !state.error),
    reload: () => setRetry((n) => n + 1),
  };
}

export function ContractorPortal({ view }: { view: "overview" | "reports" }) {
  const params = useSearchParams();
  const router = useRouter();
  const supplier = params.get("fornecedora_id") ?? "";
  const contract = params.get("contract_id") ?? "";
  const month = params.get("competencia") ?? "";
  const filters = new URLSearchParams();
  if (supplier) filters.set("fornecedora_id", supplier);
  if (contract) filters.set("contract_id", contract);
  if (month) filters.set("competencia", month);
  const query = filters.size ? "?" + filters.toString() : "";
  const { data, error, loading, reload } = useClientQuery<ClientOverview>("/api/client/overview" + query);
  const base = view === "overview" ? "/contratante" : "/contratante/pareceres";
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(filters);
    if (value) next.set(key, value); else next.delete(key);
    if (key === "fornecedora_id") next.delete("contract_id");
    if (key !== "competencia") next.delete("competencia");
    router.replace(base + (next.size ? "?" + next.toString() : ""), { scroll: false });
  };
  const effectiveFilters = new URLSearchParams(filters);
  if (!month && data?.filtros.competencia_selecionada) effectiveFilters.set("competencia", data.filtros.competencia_selecionada);
  const reportQuery = effectiveFilters.size ? "?" + effectiveFilters.toString() : "";
  const reportLink = (id: string, reportId: number) => {
    const next = new URLSearchParams(filters);
    next.set("contract_id", id);
    if (data?.filtros.competencia_selecionada) next.set("competencia", data.filtros.competencia_selecionada);
    next.set("parecer_id", String(reportId));
    return "/contratante/pareceres?" + next.toString();
  };
  return <>
    <PageIntro eyebrow="PORTAL DA CONTRATANTE"
      title={view === "overview" ? "Visão geral dos pareceres publicados." : "O que foi conferido, com as limitações claras."}
      description="Acompanhe os resultados revisados e publicados pela Bernhoeft para a sua empresa. Os indicadores refletem a publicação, não o andamento interno da análise."
    />
    <section className="workspace-card" aria-label="Filtros dos pareceres">
      <h2>Filtrar resultados</h2>
      <div className="analyst-filter-grid">
        <label className="filter-label">Fornecedora
          <select aria-label="Fornecedora" value={supplier} onChange={(e) => update("fornecedora_id", e.target.value)}>
            <option value="">Todas as fornecedoras</option>
            {(data?.filtros.fornecedoras ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </label>
        <label className="filter-label">Contrato
          <select aria-label="Contrato" value={contract} onChange={(e) => update("contract_id", e.target.value)}>
            <option value="">Todos os contratos</option>
            {(data?.filtros.contratos ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </label>
        <label className="filter-label">Competência
          <select aria-label="Competência" value={month} onChange={(e) => update("competencia", e.target.value)}>
            <option value="">Mais recente com publicação</option>
            {(data?.filtros.competencias ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      <p className="card-footnote">Somente contratos da sua organização. Rascunhos, imagens e valores em reais não são exibidos.</p>
      {(supplier || contract || month) && <button className="button secondary" onClick={() => router.replace(base, { scroll: false })}>Limpar filtros</button>}
    </section>
    {loading ? <LoadingState /> : error || !data ? <ErrorState message={error ?? "Falha ao consultar o portal."} onRetry={reload} /> : <>
      <p className="analyst-period">Competência exibida: {data.filtros.competencia_selecionada ?? "nenhuma publicação disponível"}</p>
      {view === "overview" ? <>
        <div className="stat-grid">
          <div className="stat-card"><strong>{data.resumo.contratos_com_parecer}/{data.resumo.contratos}</strong><span>Contratos com parecer</span><small>Na competência exibida</small></div>
          <div className="stat-card"><strong>{percent(data.resumo.taxa_divergencias)}</strong><span>Taxa de divergências</span><small>{data.resumo.divergencias} entre {data.resumo.analisados} comparações válidas</small></div>
          <div className="stat-card"><strong>{percent(data.resumo.cobertura)}</strong><span>Cobertura nos pareceres</span><small>{data.resumo.analisados} comparações válidas / {data.resumo.trabalhadores} vínculos publicados</small></div>
          <div className="stat-card"><strong>{data.resumo.dados_insuficientes + data.resumo.nao_avaliados}</strong><span>Sem comparação válida</span><small>Dados insuficientes ou não avaliados nos pareceres</small></div>
        </div>
        <section className="workspace-card">
          <h2>Resultados por contrato e fornecedora</h2>
          {data.contratos.length === 0 ? <EmptyState title="Nenhum contrato neste filtro." text="Limpe os filtros ou aguarde a vinculação pela Bernhoeft." /> : <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Contrato</th><th>Fornecedora</th><th>Publicação</th><th>Taxa de divergências</th><th>Cobertura</th><th>Parecer</th></tr></thead>
            <tbody>{data.contratos.map((c) => <tr key={c.id}>
              <td>{c.nome}</td><td>{c.fornecedora_nome}</td>
              <td>{c.parecer_id === null ? "Sem parecer publicado nesta competência" : `v${c.versao} · ${formatDate(c.publicado_em)}`}</td>
              <td>{percent(c.resumo?.taxa_divergencias ?? null)}</td><td>{percent(c.resumo?.cobertura ?? null)}</td>
              <td>{c.parecer_id !== null ? <Link className="text-link" href={reportLink(c.id, c.parecer_id)}>Consultar parecer</Link> : "—"}</td>
            </tr>)}</tbody>
          </table></div>}
        </section>
        {data.resumo.contratos_com_parecer === 0 && <EmptyState title="Nenhum parecer publicado ainda neste período." text="A ausência de publicação não significa que os contratos estejam regulares." />}
        <p className="card-footnote">{data.observacao} Taxas sem comparações válidas são indisponíveis (—).</p>
      </> : <PublishedReports key={reportQuery} query={reportQuery} selectedId={params.get("parecer_id")} />}
    </>}
  </>;
}

function PublishedReports({ query, selectedId }: { query: string; selectedId: string | null }) {
  const { data, loading, error, reload } = useClientQuery<Report[]>("/api/client/reports" + query);
  const [selected, setSelected] = useState<number | null>(null);
  const rows = data ?? [];
  const current = rows.find((r) => r.id === (selected ?? Number(selectedId))) ?? rows[0];
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!current) return <EmptyState title="Nenhum parecer publicado ainda." text="Quando a Bernhoeft publicar um parecer neste escopo, ele aparecerá aqui. Tente outra competência ou limpe os filtros." />;
  return <>
    <div className="list-toolbar"><label className="filter-label">Parecer
      <select value={current.id} onChange={(e) => setSelected(Number(e.target.value))}>
        {rows.map((r) => <option key={r.id} value={r.id}>{r.contract_id} · {r.competencia} · versão {r.versao} · publicado em {formatDate(r.publicado_em)}</option>)}
      </select>
    </label></div>
    {"resumo" in current.conteudo_json ? <section className="workspace-card"><ReportPdfButton report={current} /><ReportView content={current.conteudo_json as ReportContent} report={current} /></section>
      : <EmptyState title="Conteúdo do parecer indisponível." text="Solicite à Bernhoeft a verificação desta publicação." />}
  </>;
}
