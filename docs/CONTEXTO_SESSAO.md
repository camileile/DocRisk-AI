# DocRisk AI — Contexto da sessão (05/11/2026)

Resumo para continuar o trabalho em outro computador ou em outra conversa com o Claude.
Atualizado no fim do dia 1 do Hack Garanhuns Tech 2026.

## Como retomar com o Claude

Abra o Claude Code na pasta do repositório e mande:

> Leia `docs/CONTEXTO_SESSAO.md`, `docs/F2_INTEGRACAO.md` e o `README.md`. Eu sou a responsável pela F2 (motor documental e IA) e coordeno o time. Continue a partir do "Próximos passos".

## 1. O hackathon

- **Evento:** Hack Garanhuns Tech 2026, SEBRAE Garanhuns. Dia 1 em 05/11 (15h–22h); dia 2 em 06/11 (9h–16h).
- **Dia 2:** check-in às 9h · Checkpoint 3 às 11h (testes, segurança, ensaio) · **code freeze às 12h** (repositório, instruções e slides) · pré-banca às 13h · **Demo Day às 13h45** (pitch de 8 minutos, demo obrigatória) · resultado às 15h40.
- **Desafio escolhido:** 3 — Document AI Factory. Receber lotes de imagens e PDFs misturados, separar cada documento, classificar, gerar OCR pesquisável, com confiança e fila de revisão humana. Os diferenciais citados nos slides são modelos multimodais, retomada após falha e anonimização.
- **Critérios da banca** (0 a 5 cada; desempate por Inovação): pertinência, inovação, impacto e abrangência, viabilidade, pitch, escalabilidade e robustez técnica. Esse último pede arquitetura justificada, gargalos, tratamento de falhas e caminho até produção.
- **Entregáveis:** MVP demonstrável, pitch, repositório GitHub com instruções e registro de premissas, limitações, riscos e próximos passos.
- **Prêmios:** R$ 3.000, R$ 1.500 e R$ 500. Os 5 melhores vão ao AgresTI; os 3 melhores de lá vão ao FING.

## 2. O produto

Especificação da equipe: *DocRisk AI — Especificação de Produção v0.3*.

- **Foco de negócio:** apoiar a Bernhoeft na gestão de risco trabalhista de terceirizados. O motor organiza qualquer documento, mas a análise especializada é só de **ponto, holerite e comprovante de pagamento**.
- **Perfis:** Admin Bernhoeft, Analista Bernhoeft, Gestor e Operador da fornecedora, Gestor da contratante.
- **Fluxo:** fornecedora envia o lote → motor separa, classifica e faz OCR → erro objetivo vira **pendência devolvida à fornecedora**; incerteza vai para **revisão humana na Bernhoeft** → conciliação de horas extras por trabalhador e competência, com **bloqueio seletivo** → analista publica o parecer → contratante vê só a versão publicada.
- **Princípios:** a IA lê a página e as regras em Python decidem. Divergência é **indício a conferir**, nunca passivo. Horas nunca são comparadas com reais. Só dados sintéticos.
- **Documento de arquitetura:** "DocRisk AI — Tecnologias e Arquitetura" (claude.ai): https://claude.ai/artifact/AtgyV4k37Z4hjC6CpMhNk5

## 3. Stack

| Camada | Tecnologia |
|---|---|
| Back-end | Python + FastAPI (`api/`) |
| Leitura de páginas | **Gemini** (`gemini-3.5-flash`), com `textlayer` offline para testes e `tesseract` opcional |
| PDF e imagem | PyMuPDF (`import pymupdf as fitz`) + Pillow |
| Banco e busca | SQLite + FTS5 |
| Fila | Thread em segundo plano, com estado por página e cache em `ai_cache` |
| Front | Next.js + TypeScript com CSS próprio (`web/`), em exportação estática |

## 4. Frentes e situação (fim do dia 1)

