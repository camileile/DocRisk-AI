# DocRisk AI — Manual de Implantação e Operação (MVP)

**Versão:** 0.1 — procedimento técnico controlado  
**Data-base:** 06/11/2026  
**Código de referência:** `0008ab2d97f759002aa6e60b485d1e2b6965a36b`  
**Atenção:** não é um manual de implantação em produção empresarial; homologação real ainda pendente.

## 1. Objetivo e responsabilidades

Disponibilizar uma instância do MVP com **frontend Next.js em runtime**, API FastAPI, SQLite e arquivos persistentes, login Clerk e dados fictícios. O responsável por ambiente configura DNS/HTTPS/segredos, o responsável pela API verifica DB/worker/logs, e os responsáveis pelas jornadas executam homologação usando perfis próprios.

Nenhum passo deste manual autoriza habilitar tokens demonstrativos no ambiente com Clerk, copiar base com pessoas reais, ou publicar endpoints administrativos sem autorização.

## 2. Pré-requisitos

- Python 3.11+, Node.js compatível com Next.js 16, dependências instaladas a partir dos locks/manifests.
- Domínio/HTTPS e origem web conhecida; frontend e API com CORS alinhado.
- Instância Clerk configurada para o domínio e método de login, verificação de e-mail e recuperação. Não compartilhar credenciais de pessoas ou chaves no chat/repositório.
- Diretório de dados **persistente** da API com espaço para banco SQLite, arquivos enviados e páginas renderizadas.
- Ambiente exclusivo com dados fictícios e sistema de backups antes de mudanças.

## 3. Variáveis de configuração (sem valores sensíveis)

| Frontend | Uso |
|---|---|
| `NEXT_PUBLIC_AUTH_MODE=clerk` | Build operacional com Clerk; nunca usar a exportação estática como substituto. |
| `NEXT_PUBLIC_API_URL` | Endereço HTTPS da API. |
| Chaves públicas/privadas Clerk conforme `web/.env.local.example` | Configurar diretamente no painel/ambiente autorizado; não registrar valores aqui. |

