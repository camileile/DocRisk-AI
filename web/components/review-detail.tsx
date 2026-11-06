"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  ScanLine,
  ShieldCheck,
  Check,
  CircleAlert,
  RotateCcw,
  ClipboardCheck,
} from "lucide-react";
import { documents } from "@/lib/demo";
import {
  getReviewExample,
  getMergeCandidate,
  documentTypes,
  actionLabels,
  type ReviewAction,
  type ReviewExample,
} from "@/lib/review";
import { useDemo } from "./demo-provider";
import { PageIntro, DocumentBadge } from "./workspace-parts";
type DemoDocument = (typeof documents)[number];
type PreparedReview = {
  action: ReviewAction;
  type: string;
  worker: string;
  competence: string;
  reason: string;
  groups: number[][];
  target: string | null;
};
export function ReviewDetail({ id }: { id: string }) {
  const { role, contract, competence, setContract, setCompetence } = useDemo();
  const doc = documents.find((d) => d.id === id);
  const example = getReviewExample(id);
  if (role !== "ANALISTA_BH" || !doc || !example)
    return (
      <>
        <PageIntro
          eyebrow="REVISÃO DOCUMENTAL"
          title="Revisão indisponível."
          description="Esta revisão não está disponível na perspectiva selecionada."
        />
        <Link className="button secondary" href="/painel">
          Voltar ao painel
        </Link>
      </>
    );
  if (doc.contract !== contract || doc.competence !== competence)
    return (
      <>
        <PageIntro
          eyebrow="CONTEXTO DA REVISÃO"
          title="Selecione o contexto do documento."
          description="O documento pertence a outro contrato ou competência da demonstração."
        />
        <section className="workspace-card batch-context-message">
          <p>
            {doc.id} · {doc.contract} · {doc.competence}
          </p>
          <button
            className="button"
            onClick={() => {
              setContract(doc.contract);
              setCompetence(doc.competence);
            }}
          >
            Usar o contexto do documento <ArrowRight size={16} />
          </button>
          <Link href="/painel/revisao" className="text-link">
            Voltar à fila
          </Link>
        </section>
      </>
    );
  return <ReviewWorkspace key={id} doc={doc} example={example} />;
}
function ReviewWorkspace({
  doc,
  example,
}: {
  doc: DemoDocument;
  example: ReviewExample;
}) {
  const [pageIndex, setPageIndex] = useState(0);
  const [zoom, setZoom] = useState(100);
  const page = example.pages[pageIndex];
  return (
    <>
      <Link className="back-link batch-back" href="/painel/revisao">
        <ArrowLeft size={15} /> Fila de revisão
      </Link>
      <PageIntro
        eyebrow="CONFERÊNCIA DOCUMENTAL"
        title={`Revisão · ${doc.id}`}
        description={`${doc.type} · ${doc.worker} · ${doc.competence}`}
        action={<DocumentBadge status={doc.status} />}
      />
      <div className="inline-info review-alert">
        <ScanLine size={18} />
        <p>
          <strong>Conferir antes de prosseguir:</strong> {example.reason}
        </p>
      </div>
      <div className="review-workspace">
        <section
          className="workspace-card review-viewer"
          aria-label="Conferência das páginas sintéticas"
        >
          <div className="card-title">
            <h2>Páginas do documento</h2>
            <Link href={`/painel/lotes/${doc.batch}`}>
              {doc.batch} <ArrowRight size={14} />
            </Link>
          </div>
          <div className="review-viewer-toolbar">
            <div>
              <button
                className="icon-button"
                disabled={pageIndex === 0}
                onClick={() => setPageIndex(pageIndex - 1)}
                aria-label="Página anterior"
              >
                <ChevronLeft size={17} />
              </button>
              <span aria-live="polite">
                Página {page.order} do lote · {pageIndex + 1} de{" "}
                {example.pages.length} no documento
              </span>
              <button
                className="icon-button"
                disabled={pageIndex === example.pages.length - 1}
                onClick={() => setPageIndex(pageIndex + 1)}
                aria-label="Próxima página"
              >
                <ChevronRight size={17} />
              </button>
            </div>
            <div>
              <button
                className="icon-button"
                aria-label="Diminuir zoom"
                disabled={zoom <= 80}
                onClick={() => setZoom(zoom - 20)}
              >
                <ZoomOut size={16} />
              </button>
              <span>{zoom}%</span>
              <button
                className="icon-button"
                aria-label="Aumentar zoom"
                disabled={zoom >= 140}
                onClick={() => setZoom(zoom + 20)}
              >
                <ZoomIn size={16} />
              </button>
            </div>
          </div>
          <div
            className="review-page-tabs"
            aria-label="Selecionar página do documento"
          >
            {example.pages.map((item, index) => (
              <button
                key={item.order}
                className={index === pageIndex ? "selected" : ""}
                aria-pressed={index === pageIndex}
                onClick={() => setPageIndex(index)}
              >
                Página {item.order}
              </button>
            ))}
          </div>
          <div className="synthetic-page-stage">
            <article
              className="synthetic-page"
              style={{ fontSize: `${zoom / 100}em` }}
              aria-label={`Conteúdo sintético da página ${page.order}`}
            >
              <div className="synthetic-watermark">
                DEMONSTRAÇÃO · DADOS SINTÉTICOS
              </div>
              <div className="synthetic-page-title">
                <span>DOCRISK AI / DOCUMENTO DE EXEMPLO</span>
                <h2>{page.heading}</h2>
                <p>Reconstrução visual para testar a interface.</p>
              </div>
              <dl>
                <div>
                  <dt>Trabalhador</dt>
                  <dd>{page.worker}</dd>
                </div>
                <div>
                  <dt>Competência</dt>
                  <dd>{page.competence}</dd>
                </div>
                <div>
                  <dt>Origem</dt>
                  <dd>
                    {doc.batch}, página {page.order}, versão 1
                  </dd>
                </div>
              </dl>
              <div className="synthetic-lines">
                {page.lines.map((line) => (
                  <div key={line.label}>
                    <span>{line.label}</span>
                    <strong>{line.value}</strong>
                  </div>
                ))}
              </div>
              <p className="synthetic-body">{page.text}</p>
              <div className="synthetic-page-bottom">
                Página {page.order} do lote · {doc.id}
                <br />
                Sem arquivo original ou extração de IA nesta demonstração.
              </div>
            </article>
          </div>
          <p className="review-viewer-note">
            Conteúdo criado apenas para conferência da interface. Na integração,
            as imagens serão carregadas pela rota autenticada da API.
          </p>
        </section>
        <ReviewPreparation doc={doc} example={example} />
      </div>
    </>
  );
}
function ReviewPreparation({
  doc,
  example,
}: {
  doc: DemoDocument;
  example: ReviewExample;
}) {
  const [action, setAction] = useState<ReviewAction>("aprovar");
  const [type, setType] = useState(doc.type);
  const [worker, setWorker] = useState(doc.worker);
  const [competence, setCompetence] = useState(doc.competence);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [splitAfter, setSplitAfter] = useState(example.pages[0].order);
  const [prepared, setPrepared] = useState<PreparedReview | null>(null);
  const [error, setError] = useState("");
  const workers = Array.from(
    new Set(
      documents.filter((d) => d.contract === doc.contract).map((d) => d.worker),
    ),
  );
  const candidate = getMergeCandidate(doc.id);
  const canMerge = Boolean(
    candidate &&
    candidate.worker === worker &&
    candidate.type === type &&
    candidate.competence === competence,
  );
  const canSplit = example.pages.length > 1;
  function prepare(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    if (!confirmed || reason.trim().length < 10) {
      setError(
        "Confira as páginas e descreva a justificativa com pelo menos 10 caracteres.",
      );
      return;
    }
    if (
      action === "dividir" &&
      (!canSplit ||
        !example.pages.slice(0, -1).some((p) => p.order === splitAfter))
    ) {
      setError("Selecione uma divisão válida entre as páginas.");
      return;
    }
    if (action === "unir_proximo" && !canMerge) {
      setError(
        "Não há próximo documento compatível com os vínculos informados.",
      );
      return;
    }
    const pages = example.pages.map((p) => p.order);
    setPrepared({
      action,
      type,
      worker,
      competence,
      reason: reason.trim(),
      groups:
        action === "dividir"
          ? [
              pages.filter((n) => n <= splitAfter),
              pages.filter((n) => n > splitAfter),
            ]
          : [
              action === "unir_proximo" && candidate
                ? [...pages, candidate.page]
                : pages,
            ],
      target: action === "unir_proximo" && candidate ? candidate.id : null,
    });
  }
  function reset() {
    setAction("aprovar");
    setType(doc.type);
    setWorker(doc.worker);
    setCompetence(doc.competence);
    setReason("");
    setConfirmed(false);
    setSplitAfter(example.pages[0].order);
    setPrepared(null);
    setError("");
  }
  return (
    <section className="workspace-card review-preparation">
      <div className="card-title">
        <h2>Preparação da revisão</h2>
        <ShieldCheck size={19} />
      </div>
      <p className="review-form-intro">
        Confira os vínculos e prepare a decisão. Esta tela não altera documentos
        ou encaminha solicitações.
      </p>
      <form
        onSubmit={prepare}
        onChange={() => {
          setPrepared(null);
          setError("");
        }}
      >
        <label>
          Classificação proposta
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {documentTypes.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Trabalhador proposto
          <select value={worker} onChange={(e) => setWorker(e.target.value)}>
            {workers.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Competência proposta
          <select
            value={competence}
            onChange={(e) => setCompetence(e.target.value)}
          >
            <option>10/2026</option>
            <option>09/2026</option>
          </select>
        </label>
        <label>
          Ação proposta
          <select
            value={action}
            onChange={(e) => setAction(e.target.value as ReviewAction)}
          >
            <option value="aprovar">Aprovar documento</option>
            <option value="solicitar_correcao">Solicitar correção</option>
            <option value="dividir" disabled={!canSplit}>
              Dividir documento{!canSplit ? " · exige múltiplas páginas" : ""}
            </option>
            <option value="unir_proximo" disabled={!canMerge}>
              Unir ao próximo{!canMerge ? " · sem candidato compatível" : ""}
            </option>
          </select>
        </label>
        {action === "dividir" && (
          <div className="review-action-context">
            <label>
              Onde termina o primeiro documento?
              <select
                value={splitAfter}
                onChange={(e) => setSplitAfter(Number(e.target.value))}
              >
                {example.pages.slice(0, -1).map((p) => (
                  <option key={p.order} value={p.order}>
                    Após a página {p.order} do lote
                  </option>
                ))}
              </select>
            </label>
            <p>
              A prévia preservará todas as páginas em dois grupos consecutivos,
              sem criar documentos.
            </p>
          </div>
        )}
        {action === "unir_proximo" && candidate && (
          <div className="review-action-context">
            <strong>Candidato: {candidate.id}</strong>
            <p>
              {candidate.type} · página {candidate.page} · {candidate.worker}.
              Mesmo lote e competência, com página contígua. A continuidade
              ainda precisa ser conferida.
            </p>
          </div>
        )}
        {action === "solicitar_correcao" && (
          <div className="review-action-context">
            <p>
              Descreva abaixo uma orientação objetiva para a fornecedora,
              incluindo o documento, a página e a correção necessária. Nenhuma
              pendência será criada nesta prévia.
            </p>
          </div>
        )}
        <label>
          {action === "solicitar_correcao"
            ? "Orientação para a fornecedora"
            : "Justificativa da revisão"}
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            minLength={10}
            maxLength={2000}
            required
            placeholder="Registre o que foi conferido e a referência da evidência…"
          />
        </label>
        <label className="review-confirm">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            required
          />
          <span>
            Conferi as páginas, a identificação e a competência deste exemplo.
          </span>
        </label>
        {error && (
          <p className="upload-error" role="alert">
            {error}
          </p>
        )}
        <button className="button" type="submit">
          <ClipboardCheck size={17} /> Preparar prévia
        </button>
        <button className="review-reset" type="button" onClick={reset}>
          <RotateCcw size={14} /> Restaurar campos
        </button>
      </form>
      {prepared && (
        <section
          className="prepared-review"
          role="status"
          aria-label="Prévia da revisão"
        >
          <span className="eyebrow">
            <Check size={14} /> PRÉVIA PREPARADA
          </span>
          <h3>{actionLabels[prepared.action]}</h3>
          <dl className="detail-list">
            <div>
              <dt>Tipo proposto</dt>
              <dd>{prepared.type}</dd>
            </div>
            <div>
              <dt>Trabalhador</dt>
              <dd>{prepared.worker}</dd>
            </div>
            <div>
              <dt>Competência</dt>
              <dd>{prepared.competence}</dd>
            </div>
            <div>
              <dt>Origem</dt>
              <dd>
                {doc.batch} · {doc.id}
              </dd>
            </div>
            {prepared.target && (
              <div>
                <dt>Próximo documento</dt>
                <dd>{prepared.target}</dd>
              </div>
            )}
          </dl>
          <div className="review-page-groups">
            {prepared.groups.map((group, index) => (
              <span key={index}>
                {prepared.action === "dividir"
                  ? `Grupo ${index + 1}`
                  : "Páginas"}
                : {group.join(", ")}
              </span>
            ))}
          </div>
          <p className="prepared-reason">{prepared.reason}</p>
          <div className="evidence-note">
            <CircleAlert size={17} />
            <p>
              Prévia local. O documento continua em revisão. Nada foi aprovado,
              dividido, unido ou enviado à fornecedora; a fila permanece
              inalterada. A confirmação final depende da API e da auditoria.
            </p>
          </div>
        </section>
      )}
    </section>
  );
}
