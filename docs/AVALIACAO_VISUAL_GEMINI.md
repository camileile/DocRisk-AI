# Avaliação visual Gemini — corpus sintético

- Status: **BLOQUEADA_SEM_CREDENCIAL**
- Data UTC: 2026-11-06T06:47:22+00:00
- Leitor: Gemini real via `GeminiProvider`; nenhum mock ou fallback.
- Modelo configurado: `gemini-3.5-flash`
- Corpus: 16 páginas de documentos fictícios renderizados do PDF a 150 DPI.
- Casos: contrato multipágina, ponto multipágina, holerite borrado, comprovante, identidade, página faltante, horas apenas em R$ e anotação sem tipo claro.
- Dados pessoais reais: nenhum.

## Bloqueio

Não foi encontrada `GEMINI_API_KEY` no ambiente nem em `api/.env`. Nenhuma chamada foi enviada; não existem tempos ou acurácia Gemini nesta execução.
O identificador de modelo é o valor configurado localmente; não foi validado na conta. Cota e cobrança também não foram consultadas.

Para executar quando houver credencial, modelo e cota autorizados:

```powershell
cd api
.\.venv\Scripts\python.exe scripts/avaliar_gemini_visual.py --executar
```

`--executar` opta por chamadas reais, uma por página, e pode gerar cobrança da conta configurada. Sem essa opção, o script não chama a rede.
