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

- Data: 2026-11-06 07:48:23 UTC
- Leitor: `textlayer` (determinístico, sem chamadas de IA remotas)
- Ambiente: Python 3.13.5, Windows-10-10.0.19045-SP0, processador `AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD`
- Lote: 300 páginas, 100 trabalhadores, 300 documentos; status `CONCLUIDO`
- Tempo total medido: 21.39 s
- Vazão: 841.7 páginas/min
- Tempo médio: 71.3 ms/página
- Segmentação: 3.9 ms
- Conciliação: 16.1 ms
- Páginas lidas sem erro: 300/300

## Acurácia contra `gabarito.json`

- Fronteiras de documento exatas: 100.0% (300/300)
- Tipos de documento: 100.0% (300/300)
- Conciliação (status e resultado): 100.0% (100/100)

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
