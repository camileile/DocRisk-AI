import { analysisStatusLabels, formatDate, formatHours, resultLabels, typeLabels, type ReportContent } from "@/lib/api";

const SUMMARY: [string, string][] = [
  ["trabalhadores", "Trabalhadores no contrato"],
  ["avaliados", "Avaliados"],
  ["com_divergencia", "Com divergência a verificar"],
  ["dados_insuficientes", "Dados insuficientes"],
  ["sem_divergencia", "Sem divergência nos campos comparados"],
  ["bloqueados", "Bloqueados por pendência documental"],
  ["em_revisao", "Em revisão humana"],
  ["aguardando_documentos", "Aguardando documentos"],
];

export function ReportView({ content, draft = false }: { content: ReportContent; draft?: boolean }) {
  return (
    <article className="report-document">
      {draft && <p className="report-draft-flag">PRÉVIA DO RASCUNHO — não visível à contratante</p>}
      <header className="report-document-header">
        <span className="eyebrow">PARECER DOCUMENTAL · COMPETÊNCIA {content.competencia}</span>
        <h2>{content.contrato.nome}</h2>
        <p>
          Contratante: {content.contratante} · Fornecedora: {content.fornecedora} · Regra {content.regra} · gerado em{" "}
          {formatDate(content.gerado_em)}
        </p>
      </header>
      <section>
        <h3>Escopo</h3>
        <p>{content.escopo}</p>
      </section>
      <section>
        <h3>Resumo</h3>
        <table className="data-table compact">
          <tbody>
            {SUMMARY.map(([key, label]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td>{content.resumo[key] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h3>Por trabalhador</h3>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Trabalhador</th>
                <th>Situação</th>
                <th>Ponto</th>
                <th>Holerite</th>
                <th>Diferença</th>
                <th>Observação</th>
                <th>Evidências</th>
              </tr>
            </thead>
            <tbody>
              {content.itens.map((item) => (
                <tr key={item.trabalhador_id}>
                  <td>{item.trabalhador_id}</td>
                  <td>
                    {item.situacao === "ANALISADA"
                      ? resultLabels[item.resultado] ?? item.resultado
                      : analysisStatusLabels[item.situacao] ?? item.situacao}
                  </td>
                  <td>{formatHours(item.horas_ponto)}</td>
                  <td>{formatHours(item.horas_folha)}</td>
                  <td>{formatHours(item.diferenca_h)}</td>
                  <td>{item.detalhe}</td>
                  <td>
                    {item.evidencias.length === 0
                      ? "—"
                      : item.evidencias
                          .map((e) => `${typeLabels[e.tipo] ?? e.tipo} v${e.versao} (lote ${e.lote}, p. ${e.paginas.join(",")})`)
                          .join("; ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="report-limitations">
        <h3>Limitações</h3>
        <ul>
          {content.limitacoes.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
    </article>
  );
}
