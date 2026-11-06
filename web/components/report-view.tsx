import { analysisStatusLabels, formatDate, formatHours, resultLabels, typeLabels, type ReportContent, type Report } from "@/lib/api";

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

export function ReportView({ content, draft = false, report }: { content: ReportContent; draft?: boolean; report?: Pick<Report, "id" | "versao"> }) {
  return (
    <article className="report-document">
      {draft && <p className="report-draft-flag">PRÉVIA DO RASCUNHO — não visível à contratante</p>}
      <header className="report-document-header">
        <img className="report-brand" src="/brand/logo-horizontal-claro.svg" width="180" height="44" alt="DocRisk AI" />
        <p>Parecer #{content.parecer?.id ?? report?.id ?? "não registrado"} · versão {content.parecer?.versao ?? report?.versao ?? "não registrada"}</p>
        <span className="eyebrow">PARECER DOCUMENTAL · COMPETÊNCIA {content.competencia}</span>
        <h2>{content.contrato.nome}</h2>
        <p>
          Contratante: {content.contratante} · Fornecedora: {content.fornecedora} · Regra {content.regra} · gerado em{" "}
          {formatDate(content.gerado_em)}
        </p>
        <dl className="report-responsibility">
          <dt>Organização responsável</dt><dd>{content.parecer?.emissor ?? "Não registrada nesta versão"}</dd>
          <dt>Autor</dt><dd>{content.parecer?.autor.nome ?? "Não registrado nesta versão"}</dd>
          <dt>Responsável pela conferência</dt><dd>{content.parecer?.responsavel.nome ?? "Não registrado nesta versão"}</dd>
        </dl>
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
        <h3>Recomendações</h3>
        {content.recomendacoes?.length ? <ul>{content.recomendacoes.map((line,index) => <li key={index}>{line}</li>)}</ul> : <p>Recomendações não registradas nesta versão.</p>}
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
                          .map((e) => e.origem === "AEJ"
                            ? (typeLabels[e.tipo] ?? e.tipo) + " v" + e.versao + " (lote " + e.lote + ", AEJ vínculo " + e.vinculo_aej + ", linhas " + (e.linhas_origem?.join(",") ?? "") + ")"
                            : (typeLabels[e.tipo] ?? e.tipo) + " v" + e.versao + " (lote " + e.lote + ", p. " + e.paginas.join(",") + ")")
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
