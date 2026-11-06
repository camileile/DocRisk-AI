# Benchmark TextLayer do lote de 100 trabalhadores

## Escopo e amostra

- Medido: processamento local com `AI_PROVIDER=textlayer`; não houve chamada ao Gemini.
- Amostra: lote totalmente sintético, gerado por `gerar_parametrizado`; semente 2026.
- Distribuição: {"divergencia": 15, "faltante": 5, "ilegivel": 5, "normal": 70, "reais": 5}.
- Uso correto: medição de vazão local e conferência contra o gabarito gerado para este lote.
- Limite: os acertos neste conjunto sintético não medem precisão visual nem generalização para documentos reais.

## Execução

- Data: 2026-11-06 06:31:02 UTC
- Leitor: `textlayer` (determinístico, sem chamadas de IA remotas)
- Ambiente: Python 3.13.14, Windows-11-10.0.26300-SP0, processador `AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD`
- Lote: 300 páginas, 100 trabalhadores, 300 documentos; status `CONCLUIDO`
- Tempo total medido: 19.75 s
- Vazão: 911.3 páginas/min
- Tempo médio: 65.8 ms/página
- Segmentação: 5.0 ms
- Conciliação: 28.1 ms
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