| Frente | Quem | Situação |
|---|---|---|
| F2 — motor documental e IA | Camile | ✅ Na `main` (PRs #1 e #5). Separação, classificação, roteamento, worker com retomada e cache, dividir e unir na revisão. Gemini validado com chamada real. |
| F1 — API, autenticação e segurança | Rômulo | ✅ Base na `main` (PR #4). ⏳ Falta a branch `fix/f1-revisao` com as correções da seção 6. |
| Front | Jader | ✅ Telas demonstrativas na `main` (PRs #2 e #3), ainda **sem integração com a API**. ⏳ Branch `feat/web-admin-auditoria` (16 commits, com Playwright e CI) aberta e **não revisada**. |
| F3 — regras, dados e testes | a definir | ❌ **Nada entregue.** `rules/conciliacao.py`, `pendencias.py`, `parecer.py`, `metricas.py` e `scripts/gerar_lote_demo.py` ainda levantam `NotImplementedError`. Obs.: a branch `feat/conciliacoes` era do front, não da F3. |

**Testes:** `cd api; pip install -e ".[test]"; pytest -q`. São 120 passando e 1 pulado (o OCR com Tesseract, que não está instalado).

### Resultados da F2 com o Gemini real (lote de 8 páginas, 113 s)
- O contrato de 2 páginas e o ponto do T001 de 2 páginas foram agrupados corretamente, com 12 h. No holerite do T001, 8 h e R$ 160 ficaram separados.
- O ponto do T003 "1 de 2" sem a página 2 virou **pendência de página faltante**.
- Falhas 503 e 429 do Google foram recuperadas automaticamente.
- Corrigido depois desse teste: o tipo `OUTRO` e documento de foco sem nenhum campo agora vão para revisão.
- **Ainda não testado:** o holerite **visualmente** ilegível (corpo em baixa resolução) que a F3 vai gerar.

## 5. O que a F3 precisa entregar (prioridade máxima para a demo)

As assinaturas estão definidas nos arquivos e o worker da F2 já chama as funções (`pipeline/integracao_f3.py`). Enquanto elas não existem, a etapa é pulada e o log avisa.

1. `scripts/gerar_lote_demo.py`: 16 páginas e 14 documentos (tabela no próprio arquivo), com "Página X de Y" no rodapé, holerite do T002 com o corpo ilegível, o reenvio do T002, um PDF corrompido e o `gabarito.json`. **Sem isso não há demo.**
2. `rules/conciliacao.py`: `avaliar_horas_extras` e `conciliar`. Resultados esperados: T001 com divergência de 4 h, T002 e T003 bloqueados, T004 com dados insuficientes, T005 sem divergência.
3. `rules/pendencias.py`: `criar_pendencia`, `atualizar_por_nova_versao` e `resolver_ausencia`.
4. `rules/parecer.py` (`snapshot_parecer`) e `rules/metricas.py` (`calcular_metricas`).

Plano B se ninguém pegar a F3: a Camile assume com o Claude, começando pelo gerador e pela conciliação.

## 6. Tarefa do Rômulo (`fix/f1-revisao`), já enviada a ele

1. `aprovar`: só aceitar `REVISAO_HUMANA` e `PENDENTE_CORRECAO` (409 nos demais). Aceitar correção de tipo, trabalhador e competência. Responder 422 para `DESCONHECIDO`, para foco sem trabalhador ou competência e para trabalhador fora do contrato. Resolver as pendências do documento.
2. Depois de `aprovar` e `solicitar_correcao`, chamar `pipeline.integracao_f3.conciliar`.
3. `dividir` e `unir_proximo`: trocar `_edit_document_pages` por `pipeline.revisao.dividir` e `unir_proximo`, convertendo `RevisaoInvalida` em 409 ou 422. Código pronto em `docs/F2_INTEGRACAO.md`.
4. Incluir `paginas: [{page_id, ordem}]` nos documentos e na fila de revisão.
5. Criar `POST /api/batches/{id}/reprocess`, só para lotes `FALHA_PROCESSAMENTO`.
6. Criar `GET /api/reports` para o analista e converter `conteudo_json` em objeto.
7. No reenvio, mudar a pendência para `REENVIADA` e registrar no histórico.
8. Busca com marcadores `[[ ]]` em vez de `<b>`. O front nunca deve renderizar esse trecho como HTML.
9. Opcional: chamar `worker.parar_worker()` no `lifespan`.

## 7. Pendências do front (Jader) para a integração

1. Contratos, organizações e trabalhadores devem vir da API (`CT-001`; Alfa é a contratante, Beta e Gama são fornecedoras; trabalhadores `T001`…), e não de `lib/demo.ts`.
2. No envio: aceitar TIFF e não aceitar AEJ, um arquivo por lote, limite de 50 MB.
3. `/painel/lotes/[id]` com `output: "export"` só funciona para os lotes de exemplo. Trocar para `?id=` ou tirar a exportação estática.
4. Incluir os estados `NOTIFICADA`, `REABERTA` e `SUBSTITUIDO`.
5. Tirar `--hostname 0.0.0.0` do `npm run dev`.
6. Exibir as imagens de página por `/api/pages/{id}/image` com o token, como blob.
7. Revisar o PR `feat/web-admin-auditoria` antes do merge.

## 8. Configuração local (o que NÃO vai pelo git)

- **`api\.env`:** copiar de `.env.example` e preencher `GEMINI_API_KEY` (gerada em https://aistudio.google.com). Usar `GEMINI_MODEL=gemini-3.5-flash`, porque o `gemini-2.5-flash` aparece na lista mas devolve 404 nesta conta.
- **Testar a chave:** dentro de `api\`, rodar `python -m docrisk_core.ai.poc_gemini --modelos` e depois `python -m docrisk_core.ai.poc_gemini`.
- **Git no notebook:** só existe o do GitHub Desktop, em `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`. Há um `git stash` com `web/next-env.d.ts`, que é gerado pelo `next dev` e pode ser descartado.
- **Nunca** colar a chave em chat nem fazer commit do `.env`.

## 9. Próximos passos (em ordem)

1. **Definir quem faz a F3** e começar pelo gerador do lote sintético e pela conciliação. Sem eles, a demo não mostra o valor do produto.
2. Rômulo: PR `fix/f1-revisao` → revisar → merge.
3. Jader: revisar `feat/web-admin-auditoria`, depois integrar o front com a API (seção 7).
4. Rodar o lote da F3 pelo pipeline com o Gemini e com o `textlayer`, conferir com o gabarito e anotar as métricas reais para o pitch (acerto de fronteiras e de tipos, taxa de revisão, tempo por página).
5. Ensaiar a demo com o lote **já processado** (cache), para não depender da internet nem da cota do Gemini na hora do pitch.
6. Antes do code freeze (12h): README com instruções, limitações, riscos e próximos passos; slides com um slide de escalabilidade (SQLite→PostgreSQL, thread→Celery/Redis, pasta→S3, plano gratuito do Gemini→contrato pago).

## 10. Mapa rápido de arquivos

- `api/docrisk_core/contracts.py`: tipos, estados e `AnalisePagina`, compartilhados por todas as frentes.
- `api/docrisk_core/db/schema.sql`: o banco.
- `api/docrisk_core/pipeline/`: `render`, `segmentation`, `routing`, `worker`, `revisao`, `integracao_f3` (F2).
- `api/docrisk_core/ai/`: `gemini`, `textlayer`, `tesseract` e `poc_gemini` (F2).
- `api/docrisk_core/routes/__init__.py` e `auth.py`: API e segurança (F1).
- `api/docrisk_core/rules/` e `api/scripts/`: F3.
- `docs/F2_INTEGRACAO.md`: como a F1 e a F3 chamam a F2.
- `web/`: front.
