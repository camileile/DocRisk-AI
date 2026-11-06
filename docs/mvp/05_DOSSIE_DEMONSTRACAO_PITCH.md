# DocRisk AI — Dossiê de Demonstração e Pitch

**Versão:** 0.1 — roteiro preliminar, sujeito ao ensaio com a equipe  
**Data-base:** 06/11/2026  
**Produto:** plataforma modular de inteligência documental; módulo Trabalhista como MVP único.

## 1. Tese da apresentação

**Problema:** documentos chegam em diferentes formatos e exigem organização, conferência e retrabalho entre organizações.  
**Proposta:** transformar arquivos em informações estruturadas, sinalizar exceções, conectar evidências e levar o resultado a uma decisão humana rastreável.  
**Diferencial demonstrável:** um único percurso interorganizacional, da fornecedora à contratante, com papéis autorizados, análise especializada e parecer versionado.

A apresentação deve enfatizar **gestão de risco com evidências**, mas sem declarar infração comprovada a partir de uma divergência automática. A IA **apoia**, a regra **compara** e o profissional **decide**.

## 2. Mensagem principal sugerida

> “O DocRisk AI organiza documentação dispersa, identifica pontos que precisam de correção ou conferência e conecta as evidências a indicadores e pareceres. A informação circula entre fornecedora, auditora e contratante, mas cada participante enxerga apenas o que lhe cabe. O foco é reduzir a fricção documental e dar mais clareza à tomada de decisão — sempre com revisão humana.”

Esta fala é uma **proposta de narrativa**, não uma citação oficial da Bernhoeft.

## 3. Estrutura enxuta dos slides

| Parte | Mensagem-chave | Conteúdo visual recomendado |
|---|---|---|
| 1 — Abertura | Documentos complexos. Decisões mais claras. | Logotipo oficial e frase central; poucos textos. |
| 2 — Problema | Arquivos dispersos, falhas de leitura, retrabalho e falta de rastreabilidade. | Fluxo tradicional fragmentado, sem números de economia inventados. |
| 3 — Solução | Plataforma-base + módulos especializados. | Diagrama modular; Trabalhista em destaque, futuros rotulados. |
| 4 — Jornada | Envio → triagem → correção/revisão → conciliação → parecer. | Diagrama horizontal curto e papéis. |
| 5 — Inteligência / Indicadores | Cobertura, indícios de divergência, pendências e andamento. | Dashboard sintético com definições e avisos claros. |
| 6 — Demonstração | Mostrar o fluxo completo em telas reais. | Alternar abas de perfis previamente autenticados. |
| 7 — Valor / Modelo comercial | Base compartilhada, módulos contratáveis por necessidade. | Quadro modular; preços e SLA não definidos. |
| 8 — Encerramento | Controle, rastreabilidade e decisão humana. | Tela do parecer publicado / PDF, convite para validação futura. |

Conferir a apresentação já existente do hackathon antes de substituir páginas, logotipo ou textos. **Este documento não altera o PPTX existente.**

## 4. Preparação da demonstração

**Ambiente:** domínio/URL e backend operacionais, mesma instância Clerk, `DOCRISK_DEMO_MODE=0`, banco/arquivos persistentes, SHA registrado.

**Três abas distintas e sessões isoladas:**

1. **Operador da Fornecedora:** lote sintético **pré-carregado**, mostrando um documento apto e uma pendência objetiva; caminho para reenvio se necessário.
2. **Analista Bernhoeft:** fila com um item para revisão humana, evidência, correção auditada e conciliação por trabalhador/competência; dashboard exibindo indícios e cobertura.
3. **Gestor da Contratante:** parecer **já publicado** correspondente à base sintética, indicador derivado do snapshot e botão de baixar PDF.

Uma quarta aba administrativa é opcional, apenas se houver tempo para mostrar organização/vínculos. Não apresentar tela institucional ou de administração como acesso documental do Admin Geral ou Admin Bernhoeft.

**Importante:** evitar aguardar o processamento de um arquivo em tempo de palco. O lote principal deve já estar em estado terminal e conferido. Um envio simples pode ser mostrado como ação demonstrativa somente se sua resposta for rápida e se houver contingência; não é necessário para provar todo o valor.

## 5. Casos sintéticos para a narrativa

| Caso | Preparação | O que demonstrar |
|---|---|---|
| C1 — Documento apto | Espelho de ponto/holerite compatíveis | Resultado rastreável e análise válida. |
| C2 — Ilegibilidade | Arquivo deteriorado ou leitura insuficiente | Devolução motivada à fornecedora e necessidade de reenvio. |
| C3 — Divergência | Horas extras diferentes entre ponto e holerite | **Indício** e indicação de evidência, sem diagnóstico jurídico. |
| C4 — Revisão humana | Campo incerto com página de referência | Analista corrige com justificativa e histórico. |
| C5 — Dados insuficientes | Holerite informa somente valor em R$ ou falta documento | Sem comparação válida; não computar como regular. |
| C6 — AEJ | Arquivo eletrônico de jornada estruturado | Origem e jornada estruturadas; limitação da assinatura explicitada. |
| C7 — Publicação | Parecer revisado e PDF prontamente disponível | Contratante autenticada consulta somente o publicado. |

