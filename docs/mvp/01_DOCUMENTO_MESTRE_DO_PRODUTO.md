# DocRisk AI — Documento Mestre do Produto

**Versão:** 0.1 — minuta para validação  
**Data-base:** 06/11/2026  
**Referência técnica:** `camileile/DocRisk-AI`, `main`, commit `0008ab2d97f759002aa6e60b485d1e2b6965a36b`  
**Situação:** documento de produto; não constitui comprovação de homologação nem especificação jurídica definitiva.

## 1. Resumo executivo

O **DocRisk AI** é uma plataforma modular de inteligência documental que recebe arquivos empresariais, identifica conteúdos e evidências, organiza exceções para correção na origem ou revisão humana, realiza análises especializadas e publica resultados autorizados. Seu objetivo é reduzir o trabalho operacional de organizar e conferir documentos, sem substituir a decisão de profissionais responsáveis.

O MVP desenvolve **um único módulo especializado: Trabalhista**, com foco na conferência documental de ponto, holerite e comprovantes e na comparação de **quantidades de horas extras** por trabalhador e competência. A plataforma também suporta arquivos **AEJ** como informação estruturada de jornada, sujeitos a suas regras próprias e limitações. Três módulos adicionais podem ser exibidos **somente como possibilidades futuras**, não como funções operacionais já entregues.

**Promessa demonstrável:** da entrada documental ao parecer publicado, com evidências rastreáveis, responsabilidades separadas, tratamento de pendências e controle de acesso.

**Promessas que não devem ser feitas:** detecção jurídica conclusiva de infrações; cálculo automático de passivo financeiro; conformidade integral da prestadora; validação de assinatura P7S de AEJ; precisão real do Gemini sem benchmark reproduzível.

## 2. Problema e oportunidade

Empresas contratantes, fornecedoras e auditoras precisam organizar documentação recebida em formatos heterogêneos, identificar arquivos ilegíveis ou incompletos, relacionar documentos por trabalhador/período, verificar divergências e comunicar correções. Uma sequência manual e dispersa dificulta a rastreabilidade, a visão consolidada e a priorização das intervenções.

A solução proposta estabelece um fluxo compartilhado: **receber → classificar → extrair/estruturar → identificar exceções → corrigir/revisar → conciliar → conferir → publicar**. Esse fluxo é uma hipótese de valor do produto; economias, demanda de mercado e benefícios quantitativos exigem validação externa antes de serem declarados como resultados.

## 3. Usuários, responsabilidades e limites

| Perfil | Responsabilidade principal | Limite fundamental |
|---|---|---|
| **Administrador da Plataforma** (`ADMIN_PLATAFORMA`) | Organizações auditoras, convite do administrador inicial, dados institucionais | Não acessa lotes, documentos, pareceres ou análises trabalhistas. |
| **Administrador Bernhoeft** (`ADMIN_BH`) | Empresas vinculadas, contratos, convites, acompanhamento da operação e auditoria administrativa | Não decide revisão documental, não publica parecer, não consulta acervo analítico bruto. |
| **Analista Bernhoeft** (`ANALISTA_BH`) | Revisar evidências, corrigir campos justificadamente, verificar conciliações, elaborar e publicar pareceres | Limitado aos contratos autorizados; divergência não implica infração comprovada. |
| **Gestor da Fornecedora** (`GESTOR_FORN`) | Acompanhar envios e pendências da empresa, convidar/revogar operadores | Não publica parecer nem acessa análises internas da auditora. |
| **Operador da Fornecedora** (`OPERADOR_FORN`) | Enviar arquivos, acompanhar lotes da organização e responder pendências | Acesso ao acervo autorizado da **fornecedora**, não somente aos arquivos enviados por si; sem gestão de usuários. |
| **Gestor da Contratante** (`GESTOR_CONTR`) | Consultar indicadores e pareceres publicados dos contratos próprios; baixar PDF | Não acessa documentos, rascunhos, OCR, fila interna ou evidências não publicadas. |

A autorização deve ser aplicada no **backend**, combinando identidade, vínculo ativo, papel, organização e contrato. O sistema não deve inferir permissão a partir de parâmetros fornecidos apenas pela interface.

Analistas e operadores também precisam de concessão individual vigente para cada contrato. O Administrador Bernhoeft atribui contratos aos analistas da própria auditora; o Gestor da Fornecedora atribui aos operadores da própria empresa. A organização continua limitando o escopo. Novas contas não herdam contratos, e usuários Clerk existentes precisam receber concessões explícitas após a atualização. Revogar um contrato preserva os outros acessos e o histórico documental.

## 4. Escopo funcional do MVP

### 4.1 Incluído no núcleo da plataforma