| Backend | Uso |
|---|---|
| `DOCRISK_AUTH_MODE=clerk` | Autenticação real e vínculo local. |
| `DOCRISK_DEMO_MODE=0` | Impede modo demonstrativo e tokens de teste. |
| `DOCRISK_SYNC=0` | Usa worker de processamento fora da requisição no modo normal. |
| `DOCRISK_DATA_DIR` | Diretório persistente com banco e arquivos. |
| `CLERK_ISSUER` | Emissor exato da instância Clerk. |
| `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`, `CLERK_AUDIENCE` (quando aplicável), `CLERK_INVITE_REDIRECT_URL` | Verificações e convites. |
| `AI_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` | Motor de leitura, conforme capacidade realmente habilitada. |
| `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `MAX_PAGINAS` | Origem permitida e limites operacionais. |

**Não** usar `AI_PROVIDER=textlayer` como evidência de execução Gemini. Não ativar `DOCRISK_DEMO_MODE=1` para contornar problemas de provisionamento em Clerk.

## 4. Inicialização local de desenvolvimento

No diretório de API:

```bash
cd api
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\python.exe -m pip install -e ".[test]"
# macOS/Linux: .venv/bin/python -m pip install -e ".[test]"
# Ative o ambiente antes dos comandos seguintes:
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pytest -q
python -m uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000
```

No diretório web (outro terminal):

```bash
cd web
npm ci
npm run typecheck
npm run build
npm run dev
```

**Nota:** os comandos acima são de desenvolvimento e verificação local, não receita completa de produção. Criar o `.venv` antes de invocar seu Python; no Windows, não assumir que a pasta existe.

## 5. Bootstrap do ambiente operacional

1. Conferir variáveis, volume persistente e a **mesma** instância Clerk na API/frontend.
2. Criar/confirmar no Clerk a identidade autorizada do administrador institucional.
3. No ambiente da API, executar o procedimento de associação institucional descrito em `docs/D3_07_CLERK.md` por operador autorizado; não usar senha ou subject inferidos de e-mail.
4. Admin da Plataforma acessa `/plataforma` e cadastra organização auditora com convite inicial ao Admin Bernhoeft.
5. Destinatário valida seu e-mail, aceita o convite e seleciona o vínculo.
6. Admin Bernhoeft cadastra contratante, fornecedora e contrato; convida analista e gestores.
7. Gestor da Fornecedora aceita convite e convida operador.
8. Admin Bernhoeft atribui contratos aos analistas em **Gestão de Usuários**; Gestor da Fornecedora atribui contratos aos operadores em **Operadores**. A concessão pode ter validade e deve ser feita também para contas Clerk anteriores à atualização: não há preenchimento automático de acessos.
9. Preparar trabalhadores fictícios e documentos correspondentes; consultar o passo seguinte.
10. Reiniciar/reciclar uma instância controladamente e confirmar persistência antes do ensaio final, incluindo concessões e revogações. Conferir [Acesso individual a contratos](../ACESSO_INDIVIDUAL_CONTRATOS.md).

O cadastro de usuários por token (`/api/admin/users`, `/api/supplier/operators`) é exclusivo da configuração demo de testes. A sessão Clerk deve usar convites e vínculos.

## 6. Provisionamento dos trabalhadores sintéticos

O script existente `api/scripts/provision_mvp_workers.py` recebe CSV com colunas exatas `id,nome` e identificadores no formato `T001` etc. **Executá-lo no ambiente que enxerga o mesmo `DOCRISK_DATA_DIR` da API**, nunca contra outra cópia do SQLite.

```csv
id,nome
T001,Trabalhador Fictício Um
T002,Trabalhadora Fictícia Dois
```

```bash
# Após configurar o ambiente e cadastrar o contrato:
python api/scripts/provision_mvp_workers.py --contract-id CT-DO-AMBIENTE --csv trabalhadores_sinteticos.csv
# Aplicação explícita após conferência do resultado da simulação:
python api/scripts/provision_mvp_workers.py --contract-id CT-DO-AMBIENTE --csv trabalhadores_sinteticos.csv --apply --confirm-synthetic
```

O primeiro comando faz simulação; o segundo grava atomicamente, protege contra colisões e emite evento de auditoria. Confirmar IDs do contrato e trabalhadores com os documentos do lote. Não usar dados reais ou arquivos enviados por terceiros para esta prova.

## 7. Procedimento diário da demonstração

**Antes de abrir:** checar `GET /health`, URL da API, ambiente, disco, backup, processamento de worker e status de login; validar um usuário de cada papel sem registrar credenciais.  
**Antes do envio:** selecionar contrato/competência e arquivos sintéticos; conferir tamanho e extensão; guardar gabarito esperado separadamente.  
**Após o envio:** monitorar lote, documentos e estados; não repetir upload cego em erro de rede sem antes verificar se a operação foi aceita.  
**Revisão:** consultar evidência e páginas; corrigir com origem/justificativa; conferir concorrência de edição.  
**Publicação:** criar rascunho, revisar prévia e hash, conferir responsável/recomendações/limitações, publicar e confirmar PDF.  
**Consulta externa:** abrir contratante com outra conta/vínculo e provar ausência de documentos não publicados.

## 8. Backup, restauração e incidentes

**Backup mínimo:** cópia consistente de `docrisk.sqlite` e dos diretórios `uploads/` e `pages/`, com timestamp, SHA/versão e guarda fora da área pública. Backups de SQLite devem ser feitos de forma consistente com escritas (API/worker em estado seguro ou mecanismo transacional apropriado), não copiando arquivo arbitrariamente durante operações ativas.

**Restauração:** parar recepção/worker; preservar logs úteis sem dados sensíveis; restaurar banco e arquivos da **mesma** referência; validar integridade de contratos, lote e páginas; executar smoke negativo de acesso antes de liberar usuários. Não presumir que deploy frontend restaura dados da API.

**Falha de Clerk:** bloquear autenticação operacional e comunicar indisponibilidade; não habilitar tokens de demonstração como substituto silencioso.  
**Falha do Gemini:** indicar claramente se o mecanismo passou a usar TextLayer de teste ou se não houve processamento; não apresentar como sucesso da IA.  
**Falha do lote:** verificar estado e se houve gravação antes de reprocessar.  
**Falha no PDF:** manter rascunho/estado; não inventar versão publicada; registrar o erro e revalidar hash.

## 9. Liberação e rollback

| Etapa | Evidência |
|---|---|
| Código congelado | SHA frontend e backend registrados. |
| CI | Workflow de API e frontend verdes no mesmo SHA. |
| Configuração | Variáveis presentes por nome, sem revelar segredo; HTTPS/CORS/issuer corretos. |
| Persistência | Dados/arquivos sobrevivem a reinício controlado. |
| Segurança | Acesso negativo entre perfis/organizações. |
| E2E | Todos os passos com Clerk e banco real, usando documentos sintéticos. |
| Backup | Procedimento e ponto de restauração comprovados. |
| Rollback | Deploy/versão anterior identificados, compatibilidade de dados verificada. |

## 10. Pendências de operação a resolver antes de alegar produção

- Confirmar hospedagem exata do backend e suporte a volume persistente/worker de processo único.
- Monitoramento, retenção de dados e resposta a incidentes; recursos operacionais atuais são de demonstração.
- Gestão de segredos, recuperação de backups, disponibilidade e política de versões.
- Validação integral de Clerk e Gemini reais na configuração escolhida.
- Revisão de segurança e privacidade adequada a dados reais, não coberta pelo escopo atual.

## 11. Referências

`docs/D3_07_CLERK.md`; `docs/H03_PROVISIONAMENTO_CLERK_MVP.md`; `web/.env.local.example`; `.env.example`; `api/docrisk_core/config.py`; `api/scripts/link_clerk_identity.py`; `api/scripts/provision_mvp_workers.py`; `web/README.md`; `.github/workflows/`.
