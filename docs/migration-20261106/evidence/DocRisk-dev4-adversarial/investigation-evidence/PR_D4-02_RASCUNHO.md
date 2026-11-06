# Rascunho local de PR — D4-02

Título: Executar regressão de isolamento da demonstração no CI

Acrescenta detector de transportes operacionais e cenários de isolamento (seis papéis, links diretos, storage indisponível e rede offline). O workflow executa o teste antes da API e publica apenas o relatório de teste como artefato do CI. Não substitui código da demo nem reaplica a implementação anterior ao PR #26.

Base: 1148e76. Cópia: codex/d4-02-review-1148. Original preservada.
Backend: 399 aprovados, 1 ignorado. Build/TypeScript e resultado de navegador registrados no pacote de revisão final.
Revisão: Dev3 para cobertura/seletores da demo e Dev4 para workflow, timeouts e artefato. Apenas script de teste, workflow e documentação diferem da main. Não há implementação duplicada de lógica de negócio.
Sem push ou PR aberto.

Validação de navegador concluída em 1148e76: 26/26 cenários sem transporte operacional, incluindo storage indisponível e rede offline; build/TypeScript aprovados. Resultados completos em review02-isolation.json e review02-isolation.txt.
