"use client";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  Layers3,
  CircleAlert,
  Clock3,
  Check,
  Fingerprint,
} from "lucide-react";
import {
  batches,
  canExploreBatch,
  formatReceivedAt,
  getBatchDocuments,
  getBatchIssues,
} from "@/lib/batches";
import { useDemo } from "./demo-provider";
import { BatchBadge } from "./batch-badge";
import {
  PageIntro,
  DocumentBadge,
  IssueBadge,
  EmptyState,
} from "./workspace-parts";
export function BatchDetail({ id }: { id: string }) {
  const { role, contract, competence, setContract, setCompetence } = useDemo();
  const batch = batches.find((b) => b.id === id);
  if (!batch || !canExploreBatch(batch, role))
    return (
      <>
        <PageIntro
          eyebrow="LOTES"
          title="Lote indisponível."
          description="Este lote não está disponível na perspectiva selecionada."
        />
        <Link className="button secondary" href="/painel/lotes">
          Voltar aos lotes <ArrowLeft size={16} />
        </Link>
      </>
    );
  if (batch.contract !== contract || batch.competence !== competence)
    return (
      <>
        <PageIntro
          eyebrow="CONTEXTO DO LOTE"
          title="Este lote pertence a outro contexto."
          description="Ajuste o contrato e a competência para consultar os dados deste lote de exemplo."
        />
        <section className="workspace-card batch-context-message">
          <p>
            {batch.id} · {batch.contract} · {batch.competence}
          </p>
          <button
            className="button"
            onClick={() => {
              setContract(batch.contract);
              setCompetence(batch.competence);
            }}
          >
            Usar o contexto deste lote <ArrowRight size={16} />
          </button>
          <Link className="text-link" href="/painel/lotes">
            Voltar à listagem
          </Link>
        </section>
      </>
    );
  const docs = getBatchDocuments(batch.id);
  const batchIssues = getBatchIssues(batch.id);
  const supplier = role === "OPERADOR_FORN";
  const completed = batch.status === "CONCLUIDO";
  const failed = batch.status === "FALHA_PROCESSAMENTO";
  return (
    <>
      <Link href="/painel/lotes" className="back-link batch-back">
        <ArrowLeft size={15} /> Todos os lotes
      </Link>
      <PageIntro
        eyebrow="DETALHES DO LOTE"
        title={batch.id}
        description={batch.filename}
        action={<BatchBadge status={batch.status} />}
      />
      <div className="batch-detail-grid">
        <section className="workspace-card">
          <div className="card-title">
            <h2>Arquivo e contexto</h2>
            <FileText size={19} />
          </div>
          <dl className="detail-list">
            <div>
              <dt>Contrato</dt>
              <dd>{batch.contract}</dd>
            </div>
            <div>
              <dt>Competência</dt>
              <dd>{batch.competence}</dd>
            </div>
            <div>
              <dt>Formato / tamanho</dt>
              <dd>
                {batch.format} · {batch.sizeLabel}
              </dd>
            </div>
            <div>
              <dt>Recebimento (Recife)</dt>
              <dd>{formatReceivedAt(batch.receivedAt)}</dd>
            </div>
            <div>
              <dt>Etapa</dt>
              <dd>{batch.stage}</dd>
            </div>
          </dl>
          <div className="batch-progress">
            {batch.format === "AEJ" ? (
              <>
                <Layers3 size={21} />
                <div>
                  <strong>Dados estruturados de jornada</strong>
                  <p>
                    AEJ segue leitura de registros, sem OCR ou contagem de
                    páginas.
                  </p>
                </div>
              </>
            ) : (
              <div className="page-progress">
                <div>
                  <strong>Leitura de páginas</strong>
                  <span>
                    {batch.readPages} de {batch.totalPages}
                  </span>
                </div>
                <progress
                  value={batch.readPages}
                  max={batch.totalPages ?? 1}
                  aria-label="Páginas lidas"
                />
                <p>
                  Progresso de leitura do exemplo. Não representa conclusão da
                  análise.
                </p>
              </div>
            )}
          </div>
        </section>
        <section className="workspace-card">
          <div className="card-title">
            <h2>Caminho do lote</h2>
            <Clock3 size={19} />
          </div>
          <p className="batch-timeline-caption">
            Eventos sintéticos ·{" "}
            {new Intl.DateTimeFormat("pt-BR", {
              timeZone: "America/Recife",
              dateStyle: "short",
            }).format(new Date(batch.receivedAt))}
          </p>
          <ol className="batch-timeline">
            {batch.events.map((event) => (
              <li className={event.kind} key={event.title}>
                <span className="timeline-marker">
                  {event.kind === "done" ? (
                    <Check size={12} />
                  ) : event.kind === "error" ? (
                    <CircleAlert size={12} />
                  ) : (
                    <Clock3 size={12} />
                  )}
                </span>
                <div>
                  <strong>{event.title}</strong>
                  <p>{event.description}</p>
                  <small>{event.time}</small>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
      {failed && (
        <section className="batch-failure" aria-label="Falha técnica do lote">
          <CircleAlert size={22} />
          <div>
            <h2>Falha técnica no processamento</h2>
            <p>
              A leitura foi interrompida neste exemplo. Isso não atribui erro à
              fornecedora nem cria uma pendência documental automaticamente.
            </p>
            <details>
              <summary>Como será a retomada?</summary>
              <p>
                Na integração, a retomada deverá ocorrer pela ação de
                reprocessamento da API, respeitando as permissões do perfil.
                Este protótipo não executa reprocessamento nem altera o estado
                do lote.
              </p>
            </details>
          </div>
        </section>
      )}
      <section className="workspace-card">
        <div className="card-title">
          <h2>Documentos identificados</h2>
          {completed && (
            <Link href={`/painel/documentos?lote=${batch.id}`}>
              Abrir na biblioteca <ArrowRight size={14} />
            </Link>
          )}
        </div>
        {docs.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Trabalhador</th>
                  <th>Página inicial</th>
                  <th>Situação</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <strong>{d.type}</strong>
                      <small>{d.id} · versão 1 (exemplo)</small>
                    </td>
                    <td>{d.worker}</td>
                    <td>{d.page}</td>
                    <td>
                      <DocumentBadge status={d.status} supplier={supplier} />
                    </td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/painel/documentos?lote=${batch.id}&documento=${d.id}`}
                        aria-label={`Conferir ${d.id}`}
                      >
                        Conferir <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Documentos ainda não consolidados"
            text={
              batch.format === "AEJ"
                ? "Os registros de jornada aguardam processamento estruturado neste exemplo."
                : failed
                  ? "A retomada será necessária para concluir o processamento do lote."
                  : "A classificação e os vínculos documentais ainda não estão disponíveis neste exemplo."
            }
          />
        )}
        <p className="card-footnote">
          Processar o lote não aprova os documentos, resolve pendências ou
          publica pareceres.
        </p>
      </section>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Pendências vinculadas aos documentos</h2>
          <Fingerprint size={18} />
        </div>
        {batchIssues.length ? (
          batchIssues.map((issue) => (
            <div className="attention-row" key={issue.id}>
              <div className="attention-icon">
                <CircleAlert size={18} />
              </div>
              <div>
                <strong>{issue.title}</strong>
                <span>
                  {issue.id} · {issue.document} · {issue.worker}
                </span>
              </div>
              <IssueBadge status={issue.status} />
              <Link
                className="table-action"
                href={`/painel/pendencias?pendencia=${issue.id}`}
                aria-label={`Orientação de ${issue.id}`}
              >
                Orientação <ArrowRight size={14} />
              </Link>
            </div>
          ))
        ) : (
          <EmptyState
            title={
              completed
                ? "Nenhuma pendência vinculada aos documentos deste lote"
                : "Aguardando consolidação documental"
            }
            text={
              completed
                ? "Esta visão considera apenas pendências com documento de referência neste lote. Outras solicitações podem existir no contrato."
                : "O processamento incompleto não permite concluir que não há pendências."
            }
          />
        )}
      </section>
    </>
  );
}
