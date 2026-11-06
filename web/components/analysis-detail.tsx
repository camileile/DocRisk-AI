"use client";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  CircleAlert,
  FileText,
  Fingerprint,
  GitCompareArrows,
  Clock3,
  ReceiptText,
} from "lucide-react";
import { useDemo } from "./demo-provider";
import {
  PageIntro,
  EmptyState,
  DocumentBadge,
  IssueBadge,
} from "./workspace-parts";
import { AnalysisStatusBadge, AnalysisResultBadge } from "./analysis-badges";
import {
  analyses,
  financialExamples,
  getAnalysisDocuments,
  getAnalysisIssues,
  formatHours,
  formatBRL,
} from "@/lib/analyses";
import { formatReceivedAt } from "@/lib/batches";
export function AnalysisDetail({ id }: { id: string }) {
  const { role, contract, competence, setContract, setCompetence } = useDemo();
  const analysis = analyses.find((a) => a.id === id);
  if (role !== "ANALISTA_BH" || !analysis)
    return (
      <>
        <PageIntro
          eyebrow="CONCILIAÇÕES"
          title="Análise indisponível."
          description="Esta análise não está disponível na perspectiva selecionada."
        />
        <Link href="/painel" className="button secondary">
          Voltar ao painel
        </Link>
      </>
    );
  if (analysis.contract !== contract || analysis.competence !== competence)
    return (
      <>
        <PageIntro
          eyebrow="CONTEXTO DA ANÁLISE"
          title="Selecione o contexto deste par."
          description="Esta análise pertence a outro contrato ou competência da demonstração."
        />
        <section className="workspace-card batch-context-message">
          <p>
            {analysis.id} · {analysis.contract} · {analysis.competence}
          </p>
          <button
            className="button"
            onClick={() => {
              setContract(analysis.contract);
              setCompetence(analysis.competence);
            }}
          >
            Usar o contexto desta análise <ArrowRight size={16} />
          </button>
          <Link className="text-link" href="/painel/conciliacoes">
            Voltar à listagem
          </Link>
        </section>
      </>
    );
  const docs = getAnalysisDocuments(analysis);
  const linkedIssues = getAnalysisIssues(analysis);
  const finances = financialExamples[analysis.id] ?? {
    payrollOvertimeBRL: null,
    netBRL: null,
    paidBRL: null,
  };
  const receipt = docs.find((d) => d.type === "Comprovante de pagamento");
  const payroll = docs.find((d) => d.type === "Holerite");
  const missing = ["Espelho de ponto", "Holerite"].filter(
    (type) => !docs.some((d) => d.type === type),
  );
  const reviewDoc = docs.find((d) => d.status === "REVISAO_HUMANA");
  return (
    <>
      <Link href="/painel/conciliacoes" className="back-link batch-back">
        <ArrowLeft size={15} /> Todas as conciliações
      </Link>
      <PageIntro
        eyebrow={`${analysis.id} · COMPETÊNCIA ${analysis.competence}`}
        title={analysis.worker}
        description={`Contrato ${analysis.contract} · jornada e folha de pagamento`}
        action={<AnalysisStatusBadge status={analysis.status} />}
      />
      <section
        className={`workspace-card analysis-outcome ${analysis.result === "DIVERGENCIA_A_VERIFICAR" ? "attention" : ""}`}
      >
        <div className="analysis-outcome-heading">
          <GitCompareArrows size={23} />
          <div>
            <span className="eyebrow">RESULTADO DO EXEMPLO</span>
            <h2>
              {analysis.result === "NAO_AVALIADO"
                ? "A comparação ainda depende de documentos."
                : analysis.result === "DADOS_INSUFICIENTES"
                  ? "Faltam campos para comparar as horas."
                  : analysis.result === "DIVERGENCIA_A_VERIFICAR"
                    ? "Um indício pede conferência."
                    : "Coincidência nos campos comparados."}
            </h2>
          </div>
        </div>
        <AnalysisResultBadge result={analysis.result} />
        <p>{analysis.reason}</p>
      </section>
      <div className="hours-comparison">
        {[
          {
            label: "Horas extras no ponto",
            value: formatHours(analysis.hoursPoint),
            note:
              analysis.hoursPoint === null
                ? "Campo ausente ou não liberado no exemplo."
                : "Valor documental sintético, em horas.",
          },
          {
            label: "Horas extras na folha",
            value: formatHours(analysis.hoursPayroll),
            note:
              analysis.hoursPayroll === null
                ? "Referência em horas não disponível."
                : "Referência em horas, separada da rubrica em reais.",
          },
          {
            label: "Diferença · ponto menos folha",
            value:
              analysis.differenceHours === null
                ? "Não comparada"
                : formatHours(analysis.differenceHours),
            note:
              analysis.differenceHours === null
                ? "Sem cálculo liberado para este par."
                : "Diferença apenas entre os campos em horas.",
          },
        ].map((item, index) => (
          <article
            key={item.label}
            className={
              index === 2 ? "workspace-card difference-card" : "workspace-card"
            }
          >
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.note}</p>
          </article>
        ))}
      </div>
      <div className="inline-info">
        <CircleAlert size={18} />
        <p>
          Não há conversão de reais em horas, cálculo de passivo ou conclusão
          automática sobre infração. Campos indisponíveis não são tratados como
          zero.
        </p>
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Insumos e evidências de origem</h2>
          <Fingerprint size={19} />
        </div>
        {missing.length > 0 && (
          <div className="analysis-missing">
            <CircleAlert size={17} />
            <p>
              Documentos necessários ainda ausentes neste exemplo:{" "}
              <strong>{missing.join(" e ")}</strong>.
            </p>
          </div>
        )}
        {docs.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento / origem</th>
                  <th>Situação documental</th>
                  <th>
                    <span className="sr-only">Referência</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <strong>{doc.type}</strong>
                      <small>
                        {doc.id} · {doc.batch} · página {doc.page} · versão 1
                      </small>
                    </td>
                    <td>
                      <DocumentBadge status={doc.status} />
                    </td>
                    <td>
                      <div className="evidence-actions">
                        <Link
                          className="table-action"
                          href={`/painel/documentos?lote=${doc.batch}&documento=${doc.id}`}
                          aria-label={`Evidência de ${doc.id}`}
                        >
                          Conferir origem <ArrowRight size={14} />
                        </Link>
                        {doc.status === "REVISAO_HUMANA" && (
                          <Link
                            className="table-action"
                            href={`/painel/revisao/${doc.id}`}
                            aria-label={`Revisão de ${doc.id}`}
                          >
                            Abrir revisão <ArrowRight size={14} />
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Sem documentos vinculados"
            text="O acompanhamento deste exemplo está aguardando o recebimento inicial."
          />
        )}
        <p className="card-footnote">
          Referências sintéticas de versão 1. As páginas representam a origem do
          documento de exemplo, sem arquivo real ou extração de IA.
        </p>
      </section>
      <div className="analysis-detail-columns">
        <section className="workspace-card">
          <div className="card-title">
            <h2>Valores documentais em reais</h2>
            <ReceiptText size={20} />
          </div>
          <p className="analysis-section-note">
            Informações separadas da comparação de jornada. Não são uma
            estimativa de débito.
          </p>
          <dl className="detail-list analysis-money">
            <div>
              <dt>Rubrica de horas extras · folha</dt>
              <dd>{formatBRL(finances.payrollOvertimeBRL)}</dd>
            </div>
            <div>
              <dt>Valor líquido · folha</dt>
              <dd>{formatBRL(finances.netBRL)}</dd>
            </div>
            <div>
              <dt>Valor do comprovante</dt>
              <dd>{formatBRL(finances.paidBRL)}</dd>
            </div>
          </dl>
          <div className="analysis-payment-note">
            <FileText size={18} />
            <div>
              <strong>
                {receipt
                  ? "Comprovante vinculado"
                  : "Sem comprovante vinculado neste exemplo"}
              </strong>
              <p>
                {receipt
                  ? `${receipt.id} · ${receipt.batch}, página ${receipt.page}. A presença do arquivo não atesta quitação integral.`
                  : "A ausência de comprovante nesta demonstração não comprova atraso salarial."}
              </p>
            </div>
          </div>
          <p className="card-footnote">
            {payroll
              ? `Fonte da folha: ${payroll.id} · ${payroll.batch}, página ${payroll.page}.`
              : "Nenhum holerite vinculado para informar os valores da folha."}{" "}
            Dados monetários são exemplos fixos; não são comparados pela regra
            de horas.
          </p>
        </section>
        <section className="workspace-card">
          <div className="card-title">
            <h2>Rastreabilidade da análise</h2>
            <Clock3 size={19} />
          </div>
          <dl className="detail-list">
            <div>
              <dt>Identificador</dt>
              <dd>{analysis.id}</dd>
            </div>
            <div>
              <dt>Regra de referência</dt>
              <dd>{analysis.rule}</dd>
            </div>
            <div>
              <dt>Versão do exemplo</dt>
              <dd>{analysis.version}</dd>
            </div>
            <div>
              <dt>Registro demonstrativo (Recife)</dt>
              <dd>
                {analysis.checkedAt
                  ? formatReceivedAt(analysis.checkedAt)
                  : "Comparação não iniciada"}
              </dd>
            </div>
          </dl>
          <p className="analysis-section-note analysis-history-note">
            Este retrato é fixo. Não houve execução do motor de regras ou
            recálculo pela interface. Histórico real e troca de versão dependem
            da integração com a API.
          </p>
        </section>
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Solicitações deste trabalhador e competência</h2>
          <Link href="/painel/pendencias">
            Ver pendências <ArrowRight size={14} />
          </Link>
        </div>
        {linkedIssues.length ? (
          linkedIssues.map((issue) => (
            <div className="attention-row" key={issue.id}>
              <div className="attention-icon">
                <CircleAlert size={18} />
              </div>
              <div>
                <strong>{issue.title}</strong>
                <span>
                  {issue.id} · {issue.document || "Sem documento de referência"}
                </span>
              </div>
              <IssueBadge status={issue.status} />
              <Link
                className="table-action"
                href={`/painel/pendencias?pendencia=${issue.id}`}
              >
                Orientação <ArrowRight size={14} />
              </Link>
            </div>
          ))
        ) : (
          <EmptyState
            title="Nenhuma solicitação vinculada no exemplo"
            text="Isso não libera uma análise bloqueada. Criar ou atualizar solicitações depende da integração operacional."
          />
        )}
        <p className="card-footnote">
          Uma solicitação resolvida ou reenviada não libera automaticamente
          todos os insumos deste par.
        </p>
      </section>
      <section className="workspace-card analysis-next-step">
        <span className="eyebrow">PRÓXIMO PASSO DE CONFERÊNCIA</span>
        <h2>{analysis.nextStep}</h2>
        {reviewDoc ? (
          <Link className="text-link" href={`/painel/revisao/${reviewDoc.id}`}>
            Conferir documento em revisão <ArrowRight size={16} />
          </Link>
        ) : linkedIssues.some((i) => i.status !== "RESOLVIDA") ? (
          <Link
            className="text-link"
            href={`/painel/pendencias?pendencia=${linkedIssues.find((i) => i.status !== "RESOLVIDA")?.id}`}
          >
            Consultar orientação <ArrowRight size={16} />
          </Link>
        ) : docs.length > 0 ? (
          <Link
            className="text-link"
            href={`/painel/documentos?lote=${docs[0].batch}`}
          >
            Consultar documentos de origem <ArrowRight size={16} />
          </Link>
        ) : (
          <Link className="text-link" href="/painel/lotes">
            Acompanhar lotes recebidos <ArrowRight size={16} />
          </Link>
        )}
        <p className="card-footnote">
          Esta página não aprova análises nem publica pareceres.
        </p>
      </section>
    </>
  );
}
