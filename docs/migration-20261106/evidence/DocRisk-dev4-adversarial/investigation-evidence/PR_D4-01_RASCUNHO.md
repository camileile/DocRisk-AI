# Rascunho local de PR — D4-01

Título: Rejeitar coerção de status e validar ciclo dos seis papéis

A administração aceitava coerção de valores como "1" para ativo. A mudança exige booleano JSON e rejeita campos extras, alinhando a validação às demais rotas de status. Acrescenta matriz de seis papéis, autorização, ciclo de desativação/reativação e persistência.

Base de revisão: 1148e76. Cópia: codex/d4-01-review-1148. Branch original preservada.
Validação: 420 aprovados, 1 ignorado; diff --check aprovado. O último commit da cópia altera apenas documentação; código idêntico ao ensaiado.
Revisor necessário: Dev2, especialmente StatusInput em admin_management.py e resposta 401 fora do modo demo. Não altera autorização/sessões nem implementa correção equivalente já presente na main.
Sem push ou PR aberto.
