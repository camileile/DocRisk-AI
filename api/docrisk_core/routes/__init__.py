"""Rotas da API. Dono: FRENTE 1.

Cada módulo aqui expõe um `router = APIRouter(prefix=...)` incluído em api.py.
Toda rota usa `Depends(usuario_atual)` e checa contrato/papel (auth.py).

Mapa planejado (spec 8.1) — quem implementa a regra por trás entre colchetes:

| Rota                                   | Perfis              | Chama                                   |
|----------------------------------------|---------------------|-----------------------------------------|
| GET  /api/demo/users                   | (só DEMO_MODE)      | lista personas + tokens                 |
| GET  /api/me, GET /api/contracts       | todos               | auth.contratos_do_usuario               |
| POST /api/supplier/batches             | GESTOR/OPERADOR_FORN| pipeline.worker.criar_lote + enfileirar [F2] |
| GET  /api/batches, /api/batches/{id}   | forn., Bernhoeft    | —                                       |
| GET  /api/batches/{id}/documents       | forn., Bernhoeft    | fornecedora vê EM_ANALISE, sem motivos internos |
| POST /api/batches/{id}/reprocess       | Bernhoeft, quem enviou | pipeline.worker.enfileirar [F2]      |
| GET  /api/pages/{id}/image             | forn., Bernhoeft    | arquivo privado, nunca pasta pública    |
| GET  /api/review-queue                 | ANALISTA_BH         | documents.status = REVISAO_HUMANA       |
| PATCH /api/documents/{id}/review       | ANALISTA_BH         | aprovar / dividir / unir / solicitar_correcao [F2+F3] |
| GET  /api/supplier/issues              | fornecedora         | —                                       |
| POST /api/issues/{id}/resubmit         | fornecedora         | criar_lote(issue_id=...) [F2] + rules.pendencias [F3] |
| GET  /api/issues, /api/analyses        | Bernhoeft           | —                                       |
| GET  /api/search?q=                    | forn., Bernhoeft    | page_fts filtrado por contratos do usuário |
| GET  /api/bernhoeft/metrics            | Bernhoeft           | rules.metricas.calcular_metricas [F3]   |
| POST /api/reports                      | ANALISTA_BH         | cria RASCUNHO                           |
| POST /api/reports/{id}/publish         | ANALISTA_BH         | rules.parecer.snapshot_parecer [F3]     |
| GET  /api/client/reports               | GESTOR_CONTR        | só APROVADO_PUBLICADO, sem R$ nem OCR   |
| GET  /api/audit                        | ADMIN_BH            | —                                       |
"""
