# D2-13 — Obrigações e outbox

Esta entrega adiciona um módulo de domínio para obrigações por contrato e competência e uma outbox transacional para alertas. A estrutura é criada pela migração aditiva `0001_obligations_outbox.sql`, aplicada por `db.init_db()`; `schema.sql` permanece intacto.

## Uso

- `criar_obrigacao(...)` registra contrato, competência, tipo, vencimento, fuso, responsável e o evento inicial no histórico.
- `atualizar_obrigacao(...)` atualiza o estado sem apagar o histórico.
- `configurar_agendamento(...)` define aviso antes, no ou depois do prazo, por contrato e tipo documental opcional.
- `agendar_alertas(...)` encontra avisos vencidos e os grava na outbox dentro da transação do chamador. Os callbacks obrigatórios resolvem os destinatários e confirmam sua autorização para o contrato e finalidade. Cada destinatário recebe uma chave idempotente própria.
- `processar_simulado(...)` e `registrar_falha(...)` registram tentativas e resultados. Uma falha de comunicação não altera a obrigação.

O payload da outbox contém somente identificadores e metadados da obrigação; não inclui texto, imagem nem conteúdo de documento. O canal é configurável, mas esta entrega não faz envio externo: o adaptador simulado marca explicitamente “envio externo não realizado”. A integração real depende de canal, destinatários e política de autorização aprovados. O módulo ainda não expõe rotas administrativas; a aplicação precisa chamar essas funções a partir do fluxo autorizado.

## Testes

`pytest -q tests/test_d2_13_obligations_outbox.py` cobre criação e histórico, validação, calendário com fuso, idempotência, autorização explícita de destinatários, payload sem conteúdo documental, simulação e falha sem alteração da obrigação.
