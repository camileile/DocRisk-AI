# DocRisk AI

Hack Garanhuns Tech 2026 · Desafio 3 — Document AI Factory.

Recebe lotes de documentos misturados, separa e classifica cada documento, deixa o
texto pesquisável e, para ponto e folha de pagamento de terceirizados, concilia horas
extras por trabalhador e competência — com pendências objetivas para a fornecedora,
revisão humana na Bernhoeft e parecer publicado só depois de aprovado.

> **Somente dados sintéticos.** Nenhum documento real ou dado pessoal entra no repositório.

## Estado atual (05/11/2026, branch `fix/auditoria-integracao-geral`)

| Parte | Estado | Evidência |
|---|---|---|
| API, autenticação por token, isolamento por organização/contrato | Pronto e testado | `tests/test_f1_*.py` |
| Motor documental: render PDF/imagem/TIFF, Gemini, segmentação, roteamento, worker com retomada e cache | Integração implementada; a equipe relata teste real do Gemini em 05/11, sem relatório reproduzível versionado. Os testes automatizados usam o leitor offline. | `tests/test_f2_*.py` |
| Regras (F3): conciliação de horas extras, pendências, parecer, métricas | Pronto e testado | `tests/test_f3_regras.py` |
| Lote sintético (16 páginas, 14 documentos) + reenvio + PDF corrompido + gabarito | Pronto e versionado | `api/scripts/lote_demo/` |
| Front-end Next.js integrado à API (todos os perfis) | Pronto; smoke ponta a ponta com Playwright | `web/scripts/smoke.cjs` |
| AEJ, anonimização, base de 100 trabalhadores, PostgreSQL/fila externa | Não implementado (ver Limitações) | — |

## Estrutura e donos

```
api/
  docrisk_core/
    contracts.py        TODOS   tipos, estados, AnalisePagina (JSON da página)
    config.py           F1      variáveis de ambiente
    db/                 F1      schema.sql + conexão + dados demo
    auth.py             F1      token, organização + contrato + papel, auditoria
    routes/             F1      rotas da API (mapa no __init__.py)
    api.py              F1      app FastAPI, CORS, lifespan (worker)
    ai/                 F2      Gemini (principal), camada de texto (testes), Tesseract (opcional)
    pipeline/           F2      render, segmentação, roteamento, worker com retomada
    importer.py, documents.py, aej.py, cli.py   sprint01 (F2 reaproveita; AEJ é P1)
    rules/              F3      conciliação, pendências, parecer, métricas
  scripts/              F3      gerador do lote sintético + gabarito
  tests/                F3      (cada frente testa o que entrega)
docs/                           sprint01, decisões, entregas
web/                            Next.js: institucional + telas do Trabalhista ligadas à API
```

**F1 — API, banco e segurança · F2 — motor documental e IA · F3 — regras, dados e testes.**

Funções que ligam as frentes (não mudar a assinatura sem combinar):

- `pipeline.worker.criar_lote(usuario, contract_id, filename, data, issue_id=None) -> batch_id` — F2, chamada pelas rotas de F1
- `pipeline.worker.processar_lote(batch_id)` e `enfileirar(batch_id)` — F2
- `pipeline.segmentation.segmentar(analises) -> list[SegmentoDocumento]` — F2, função pura
- `pipeline.worker.consolidar_lote(conn, batch_id) -> pares afetados` — F2, chama F3
- `rules.pendencias.criar_pendencia(conn, ...)` — F3, chamada por F2 e pela revisão
- `rules.conciliacao.conciliar(conn, contract_id, worker_id, competencia)` — F3
- `rules.parecer.snapshot_parecer(conn, contract_id, competencia)` e `rules.metricas.calcular_metricas(conn, contratos)` — F3, chamadas pelas rotas de F1

## Como rodar (Windows)

API:

```powershell
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"
copy ..\.env.example .env      # preencha GEMINI_API_KEY (Google AI Studio)
pytest -q
uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000   # http://127.0.0.1:8000/docs
```

Sem internet ou sem cota do Gemini, rode a API com o leitor offline (regras sobre o texto
digital do PDF — **não é IA**, serve para testes e plano B): `$env:AI_PROVIDER="textlayer"`.

Front-end (outro terminal):

```powershell
cd web
npm ci
npm run dev        # http://127.0.0.1:3000 (usa NEXT_PUBLIC_API_URL, padrão http://127.0.0.1:8000)
```

Roteiro de demonstração: em `/acesso`, entre como **Operador da fornecedora** e envie
`api/scripts/lote_demo/lote_demo.pdf`; em *Pendências*, reenvie
`reenvio_holerite_T002.pdf` na pendência do holerite ilegível; entre como **Analista
Bernhoeft** e veja *Conciliações* (T001: 4 h a conferir; T003 bloqueado; T004 dados
insuficientes), aprove a anotação na *Fila de revisão*, busque "T001" em *Documentos* e
publique o parecer em *Pareceres*; entre como **Gestor da contratante** para ver só o
parecer publicado; **Administrador** vê a trilha de auditoria.
Para regenerar o lote: `python scripts/gerar_lote_demo.py`.

Smoke ponta a ponta (API em 8000 com `AI_PROVIDER=textlayer`, `DOCRISK_DEMO_MODE=1`,
banco limpo e `CORS_ORIGINS=http://127.0.0.1:4173`; front exportado em 4173):
`npm run build`, `python -m http.server 4173 --directory out` e `node scripts/smoke.cjs`.

Tesseract é **opcional** (o leitor principal é o Gemini). O teste de OCR local é
pulado automaticamente se o Tesseract não estiver instalado.

**Nunca** use `--host 0.0.0.0` nem publique a API: é um protótipo de hackathon.

## Limitações conhecidas

- Autenticação por token fixo de demonstração (`/api/demo/users` só com `DOCRISK_DEMO_MODE=1`); produção = SSO/OIDC.
- SQLite + fila em thread única por processo: rode **um** processo da API. Produção: PostgreSQL, fila externa (Celery/Redis) e armazenamento de objetos.
- Os testes automatizados usam o leitor offline. A qualidade visual do Gemini não é medida no CI nem pelo benchmark TextLayer; falta um relatório versionado da validação real relatada pela equipe. O holerite "ilegível" do lote é um corpo borrado.
- AEJ, anonimização e a base de 100 trabalhadores ainda não foram implementados.
- Pendência de `DOCUMENTO_AUSENTE` nasce `ABERTA` (aguarda o analista); não há notificação por e-mail.

## Regras do projeto

- IA lê a página; **regras em Python decidem** fronteiras, bloqueios e conciliação.
- Toda rota confere organização + contrato + papel **no back-end**.
- Chave do Gemini só no `.env` (fora do Git).
- Resultado sempre com evidência (documento, versão, página). Divergência é **indício a conferir**, nunca passivo ou infração.

Documentação de arquitetura e tecnologias: doc "DocRisk AI — Tecnologias e Arquitetura" da equipe.
