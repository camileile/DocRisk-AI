import {
  publicStateLabels,
  publicResultLabels,
  summarizeReport,
  type PublicItem,
} from "@/lib/published-reports";
export type ReportContentData = {
  id: string;
  series: string;
  version: number;
  contract: string;
  competence: string;
  client: string;
  supplier: string;
  rule: string;
  scope: string;
  limitations: string;
  items: PublicItem[];
};
export function ReportContent({ report }: { report: ReportContentData }) {
  const summary = summarizeReport(report.items);
  return (
    <div className="report-content">
      <section className="workspace-card report-document">
        <div className="report-document-header">
          <img
            src="/brand/logo-horizontal-claro.svg"
            alt="DocRisk AI"
            width="165"
            height="43"
          />
          <span>EXEMPLO SINTÉTICO · {report.id}</span>
        </div>
        <h2>Parecer de acompanhamento documental</h2>
        <p className="report-document-lead">
          Trabalhista · competência {report.competence}
        </p>
        <dl className="detail-list report-identification">
          <div>
            <dt>Contratante</dt>
            <dd>{report.client}</dd>
          </div>
          <div>
            <dt>Fornecedora</dt>
            <dd>{report.supplier}</dd>
          </div>
          <div>
            <dt>Contrato / versão</dt>
            <dd>
              {report.contract} · versão {report.version}
            </dd>
          </div>
          <div>
            <dt>Regra de referência</dt>
            <dd>{report.rule}</dd>
          </div>
        </dl>
        <section className="report-text-section">
          <h3>Escopo da conferência</h3>
          <p>{report.scope}</p>
        </section>
        <section className="report-text-section">
          <h3>Resumo do acompanhamento</h3>
          <div className="report-summary-grid">
            {[
              { label: "Total acompanhado", value: summary.total },
              { label: "Avaliados", value: summary.evaluated },
              { label: "Bloqueados", value: summary.blocked },
              { label: "Em revisão", value: summary.review },
              { label: "Aguardando documentos", value: summary.waiting },
            ].map((item) => (
              <div key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
          <p className="report-denominator">
            {summary.evaluated} de {summary.total} pares avaliados. Os{" "}
            {summary.blocked + summary.review + summary.waiting} pares restantes
            continuam no total acompanhado.
          </p>
          <div className="report-outcome-counts">
            <span>
              Indícios a conferir <b>{summary.divergence}</b>
            </span>
            <span>
              Dados insuficientes <b>{summary.insufficient}</b>
            </span>
            <span>
              Sem divergência nos campos <b>{summary.matching}</b>
            </span>
          </div>
        </section>
        <section className="report-text-section">
          <h3>Itens por trabalhador</h3>
          {report.items.length ? (
            report.items.map((item) => (
              <article className="report-worker-item" key={item.worker}>
                <div>
                  <h4>{item.worker}</h4>
                  <span
                    className={`status-badge ${item.state === "BLOQUEADO" ? "warning" : item.state === "EM_REVISAO" ? "review" : "neutral"}`}
                  >
                    <i />
                    {publicStateLabels[item.state]}
                  </span>
                </div>
                <strong>{publicResultLabels[item.result]}</strong>
                <p>{item.note}</p>
                <div className="report-evidence">
                  <span>Referências documentais</span>
                  {item.evidence.length ? (
                    <ul>
                      {item.evidence.map((e) => (
                        <li key={e.document}>
                          {e.document} · {e.batch} · página {e.page} · versão{" "}
                          {e.version}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>Nenhum documento recebido neste exemplo.</p>
                  )}
                </div>
              </article>
            ))
          ) : (
            <p>Nenhum par incluído neste exemplo.</p>
          )}
        </section>
        <section className="report-text-section report-limitations">
          <h3>Limitações e alcance</h3>
          <p>{report.limitations}</p>
        </section>
        <div className="report-synthetic-note">
          Documento demonstrativo com dados sintéticos. As referências
          identificam os insumos do exemplo.
        </div>
      </section>
    </div>
  );
}
