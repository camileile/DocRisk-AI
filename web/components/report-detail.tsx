"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  Check,
  CircleAlert,
} from "lucide-react";
import { useDemo } from "./demo-provider";
import { reports, getReportContent, type InternalReport } from "@/lib/reports";
import { formatReceivedAt } from "@/lib/batches";
import { summarizeReport } from "@/lib/published-reports";
import { PageIntro } from "./workspace-parts";
import { ReportBadge } from "./report-badge";
import { ReportContent } from "./report-content";
export function ReportDetail({ id }: { id: string }) {
  const { role, contract, competence, setContract, setCompetence } = useDemo();
  const report = reports.find((r) => r.id === id);
  if (role !== "ANALISTA_BH" || !report)
    return (
      <>
        <PageIntro
          eyebrow="PARECERES"
          title="Parecer indisponível."
          description="Este parecer não está disponível nesta perspectiva."
        />
        <Link href="/painel" className="button secondary">
          Voltar ao painel
        </Link>
      </>
    );
  if (report.contract !== contract || report.competence !== competence)
    return (
      <>
        <PageIntro
          eyebrow="CONTEXTO DO PARECER"
          title="Selecione o contexto desta versão."
          description="O parecer pertence a outro contrato ou competência da demonstração."
        />
        <section className="workspace-card batch-context-message">
          <p>
            {report.id} · {report.contract} · {report.competence}
          </p>
          <button
            className="button"
            onClick={() => {
              setContract(report.contract);
              setCompetence(report.competence);
            }}
          >
            Usar o contexto deste parecer <ArrowRight size={16} />
          </button>
          <Link className="text-link" href="/painel/pareceres">
            Voltar à listagem
          </Link>
        </section>
      </>
    );
  const content = getReportContent(report);
  return (
    <>
      <Link className="back-link batch-back" href="/painel/pareceres">
        <ArrowLeft size={15} /> Todos os pareceres
      </Link>
      <PageIntro
        eyebrow="ANALISTA BERNHOEFT"
        title={report.id}
        description={`Versão ${report.version} · ${report.contract} · competência ${report.competence}`}
        action={<ReportBadge status={report.status} />}
      />
      {report.status === "SUBSTITUIDO_POR_VERSAO" ? (
        <section className="workspace-card report-retired">
          <h2>Esta versão foi substituída.</h2>
          <p>
            O conteúdo histórico não foi reconstruído a partir das análises
            atuais. Este exemplo preserva a referência da versão, sem apresentar
            um retrato antigo inexistente.
          </p>
          <Link
            className="button secondary"
            href={`/painel/pareceres/${report.supersededBy}`}
          >
            Consultar versão publicada <ArrowRight size={16} />
          </Link>
        </section>
      ) : (
        content && (
          <>
            <div className="inline-info">
              <ShieldCheck size={18} />
              <p>
                {report.status === "APROVADO_PUBLICADO"
                  ? `Exemplo de versão previamente aprovada por ${content.approvedBy}, em ${content.approvedAt ? formatReceivedAt(content.approvedAt) : ""} (Recife). Conteúdo fixo; nenhuma publicação foi executada por esta tela.`
                  : "Prévia de trabalho, ainda não disponibilizada à contratante. O conteúdo é preparado com os exemplos atuais e não representa um retrato publicado."}
              </p>
            </div>
            <ReportContent report={content} />
            {(report.status === "RASCUNHO" ||
              report.status === "EM_REVISAO") && (
              <ReportPreparation
                key={report.id}
                report={report}
                total={summarizeReport(content.items).total}
              />
            )}
            {report.status === "APROVADO_PUBLICADO" && (
              <section className="workspace-card report-fixed">
                <h2>Versão publicada em modo de consulta.</h2>
                <p>
                  Correções posteriores exigem nova versão. Um rascunho novo não
                  altera este conteúdo nem o substitui automaticamente.
                </p>
                <Link className="text-link" href="/painel/pareceres">
                  Consultar versões <ArrowRight size={16} />
                </Link>
              </section>
            )}
          </>
        )
      )}
    </>
  );
}
function ReportPreparation({
  report,
  total,
}: {
  report: InternalReport;
  total: number;
}) {
  const [action, setAction] = useState("revisao");
  const [notes, setNotes] = useState("");
  const [checks, setChecks] = useState([false, false, false]);
  const [prepared, setPrepared] = useState(false);
  const [error, setError] = useState("");
  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!checks.every(Boolean) || notes.trim().length < 10) {
      setError(
        "Conclua as conferências e registre uma observação com pelo menos 10 caracteres.",
      );
      return;
    }
    if (action === "publicacao" && report.status !== "EM_REVISAO") {
      setError(
        "O exemplo precisa estar em revisão antes de preparar a publicação.",
      );
      return;
    }
    setError("");
    setPrepared(true);
  }
  return (
    <section className="workspace-card report-preparation">
      <div className="card-title">
        <h2>Conferência antes do encaminhamento</h2>
        <ShieldCheck size={20} />
      </div>
      <p>
        As observações abaixo são internas. Preparar a prévia não muda a
        situação, cria versão ou publica conteúdo.
      </p>
      <form
        onSubmit={prepare}
        onChange={() => {
          setPrepared(false);
          setError("");
        }}
      >
        <label>
          Etapa proposta
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="revisao">Encaminhar à revisão</option>
            <option
              value="publicacao"
              disabled={report.status !== "EM_REVISAO"}
            >
              Preparar aprovação e publicação
              {report.status !== "EM_REVISAO"
                ? " · exige etapa de revisão"
                : ""}
            </option>
          </select>
        </label>
        <fieldset>
          <legend>Conferências obrigatórias</legend>
          {[
            "Conferi o escopo, as limitações e as referências de evidência.",
            `Conferi os ${total} pares do total, incluindo bloqueados e em revisão.`,
            "Conferi a linguagem de indícios e o conteúdo destinado à contratante.",
          ].map((label, index) => (
            <label className="review-confirm" key={label}>
              <input
                type="checkbox"
                checked={checks[index]}
                required
                onChange={(e) =>
                  setChecks(
                    checks.map((value, i) =>
                      i === index ? e.target.checked : value,
                    ),
                  )
                }
              />
              <span>{label}</span>
            </label>
          ))}
        </fieldset>
        <label>
          Observação interna para revisão
          <textarea
            required
            minLength={10}
            maxLength={2000}
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Registre a conferência realizada e os pontos de atenção…"
          />
        </label>
        {error && (
          <p role="alert" className="upload-error">
            {error}
          </p>
        )}
        <button className="button" type="submit">
          Preparar prévia <ArrowRight size={17} />
        </button>
      </form>
      {prepared && (
        <div className="report-prepared" role="status">
          <span className="eyebrow">
            <Check size={14} /> PRÉVIA LOCAL PREPARADA
          </span>
          <h3>
            {action === "publicacao"
              ? "Preparação de aprovação e publicação"
              : "Preparação de encaminhamento à revisão"}
          </h3>
          <p>
            {report.id} · versão {report.version} · {total} pares incluídos.
          </p>
          <p className="prepared-reason">{notes.trim()}</p>
          <div className="evidence-note">
            <CircleAlert size={17} />
            <p>
              Nenhuma alteração foi aplicada. O parecer mantém a situação
              original, e o portal da contratante continua exibindo somente os
              exemplos previamente publicados. A ação real depende da API, da
              autorização do analista e da auditoria.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