1. Site institucional com proposta de valor, fluxo, módulos, contato e acesso.
2. Autenticação por Clerk no modo operacional, seleção de vínculo e convite por usuários autorizados. Login real configurado e validado ainda é **critério pendente de homologação**, não um resultado presumido.
3. Cadastro operacional autorizado de organizações e contratos; provisionamento controlado de trabalhadores **sintéticos** para a demonstração.
4. Recepção de arquivos PDF/imagens e AEJ, com verificação básica de formatos e limites; registro e acompanhamento de lotes.
5. Leitura, segmentação/classificação e organização dos documentos, com identificação de origem, versão e páginas quando aplicável.
6. Sinalização de pendências objetivas (por exemplo, ilegibilidade, página faltante, documento ausente) e solicitação de correção à fornecedora.
7. Reenvio vinculado à pendência, com histórico de versões. Pendências reenviadas podem aguardar processamento ou conferência; não equivalem a resolução automática.
8. Revisão humana com evidência, justificativa e registro auditável de correção de campo. A API exige identificação de fonte e guarda de concorrência.
9. Conciliação das quantidades de horas extras entre espelho de ponto e holerite, por trabalhador e competência. AEJ acrescenta evidência estruturada de jornada conforme regras de associação existentes.
10. Indicadores de operação, cobertura, divergências e pendências por perfil e pelo escopo permitido.
11. Elaboração de prévia, revisão de recomendações e publicação versionada de parecer; consulta e download de PDF pela contratante autenticada.
12. Trilha de auditoria de ações e segregação das visões por perfil.

### 4.2 Fora do escopo demonstrável

- Implementar os três módulos futuros apresentados no catálogo.
- Análise jurídica conclusiva ou classificação automática de risco financeiro/passivo.
- Processar dados pessoais reais no hackathon; atestar conformidade com a LGPD em ambiente produtivo.
- Portal de assinatura contratual, cobrança e assinatura digital dos pareceres.
- Notificações externas automáticas de prazo: existe módulo interno de obrigações/outbox, **sem entrega efetiva de alertas externos ou integração no painel do MVP**.
- Garantir precisão do reconhecimento visual com Gemini sem medição em corpus e ambiente apropriados.
- Transformar o protótipo SQLite em SaaS de produção escalável no encerramento do hackathon.

## 5. Jornada operacional de ponta a ponta

**Preparação:** administrador institucional estabelece a auditora; o administrador da auditora cria contratante, fornecedora e contrato; perfis recebem convites autenticados. Trabalhadores e documentos são exclusivamente fictícios.

**Envio:** operador seleciona contrato permitido e importa lote. A interface registra o recebimento e consulta o processamento sem bloquear necessariamente a navegação.

**Tratamento inicial:** o sistema identifica documentos e classifica versões. Itens claros seguem; itens ilegíveis, ausentes ou incertos geram pendência ou revisão humana conforme a regra.

**Correção na origem:** a fornecedora identifica a ação solicitada e envia nova versão, preservando a rastreabilidade. O sistema reconsidera apenas as dependências pertinentes.

**Conferência especializada:** o analista verifica os campos e as fontes, realiza a correção auditada quando necessário, acompanha a comparação das horas extras e registra decisões.

**Parecer:** o analista cria rascunho, confere a prévia, as recomendações, as limitações e a autoria e publica a versão autorizada. Versões anteriores permanecem identificáveis.

**Consulta externa:** o gestor da contratante visualiza exclusivamente o conteúdo publicado e obtém o PDF; alterações internas posteriores não reescrevem o snapshot publicado.

## 6. Regras de negócio fundamentais

| Código | Regra | Critério verificável |
|---|---|---|
| RN-01 | Toda ação sensível exige identidade e vínculo ativos, em organização/contrato permitido. | Requisições com vínculo de outra empresa não expõem dados. |
| RN-02 | Uma falha documental não deve impedir análise de pares independentes. | Trabalho de outro vínculo/competência segue disponível. |
| RN-03 | A conciliação trabalhista atual exige espelho de ponto e holerite vigentes, aptos e com dados comparáveis. | Sem um deles: bloqueio/espera, jamais resultado regular automático. |
| RN-04 | Comparar somente **horas com horas**; valor monetário isolado não substitui quantidade. | Caso com apenas R$ produz dados insuficientes. |
| RN-05 | Divergência significa **indício a verificar**, não culpa, infração ou passivo. | Rótulos e parecer explicitam o limite. |
| RN-06 | Correção de campo exige justificativa e origem por página, controle de concorrência e histórico. | Payload legado sem rastreabilidade é recusado. |
| RN-07 | Reenvio conserva vínculo à pendência e não apaga versão anterior. | Linha do tempo e versão anterior consultáveis. |
| RN-08 | Somente o analista autorizado publica parecer; a contratante vê apenas publicação válida. | Rascunho não aparece no portal externo. |
| RN-09 | A publicação preserva conteúdo conferido (snapshot e hash). | Alteração após conferência requer nova prévia. |
| RN-10 | A falta de comprovante de pagamento não constitui prova de atraso salarial. | Observação expressa na análise. |
| RN-11 | AEJ é dado estruturado e sua interpretação respeita limitações da regra atual. | Não anunciar validação de assinatura P7S ou cálculo semanal completo. |
| RN-12 | Ambiente de demonstração offline e sessão Clerk operacional são distintos. | Offline não executa mutações reais nem equivale a validação de login. |

