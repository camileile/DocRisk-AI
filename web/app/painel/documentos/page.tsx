"use client";
import { Suspense, useState } from "react";
import { Search, FileText, X, ArrowUpRight, Fingerprint } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { documents } from "@/lib/demo";
import { useDemo } from "@/components/demo-provider";
import {
  DocumentBadge,
  EmptyState,
  PageIntro,
} from "@/components/workspace-parts";
export default function Documents() {
  return (
    <Suspense fallback={<p>Carregando documentos…</p>}>
      <DocumentsContent />
    </Suspense>
  );
}
function DocumentsContent() {
  const searchParams = useSearchParams();
  const batch = searchParams.get("lote");
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  const [expandedId, setSelectedId] = useState<string | null | undefined>(
    undefined,
  );
  const selectedId =
    expandedId === undefined ? searchParams.get("documento") : expandedId;
  const supplier = role === "OPERADOR_FORN";
  const rows = documents.filter(
    (d) =>
      d.contract === contract &&
      d.competence === competence &&
      (!batch || d.batch === batch) &&
      (status === "todos" || d.status === status) &&
      `${d.id} ${d.worker} ${d.type} ${d.batch}`
        .toLocaleLowerCase("pt-BR")
        .includes(query.toLocaleLowerCase("pt-BR")),
  );
  const selected = rows.find((d) => d.id === selectedId);
  return (
    <>
      <PageIntro
        eyebrow="BIBLIOTECA DOCUMENTAL"
        title="Documentos conectados."
        description="Consulte a situação, o vínculo e a origem de cada documento de exemplo."
        action={
          supplier ? (
            <Link href="/painel/envio" className="button">
              Preparar envio <ArrowUpRight size={16} />
            </Link>
          ) : undefined
        }
      />
      {batch && (
        <div className="batch-filter-chip">
          <span>
            Lote filtrado: <strong>{batch}</strong>
          </span>
          <Link href="/painel/documentos">
            Limpar filtro <X size={14} />
          </Link>
        </div>
      )}
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar documentos"
              placeholder="Buscar trabalhador, tipo ou ID…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="filter-label">
            Situação
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="todos">Todas as situações</option>
              <option value="APTO">Apto</option>
              <option value="REVISAO_HUMANA">
                {supplier ? "Em análise" : "Revisão humana"}
              </option>
              <option value="PENDENTE_CORRECAO">Pendente de correção</option>
            </select>
          </label>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length} documento{rows.length !== 1 ? "s" : ""} encontrado
          {rows.length !== 1 ? "s" : ""}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Trabalhador</th>
                  <th>Competência</th>
                  <th>Situação</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div className="document-cell">
                        <FileText size={19} />
                        <div>
                          <strong>{d.type}</strong>
                          <small>
                            {d.id} · {d.batch}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>{d.worker}</td>
                    <td>{d.competence}</td>
                    <td>
                      <DocumentBadge status={d.status} supplier={supplier} />
                    </td>
                    <td>
                      <button
                        className="table-action"
                        aria-expanded={selectedId === d.id}
                        onClick={() =>
                          setSelectedId(selectedId === d.id ? null : d.id)
                        }
                      >
                        Detalhes <ArrowUpRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum documento encontrado"
            text="Ajuste a busca, a situação ou o contexto da análise para consultar outros exemplos."
          />
        )}
      </section>
      {selected && (
        <section
          className="workspace-card evidence-panel"
          aria-label={`Detalhes de ${selected.id}`}
        >
          <div className="card-title">
            <div>
              <span className="eyebrow">
                RASTREABILIDADE · EXEMPLO SINTÉTICO
              </span>
              <h2>
                {selected.type} · {selected.id}
              </h2>
            </div>
            <button
              className="icon-button"
              aria-label="Fechar detalhes"
              onClick={() => setSelectedId(null)}
            >
              <X size={19} />
            </button>
          </div>
          <div className="evidence-grid">
            <div className="document-preview">
              <FileText size={38} />
              <strong>Referência documental</strong>
              <p>
                <Link
                  className="text-link"
                  href={`/painel/lotes/${selected.batch}`}
                >
                  {selected.batch}
                </Link>{" "}
                · página {selected.page}
              </p>
              <span>
                Representação ilustrativa. O arquivo original não está
                disponível nesta demonstração.
              </span>
            </div>
            <div>
              <dl className="detail-list">
                <div>
                  <dt>Trabalhador</dt>
                  <dd>{selected.worker}</dd>
                </div>
                <div>
                  <dt>Competência</dt>
                  <dd>{selected.competence}</dd>
                </div>
                <div>
                  <dt>Contrato</dt>
                  <dd>{selected.contract}</dd>
                </div>
                <div>
                  <dt>Versão</dt>
                  <dd>1 · exemplo</dd>
                </div>
                <div>
                  <dt>Situação</dt>
                  <dd>
                    <DocumentBadge
                      status={selected.status}
                      supplier={supplier}
                    />
                  </dd>
                </div>
              </dl>
              <div className="evidence-note">
                <Fingerprint size={18} />
                <p>
                  {supplier && selected.status === "REVISAO_HUMANA"
                    ? "Documento em análise pela equipe responsável. Aguarde a conferência."
                    : selected.note}
                </p>
              </div>
            </div>
          </div>
          {!supplier && selected.status === "REVISAO_HUMANA" && (
            <Link
              className="button review-open-link"
              href={`/painel/revisao/${selected.id}`}
            >
              Conferir na revisão <ArrowUpRight size={16} />
            </Link>
          )}
          {!supplier && selected.status === "REVISAO_HUMANA" && (
            <p className="integration-note">
              A aprovação e a revisão documental serão conectadas à API em uma
              próxima etapa.
            </p>
          )}
        </section>
      )}
    </>
  );
}
