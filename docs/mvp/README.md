# DocRisk AI — Pacote de documentação MVP

**Versão:** 0.1 — material de trabalho e validação  
**Data-base:** 06/11/2026  
**Código verificado:** `camileile/DocRisk-AI` / `main` / `0008ab2d97f759002aa6e60b485d1e2b6965a36b`

**Complemento de integração:** a revisão desta documentação incorpora a atribuição individual de contratos da PR #75. Consulte [Acesso individual a contratos](../ACESSO_INDIVIDUAL_CONTRATOS.md): analistas e operadores novos ou já existentes precisam de concessão explícita, sem preenchimento automático na atualização.

## Índice e uso desta documentação

As cinco minutas são a **documentação consolidada do MVP**, versionada nesta pasta para consulta e manutenção. A inclusão destes arquivos não modifica código da aplicação ou qualquer implantação. Os títulos e regras consideram o código e as descrições atuais. As palavras **implementado**, **testado em ambiente simulado** e **homologado com provedor real** são deliberadamente distintas.

| Documento | Objetivo | Primeiro revisor sugerido |
|---|---|---|
| [01_DOCUMENTO_MESTRE_DO_PRODUTO.md](./01_DOCUMENTO_MESTRE_DO_PRODUTO.md) | Problema, escopo, usuários, funcionalidades e regras de produto | Liderança de produto + equipe |
| [02_DOCUMENTO_TECNICO_ARQUITETURA.md](./02_DOCUMENTO_TECNICO_ARQUITETURA.md) | Componentes, dados, endpoints, segurança e limites | Backend/frontend |
| [03_PLANO_HOMOLOGACAO_QUALIDADE.md](./03_PLANO_HOMOLOGACAO_QUALIDADE.md) | Matriz H01–H14, aceite e evidências | Coordenação técnica + QA |
| [04_MANUAL_IMPLANTACAO_OPERACAO.md](./04_MANUAL_IMPLANTACAO_OPERACAO.md) | Ambiente, Clerk, dados sintéticos, backup e execução | DevOps/backend |
| [05_DOSSIE_DEMONSTRACAO_PITCH.md](./05_DOSSIE_DEMONSTRACAO_PITCH.md) | Narrativa, telas, dados de palco, contingências e modelo modular | Produto + apresentador |

## Principais fatos observados

- O módulo especializado demonstrável é o **Trabalhista**; os três adicionais são futuros.
- Clerk, convites e autorização estão codificados, mas **não há evidência de validação real de e-mail/sessão na documentação consultada**.
- Os testes de código e frontend estavam **verdes para o SHA de referência**; isso não comprova homologação E2E com Clerk real.
- `docs/BENCHMARK.md` mede TextLayer sintético (não acurácia Gemini); `docs/AVALIACAO_VISUAL_GEMINI.md` registra bloqueio sem credencial.
- H03 já está incorporada no código; o módulo de obrigações/outbox não equivale a motor de aviso externo ativo.
- Os documentos anteriores do repo podem conter cabeçalhos históricos como “não implementado”; avaliar sempre junto ao commit e à documentação mais recente.

## Antes de declarar v1.0

1. Validar o **Documento Mestre**, especialmente escopo, nomes dos módulos futuros, indicador e modelo comercial modular.
2. Conferir arquitetura e configurações com os responsáveis técnicos, sem expor segredos.
3. Executar e anexar evidências ao Plano de Homologação; atualizar as situações com data, domínio e SHA.
4. Ensaiar o pitch com as contas reais, dados previamente processados e PDF publicado.
5. Resolver as pendências/contradições e só então revisar a versão para 1.0.

**Registro desta versão:** os documentos são propostos por pull request e não representam homologação concluída. Nenhuma implantação ou alteração de funcionalidades está incluída.
