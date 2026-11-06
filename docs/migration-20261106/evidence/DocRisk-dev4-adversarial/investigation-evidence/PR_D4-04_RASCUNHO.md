# Rascunho local de PR — D4-04

Título: Validar inicialização e impedir instâncias sobre o mesmo diretório de dados

Recusa configuração inválida antes de abrir o banco e usa trava do sistema operacional por diretório de dados. Preserva inicialização Clerk, seed condicionado, métodos e cabeçalhos CORS atuais. Inclui ensaio com processos reais, falha/reinício e testes de configuração.

Base: 1148e76. Cópia: codex/d4-04-review-1148. Original preservada.
Validação: 424 aprovados, 1 ignorado; runtime_check 11/11; diff --check aprovado. Último commit só acrescenta evidência, sem alterar código testado.
Dev1 revisa config.py e interação com worker. Dev2 revisa lifespan/autenticação/CORS. Dev4 revisa trava e configuração do CI.
A validação de origens do Dev2 no import foi preservada, além da política operacional adicional no runtime; existe sobreposição intencional de leitura/validação CORS a ser revisada, não uma ausência absoluta de lógica semelhante. Não foi feita refatoração estrutural para ocultar essa fronteira. A trava protege processos que cooperam com esse runtime; não é processamento distribuído.
Sem push ou PR aberto.
