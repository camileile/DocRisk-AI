# Benchmark do lote de 100 trabalhadores

## Execução

- Data: 2026-11-06 04:28:06 UTC
- Leitor: `textlayer` (determinístico, sem chamadas de IA remotas)
- Lote: 300 páginas, 100 trabalhadores, 300 documentos; status `CONCLUIDO`
- Tempo total medido: 18.83 s
- Vazão: 955.8 páginas/min
- Tempo médio: 62.8 ms/página
- Segmentação: 3.6 ms
- Conciliação: 18.1 ms
- Páginas lidas sem erro: 300/300

## Acurácia contra `gabarito.json`

- Fronteiras de documento exatas: 100.0% (300/300)
- Tipos de documento: 100.0% (300/300)
- Conciliação (status e resultado): 100.0% (100/100)

## Estimativa Gemini por página

- Resolução de renderização: aproximadamente 1239×1754 px (150 DPI)
- Tokens visuais estimados: 1548 por página (6 blocos × 258 tokens)
- Modelo/preço: Gemini 3.5 Flash, entrada padrão, US$ 1.50/1M tokens
- Estimativa: US$ 0.002322/página; US$ 0.6966/300 páginas
- A estimativa inclui apenas tokens visuais; prompt e saída JSON não estão incluídos. O preço e a regra de blocos foram consultados em 2026-11-06 na [tabela oficial](https://ai.google.dev/gemini-api/docs/pricing) e na [documentação de tokens de imagem](https://ai.google.dev/gemini-api/docs/image-understanding).

## Reprodução

```powershell
cd api
python scripts/benchmark.py
```

O benchmark falha com exceção se o PDF não tiver 300 páginas, se houver erro de leitura ou se o lote não chegar a `CONCLUIDO`.
