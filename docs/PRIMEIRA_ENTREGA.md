# Primeira entrega técnica — decisões e próximo gate

**Objetivo entregue:** uma prova de conceito de importação, separando processamento AEJ estruturado do processamento PDF/imagem, com testes locais.

**Não entregue ainda:** aplicação web, modelo multimodal, autenticação, revisão por UI, análise jurídica, motor de prazos, reenvios, indicadores, pareceres e a base de 100 trabalhadores.

## Gate 1 — P0 documental
1. Com lote misto preparado pela equipe, medir início e fim dos documentos, incluindo páginas de continuação.
2. Comparar a classificação automática com gabarito e documentar erros.
3. Revisão humana de agrupamentos ambíguos (futura UI).
4. Validar AEJ real permitido para teste, sem dados pessoais, e ampliar parser com base no anexo oficial.
5. Somente após Gate 1: acrescentar vínculo trabalhador/competência e motor de análises.

## Regra de produto
O motor documental é generalista na classificação; o módulo especializado inicial se limita a ponto, horas extras e pagamentos. Não criar catálogo configurável nesta fase.

## Cuidados
- Erro com documento de um trabalhador bloqueia apenas análises dependentes dele na competência, quando esse comportamento for implementado.
- Devoluções automáticas precisam de justificativa verificável; casos incertos para revisão.
- A Bernhoeft revisa e publica os pareceres; a contratante recebe só versões autorizadas.
- A base sintética de 100 trabalhadores permanece em planejamento, SEM geração nesta entrega.
