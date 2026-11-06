# DocRisk AI

Hack Garanhuns Tech 2026 · Desafio 3 — Document AI Factory.

Recebe lotes de documentos misturados, separa e classifica cada documento, deixa o
texto pesquisável e, para ponto e folha de pagamento de terceirizados, concilia horas
extras por trabalhador e competência — com pendências objetivas para a fornecedora,
revisão humana na Bernhoeft e parecer publicado só depois de aprovado.

> **Somente dados sintéticos.** Nenhum documento real ou dado pessoal entra no repositório.

## Estado atual

| Parte | Estado |
|---|---|
| Importação PDF / imagem / AEJ (sprint01) | Funciona como prova de conceito (`api/docrisk_core/importer.py`, `documents.py`, `aej.py`) |
| Contratos compartilhados (tipos, estados, JSON da página) | Pronto — `api/docrisk_core/contracts.py` |
| Esquema do banco + dados demo | Pronto — `api/docrisk_core/db/` |
| Auth, rotas, IA, segmentação, worker, regras, gerador do lote | **Assinaturas definidas, implementação pendente** (cada função diz o critério de aceite) |
| Front-end Next.js | Landing, contato e nove telas demonstrativas do Trabalhista prontas (`web/`); autenticação e integração operacional pendentes |

## Estrutura e donos

```
api/
  docrisk_core/
    contracts.py        TODOS   tipos, estados, AnalisePagina (JSON da página)
    config.py           F1      variáveis de ambiente
    db/                 F1      schema.sql + conexão + dados demo
    auth.py             F1      token, organização + contrato + papel, auditoria
    routes/             F1      rotas da API (mapa no __init__.py)
    api.py              F1      app FastAPI (hoje: /health e /api/v1/inspect do sprint01)
    ai/                 F2      Gemini (principal), camada de texto (testes), Tesseract (opcional)
    pipeline/           F2      render, segmentação, roteamento, worker com retomada
    importer.py, documents.py, aej.py, cli.py   sprint01 (F2 reaproveita; AEJ é P1)
    rules/              F3      conciliação, pendências, parecer, métricas
  scripts/              F3      gerador do lote sintético + gabarito
  tests/                F3      (cada frente testa o que entrega)
docs/                           sprint01, decisões, entregas
web/                            Next.js: institucional + telas demonstrativas do Trabalhista
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

```powershell
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"
copy ..\.env.example .env      # preencha GEMINI_API_KEY (Google AI Studio)
pytest -q
uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000   # http://127.0.0.1:8000/docs
```

Tesseract é **opcional** (o leitor principal é o Gemini). O teste de OCR local é
pulado automaticamente se o Tesseract não estiver instalado.

**Nunca** use `--host 0.0.0.0` nem publique a API: é um protótipo de hackathon.

## Regras do projeto

- IA lê a página; **regras em Python decidem** fronteiras, bloqueios e conciliação.
- Toda rota confere organização + contrato + papel **no back-end**.
- Chave do Gemini só no `.env` (fora do Git).
- Resultado sempre com evidência (documento, versão, página). Divergência é **indício a conferir**, nunca passivo ou infração.

Documentação de arquitetura e tecnologias: doc "DocRisk AI — Tecnologias e Arquitetura" da equipe.
