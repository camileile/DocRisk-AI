# Benchmark TextLayer do lote de 100 trabalhadores

## Escopo e amostra

- Medido: processamento local com `AI_PROVIDER=textlayer`; não houve chamada ao Gemini.
- Amostra: lote totalmente sintético, gerado por `gerar_parametrizado`; semente 2026.
- Distribuição: {"divergencia": 15, "faltante": 5, "ilegivel": 5, "normal": 70, "reais": 5}.
- Uso correto: medição de vazão local e conferência contra o gabarito gerado para este lote.
- Limite: os acertos neste conjunto sintético não medem precisão visual nem generalização para documentos reais.

## Corpus representativo de desenvolvimento (D1-08)

- Inventário sintético: 7 casos, 9 páginas; distribuição por caso: {"ambiguidade": 1, "ausencia_documento": 1, "ausencia_pagina": 1, "campo_so_em_reais": 1, "multipagina": 1, "rotacao": 1, "scan": 1}.
- Cobertura: 1 página(s) sem camada de texto (scan) e 2 página(s) com rotação; multipágina, página/documento ausente, identidade ambígua e campo de horas apenas em reais.
- PDF de desenvolvimento SHA-256: `20902f08e8502d91efcef1e892dd5f0b86b527663ced2326eba64ce7d6201489`; semente 1808.
- Esta seção registra a cobertura; o benchmark de desempenho continua medindo o lote sintético de 100 trabalhadores. O holdout congelado não é carregado nem pontuado por este script.

## Execução

- Data: 2026-11-06 08:04:08 UTC
- Leitor: `textlayer` (determinístico, sem chamadas de IA remotas)
- Ambiente: Python 3.13.5, Windows-10-10.0.19045-SP0, processador `AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD`
- Lote: 300 páginas, 100 trabalhadores, 300 documentos; status `CONCLUIDO`
- Tempo total medido: 26.00 s
- Vazão: 692.3 páginas/min
- Tempo médio: 86.7 ms/página
- Segmentação: 4.3 ms
- Conciliação: 17.2 ms
- Páginas lidas sem erro: 300/300

## Acurácia contra `gabarito.json`

- Fronteiras de documento exatas: 100.0% (300/300)
- Tipos de documento: 100.0% (300/300)
- Conciliação (status e resultado): 100.0% (100/100)

## Métricas detalhadas D1-09

- Fronteiras exatas: precisão 100.0%, recall 100.0% (300 corretas; 300 previstas; 300 esperadas).
- Tipo por documento, alinhado pela primeira página:

| Tipo | Precisão | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| COMPROVANTE_PAGAMENTO | 100.0% | 100.0% | 100 | 0 | 0 |
| ESPELHO_PONTO | 100.0% | 100.0% | 100 | 0 | 0 |
| HOLERITE | 100.0% | 100.0% | 100 | 0 | 0 |

- Campos numéricos usam tolerância absoluta 0.01; valores ausentes contam como FN e MAE usa os pares numéricos previstos.

| Campo | Precisão | Recall | MAE |
|---|---:|---:|---:|
| `horas_extras_h` | 100.0% | 94.9% | 0.000 |
| `horas_extras_valor` | 100.0% | 95.0% | 0.000 |
| `valor_liquido` | 100.0% | 95.0% | 0.000 |
| `valor_pago` | 100.0% | 100.0% | 0.000 |

- Associação ao trabalhador: precisão 100.0%, recall 100.0% (TP 300, FP 0, FN 0).
- Revisão humana: taxa 3.3%; precisão 100.0%; recall 100.0%.
- Falsos alertas de revisão: 0 (taxa 0.0%); falsos negativos de revisão: 0.
- Avaliação sobre gabarito sintético fixo do lote de desenvolvimento; não estima desempenho em documentos reais. O holdout D1-08 não é carregado.
## Estimativa de custo Gemini (não medida)

- Resolução de renderização: aproximadamente 1239×1754 px (150 DPI)
- Tokens visuais estimados: 1548 por página (6 blocos × 258 tokens)
- Modelo/preço: Gemini 3.5 Flash, entrada padrão, US$ 1.50/1M tokens
- Estimativa: US$ 0.002322/página; US$ 0.6966/300 páginas
- A estimativa inclui apenas tokens visuais; prompt e saída JSON não estão incluídos. Não é resultado de execução do Gemini. Preço e regra visual consultados em 2026-11-06 na [tabela oficial](https://ai.google.dev/gemini-api/docs/pricing) e na [documentação de tokens de imagem](https://ai.google.dev/gemini-api/docs/tokens).

## Reprodução

```powershell
cd api
python scripts/benchmark.py
```

O benchmark falha com exceção se o PDF não tiver 300 páginas, se houver erro de leitura ou se o lote não chegar a `CONCLUIDO`.
