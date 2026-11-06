"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowUpRight, Search } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import {
  DocumentBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageIntro,
  Snippet,
} from "@/components/workspace-parts";
import { api, docStatusLabels, pageList, typeLabels, type Doc, type SearchHit } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function DocumentsPage() {
  const { contract, me } = useSession();
  const supplier = me?.org_tipo === "FORNECEDORA";
  const [status, setStatus] = useState("");
  const [tipo, setTipo] = useState("");
  const params = new URLSearchParams();
  if (contract) params.set("contract_id", contract);
  if (status) params.set("status", status);
  if (tipo) params.set("tipo", tipo);
  const { data, error, loading, reload } = useApi<Doc[]>(`/api/documents?${params.toString()}`);
  const rows = (data ?? []).filter((d) => !contract || d.contract_id === contract);

  return (
    <>
      <PageIntro
        eyebrow="DOCUMENTOS CLASSIFICADOS"
        title="Separados, classificados e pesquisáveis."
        description="Consulte os documentos da fornecedora neste contrato, inclusive os enviados por outros operadores. A seleção de contrato limita a lista e a busca."
      />
      <SearchBox key={contract} contract={contract} />
      <div className="list-toolbar">
        <label className="filter-label">
          Tipo
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(typeLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="filter-label">
          Situação
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todas</option>
            {(["APTO", "PENDENTE_CORRECAO", supplier ? "EM_ANALISE" : "REVISAO_HUMANA", "SUBSTITUIDO"] as const).map((k) => (
              <option key={k} value={k}>{docStatusLabels[k]}</option>
            ))}
          </select>
        </label>
      </div>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhum documento encontrado." text="Ajuste os filtros ou envie um lote." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Documento</th>
                <th>Tipo</th>
                <th>Trabalhador</th>
                <th>Competência</th>
                <th>Lote / páginas</th>
                <th>Situação</th>
                <th><span className="sr-only">Ações</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  <td>#{d.id}{d.versao > 1 && <small className="muted"> · v{d.versao}</small>}</td>
                  <td>{typeLabels[d.tipo] ?? d.tipo}</td>
                  <td>{d.worker_id ?? "—"}</td>
                  <td>{d.competencia ?? "—"}</td>
                  <td>#{d.batch_id} · {pageList(d.paginas)}</td>
                  <td><DocumentBadge status={d.status} /></td>
                  <td>
                    <Link className="table-action" href={`/painel/documentos/detalhe?id=${d.id}`}>
                      Abrir <ArrowUpRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function SearchBox({ contract }: { contract: string }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setHits(await api<SearchHit[]>(`/api/search?q=${encodeURIComponent(query.trim())}&contract_id=${encodeURIComponent(contract)}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha na busca");
      setHits(null);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workspace-card">
      <form className="search-form" onSubmit={submit} role="search">
        <label className="search-field">
          <Search size={18} />
          <span className="sr-only">Buscar no texto das páginas</span>
          <input
            type="search"
            placeholder="Buscar no texto lido das páginas (ex.: T001, horas extras)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button className="button" disabled={busy || !query.trim()}>{busy ? "Buscando…" : "Buscar"}</button>
      </form>
      {error && <Notice tone="error">{error}</Notice>}
      {hits && (hits.length === 0 ? (
        <p className="muted">Nenhuma página encontrada para “{query}”.</p>
      ) : (
        <ul className="search-results">
          {hits.map((h) => (
            <li key={h.page_id}>
              {h.document_id ? (
                <Link href={`/painel/documentos/detalhe?id=${h.document_id}#pagina-${h.page_id}`}>
                  Documento #{h.document_id} · página {h.ordem} do lote #{h.batch_id}
                </Link>
              ) : (
                <strong>Página {h.ordem} do lote #{h.batch_id}</strong>
              )}
              <span className="muted"> · {h.contract_id}</span>
              <p><Snippet text={h.trecho} /></p>
            </li>
          ))}
        </ul>
      ))}
    </section>
  );
}