Os IDs, competências e resultados exatos precisam corresponder ao banco congelado da apresentação; não usar valores hipotéticos na fala como se fossem resultados medidos.

## 6. Indicadores recomendados para exibição

**Analista:** taxa de divergências sobre análises válidas, cobertura, diferenças numéricas em horas e análises bloqueadas/em revisão.  
**Fornecedora:** lotes enviados, andamento, pendências a responder e reenviadas que aguardam verificação.  
**Administrador Bernhoeft:** operação, revisões, pendências, tempo de regularização e pareceres publicados.  
**Contratante:** contratos com parecer, divergências/cobertura **dos snapshots publicados** e casos sem comparação válida.

Não usar um único “índice de risco” sem modelo aprovado. Não inserir “pendências vencidas” como gestão contratual sem validar regra de prazos e responsável por etapa.

## 7. Fala-base da demonstração por momento

**Transição do problema para o produto:** “O objetivo não é apenas digitalizar arquivos: é saber o que foi recebido, o que pode ser comparado e onde alguém precisa agir.”

**Operador:** “Aqui a fornecedora acompanha seus envios. Quando um documento não permite análise, a pendência informa a razão e a correção solicitada; o reenvio mantém histórico.”

**Analista:** “A auditoria recebe somente os casos que exigem decisão. O analista pode consultar a origem, corrigir campos com justificativa e visualizar a conciliação. Uma divergência é evidência a investigar, não uma conclusão automática.”

**Indicadores:** “O painel mostra não apenas quantas divergências foram encontradas, mas também a cobertura: quantos trabalhadores tiveram dados suficientes para comparar. Isso evita tratar falta de documento como conformidade.”

**Contratante:** “Depois da conferência e publicação, a contratante visualiza os resultados autorizados e o PDF versionado. O que ainda está em análise não é divulgado como parecer definitivo.”

**Fechamento:** “O módulo Trabalhista valida uma arquitetura que pode receber novas especialidades. O modelo comercial proposto é modular; as regras de contratação ainda exigem validação.”

## 8. Contingências e integridade da apresentação

- **Clerk indisponível:** não afirmar “login real demonstrado” com demo offline. Informar claramente que a navegação alternativa é simulação.
- **Gemini indisponível:** mostrar resultados do lote já processado com proveniência conhecida; não atribuir ao Gemini resultados TextLayer.
- **Reenvio demora:** trocar para registro já reenviado e seu histórico.
- **Erro na prévia/publicação:** usar parecer publicado previamente validado e demonstrar consulta; não inventar publicação na hora.
- **Internet/projetor:** ter vídeo/capturas legíveis de reserva, claramente identificados como registros prévios.
- **Pergunta sobre economia/precisão:** responder que não há resultado real generalizável validado; benchmark sintético local não é benchmark de documentos empresariais reais.

## 9. Checklist do apresentador

- [ ] Revisar tempo autorizado pela organização e ajustar número de slides. **Não assumir duração aqui.**
- [ ] Revisar logotipo oficial (símbolo de camadas, índigo/violeta) e contraste em projeção.
- [ ] Abrir todas as abas e verificar sessões independentes, sem compartilhar perfis por engano.
- [ ] Lote/documento de demonstração já processado; cenário ilegível e análise já preparados.
- [ ] Parecer de referência publicado e PDF baixável, com competência correta e dados fictícios.
- [ ] Conferir cada indicador do slide com os denominadores do sistema.
- [ ] Testar transições entre abas em resolução do projetor e no celular reserva.
- [ ] Deixar prontos os limites: dados sintéticos, revisão humana e módulos futuros.
- [ ] Possuir alternativa offline **rotulada** e saber em que circunstâncias usá-la.

## 10. Questões comerciais a validar

- Segmentação dos compradores: contratação por auditora, contratante ou grupo econômico?
- Plataforma-base inclusa e especialidades contratadas separadamente: aprovar no desenho comercial final.
- Faixas, implantação, preço por documento/contrato/usuário e serviços profissionais: **não definidos neste pacote**.
- Requisitos de segurança, disponibilidade, suporte e tratamento de dados reais antes de qualquer piloto empresarial.

## 11. Referências

`web/app/page.tsx`; `web/app/como-funciona/page.tsx`; `web/app/modulos/page.tsx`; `docs/D3_08_PARECER_CORPORATIVO.md`; `docs/INTEGRACAO_SEIS_PERFIS.md`; `docs/BENCHMARK.md`; `docs/AVALIACAO_VISUAL_GEMINI.md`; apresentação de pitch existente (não copiada para este pacote).
