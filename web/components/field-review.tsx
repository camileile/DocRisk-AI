"use client";
import { useState } from "react";
import { formatDate, type Campos, type DocDetail } from "@/lib/api";

const LABELS: Record<keyof Campos, string> = {
  horas_extras_h: "Horas extras (h)", horas_extras_valor: "Horas extras (R$)",
  valor_liquido: "Valor líquido (R$)", valor_pago: "Valor pago (R$)", data_pagamento: "Data de pagamento (DD/MM/AAAA)",
};
export function FieldReview({ doc, disabled, onSave, onSelectPage }: {
  doc: DocDetail; disabled: boolean; onSave: (payload: Record<string, unknown>) => void; onSelectPage: (id: number) => void;
}) {
  const fields = Object.keys(LABELS) as (keyof Campos)[];
  const [values, setValues] = useState(() => Object.fromEntries(fields.map(name => [name, String(doc.campos[name] ?? "")])));
  const [sources, setSources] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const changed = fields.filter(name => values[name] !== String(doc.campos[name] ?? ""));
  const valid = changed.every(name => sources[name] && (name === "data_pagamento" || values[name] === "" || (Number.isFinite(Number(values[name])) && Number(values[name]) >= 0)));
  function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled || !changed.length || !valid || !reason.trim()) return;
    onSave({ acao: "editar_campos", esperado_em: doc.updated_at, justificativa: reason.trim(),
      campos: Object.fromEntries(changed.map(name => [name, values[name] === "" ? null : name === "data_pagamento" ? values[name] : Number(values[name])])),
      fontes: Object.fromEntries(changed.map(name => [name, Number(sources[name])])),
    });
  }
  return (
    <section className="workspace-card field-review">
      <h2>Conferência dos campos</h2>
      <p className="muted">Os valores abaixo são os atuais. Consulte a origem antes de corrigir. Confiança por campo não disponível; a confiança da classificação não comprova a exatidão do valor.</p>
      <form onSubmit={save}>
        <fieldset>
          <legend>Valores, fontes e correções</legend>
          {fields.map(name => <div key={name} className="field-review-item">
            <label className="filter-label">{LABELS[name]}
              <input aria-label={LABELS[name]} disabled={disabled} type={name === "data_pagamento" ? "text" : "number"} min={name === "data_pagamento" ? undefined : 0} step="any"
                value={values[name]} placeholder={name === "data_pagamento" ? "DD/MM/AAAA" : "Não informado"} onChange={event => setValues(previous => ({ ...previous, [name]: event.target.value }))} />
            </label>
            {(doc.evidencias_campos?.[name] ?? []).map(source => <p className="muted" key={source.page_id}>
              <button type="button" className="field-source" onClick={() => onSelectPage(source.page_id)}>Lote p. {source.ordem}</button>
              {` · ${source.origem} · valor extraído: ${source.valor}`}
              {source.confianca_classificacao != null && ` · confiança da classificação: ${Math.round(source.confianca_classificacao * 100)}%`}
            </p>)}
            {!doc.evidencias_campos?.[name]?.length && <p className="muted">Sem fonte de extração informada para este campo.</p>}
            {changed.includes(name) && <label className="filter-label">Página conferida para {LABELS[name]}
              <select disabled={disabled} required value={sources[name] ?? ""} onChange={event => setSources(previous => ({ ...previous, [name]: event.target.value }))}>
                <option value="">Selecione a página…</option>
                {doc.paginas.map(page => <option key={page.page_id} value={page.page_id}>Página {page.ordem} do lote</option>)}
              </select>
            </label>}
          </div>)}
          <label className="filter-label">Justificativa da edição
            <textarea disabled={disabled} maxLength={500} rows={3} value={reason} onChange={event => setReason(event.target.value)} required={changed.length > 0} />
          </label>
          <p className="muted">Campo vazio significa dado ausente. Salvar a correção mantém a revisão pendente até aprovar a classificação.</p>
          <button type="submit" className="button secondary" disabled={disabled || !changed.length || !valid || !reason.trim()}>Salvar campos conferidos</button>
        </fieldset>
      </form>
      {!!doc.revisoes_campos?.length && <details><summary>Histórico de correções ({doc.revisoes_campos.length} mais recentes)</summary>
        {doc.revisoes_campos.map(review => <article key={review.id}>
          <p><strong>{review.autor}</strong> · {formatDate(review.created_at)}</p><p>{review.justificativa}</p>
          <ul>{Object.entries(review.depois).map(([name, value]) => <li key={name}>{LABELS[name as keyof Campos]}: {String(review.antes[name as keyof Campos] ?? "ausente")} → {String(value ?? "ausente")} · página de origem #{review.fontes[name as keyof Campos]}</li>)}</ul>
        </article>)}
      </details>}
    </section>
  );
}