## 7. Indicadores aprovados tecnicamente

| Indicador | Unidade / fórmula | Observação |
|---|---|---|
| Taxa de divergências | Trabalhadores com divergência / análises válidas no filtro | Sem análise válida = indisponível, não 0%. |
| Cobertura da análise | Análises válidas / trabalhadores cadastrados nos contratos selecionados | Depende de cadastro sintético correto e competência selecionada. |
| Horas divergentes | Soma dos módulos das diferenças em horas verificadas | Parcial quando a diferença numérica não pode ser estimada. Não converter em R$. |
| Análises bloqueadas/em revisão | Pares atuais nos estados correspondentes | Não denominar automaticamente de casos de risco crítico. |
| Pendências abertas/resolvidas | Contagem por estado no escopo | Distinguir `REENVIADA` de pendência que exige ação da fornecedora. |
| Tempo médio de regularização | Média de `(resolved_at - created_at)` para pendências resolvidas | Medida operacional; não conformidade jurídica. |
| Publicações | Pareceres em estado publicado | Para a contratante, apenas snapshots publicados. |
| Páginas processadas / tempo por página | Registros de páginas/tempo de processamento | Performance da aplicação, não indicador de qualidade da IA. |

**Em discussão, não aprovados para o dashboard:** vencimento contratual de pendências, regularização no prazo, índice único de risco, estimativa de passivo e economia automática. O padrão de 3 dias de correção cadastrado no sistema **não foi validado como política universal da Bernhoeft**.

## 8. Modelo comercial e posicionamento

A arquitetura e a apresentação enfatizam **modularidade**. O módulo Trabalhista é o único especializado do MVP. Os módulos futuros sugeridos no site são: **Homologação de Fornecedores**, **Saúde e Segurança Ocupacional** e **Conformidade Ambiental**.

**Hipótese comercial a apresentar:** plataforma-base com módulos especializados contratáveis conforme necessidade. Não foram verificados nesta revisão: preços, SLA contratado, regras de cobrança, disponibilidade garantida, termos de licenciamento e modelo definitivo de comercialização. Portanto, tratá-los como proposta a validar, não como acordo fechado.

## 9. Critério de MVP encerrado

O MVP de hackathon só será considerado demonstrado integralmente após: (a) identidade Clerk real, (b) vínculo autorizado, (c) contrato e trabalhadores sintéticos, (d) lote já processado em ambiente configurado, (e) revisão/correção, (f) conciliação, (g) parecer conferido e publicado e (h) gestor de contratante autenticado consultando/baixando o PDF — no **mesmo release**, com evidências.

Testes unitários, builds e casos com provider simulado são necessários, mas não substituem a homologação do fluxo real.

## 10. Questões em aberto e decisões a registrar

- Ambiente/domínio/instância Clerk e prova de sessões, e-mails e convites reais.
- Evidência reproduzível de leitura Gemini e custo/latência no corpus sintético; fallback offline não comprova IA.
- Validação de cenários de upload simultâneo, reenvio duplicado e falha parcial.
- Definição institucional dos prazos (se forem incluídos no futuro) e dos comprovantes efetivamente exigíveis.
- Conferência visual presencial (desktop, mobile, projetor) e ajustes essenciais de legibilidade.
- Validação da narrativa comercial modular pelo time e organizadores do evento.

## 11. Referências de implementação

- `api/docrisk_core/contracts.py` — papéis, tipos e estados.
- `api/docrisk_core/rules/conciliacao.py`, `metricas.py`, `metricas_analista.py`, `portal_contratante.py` — regras e indicadores.
- `docs/INTEGRACAO_SEIS_PERFIS.md` — isolamento e seis jornadas.
- `docs/D3_07_CLERK.md`, `docs/H03_PROVISIONAMENTO_CLERK_MVP.md` — identidade e preparação.
- `docs/D3_08_PARECER_CORPORATIVO.md` — prévia, versão e publicação.
- `docs/AEJ.md`, `docs/BENCHMARK.md`, `docs/AVALIACAO_VISUAL_GEMINI.md` — AEJ e limites de IA.
