# D1-06 — revisão estruturada de campos

Analistas podem corrigir valores extraídos pela rota `PATCH /api/documents/{id}/review`:

```json
{
  "acao": "corrigir_campos",
  "campos": {"horas_extras_h": 10, "horas_extras_valor": 150.5},
  "motivo": "Conferido no comprovante",
  "fonte": "Holerite, página 2"
}
```

Os campos aceitos são `horas_extras_h`, `horas_extras_valor`, `valor_liquido`, `valor_pago` e `data_pagamento`. O backend valida valores, registra cada alteração em `document_field_reviews` e atualiza `documents.campos_json` na mesma transação. Cada registro guarda valor anterior e corrigido, autor, motivo, fonte, revisão e versão do documento. A rota de detalhe retorna esse histórico somente para usuários da Bernhoeft.

Ao corrigir um documento de foco com trabalhador e competência, a conciliação desse par é recalculada. A correção não aprova o documento por si só. Testes cobrem campos múltiplos, revisões sucessivas, preservação dos valores anteriores, validação, acesso ao histórico e recálculo.
