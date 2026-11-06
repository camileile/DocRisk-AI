# DocRisk AI — Primeira integração Web ↔ API F1

**Escopo concluído em código:** autenticação de teste por token Bearer da API FastAPI, consulta do usuário (`GET /api/me`), contratos (`GET /api/contracts`), lotes (`GET /api/batches`) e detalhe dos lotes/documentos (`GET /api/batches/{id}` e `GET /api/batches/{id}/documents`).

Não é login de produção. O token é uma credencial *demo* criada no banco local: **não deve ser publicado, commitado, compartilhado, colocado em variáveis NEXT_PUBLIC ou usado contra uma API pública**. A interface mantém o token apenas no estado React, sem cookie, localStorage, sessionStorage ou persistência após refresh. A troca de perfil desconecta a sessão.

## 1. Iniciar a API apenas localmente

Em um terminal, na pasta `api`:

```bash
python -m venv .venv
# Ative o virtualenv conforme seu terminal
pip install -e ".[test]"
```

Configuração local necessária (NÃO versionar segredos):

```text
DOCRISK_DEMO_MODE=1
AI_PROVIDER=textlayer
DOCRISK_SYNC=1
```

Defina essas variáveis no ambiente ou no arquivo privado `api/.env`; inicie:

```bash
uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000
```

- `GET http://127.0.0.1:8000/health` deve responder `status=ok` e `production_ready=false`.
- Apenas na máquina de teste, `GET http://127.0.0.1:8000/api/demo/users` lista os usuários e respectivos tokens de demonstração. **Essa rota revela todos os tokens quando DOCRISK_DEMO_MODE=1. Nunca exponha essa API à rede pública, à LAN ou a um túnel; sempre mantenha host 127.0.0.1.**
- Para começar, escolha `u-analista` ou `u-oper-beta`. `u-gestor-beta` também navega como fornecedora, mas sua autorização continua sendo a da API.
- O banco SQLite e os arquivos de testes ficam em `api/data` (ou em `DOCRISK_DATA_DIR`).

## 2. Iniciar o frontend

Na pasta `web`, crie `.env.local` copiando `.env.local.example`:

```text
NEXT_PUBLIC_DOCRISK_API_URL=http://127.0.0.1:8000
```

Depois:

```bash
npm ci
npm run dev
```

Abra **http://localhost:3000/acesso** (não `127.0.0.1:3000`: o CORS atual da F1 só permite `http://localhost:3000`).

A tela `/acesso` mantém o seletor de perfis para demonstração sintética. Quando a URL da API está configurada no build, oferece uma segunda seção, **Conectar API de testes**. Cole nela o token local. A API, não a interface, determina o papel real e os contratos disponíveis.

Somente os perfis `ANALISTA_BH`, `OPERADOR_FORN` e `GESTOR_FORN` entram no primeiro fluxo integrado. Administrador e contratante continuam apenas no modo demonstrativo até as respectivas integrações.

## 3. Telas integradas e limites

- `/painel`: identidade, contrato selecionado e indicadores **derivados dos lotes retornados pela API**.
- `/painel/lotes`: situação, arquivo, quantidade de páginas, filtros, atualização manual e detalhe/documentos do lote por chamada à API. O token nunca é colocado na URL.
- `/painel/envio`: **envio real de PDF, PNG, JPEG e TIFF** pela fornecedora conectada à API local, com confirmação explícita de que o arquivo é sintético. A API cria um lote por arquivo, e o frontend acompanha o status por consultas a `GET /api/batches/{id}` até conclusão/falha ou até o limite de verificações.
- `/painel/lotes/{id}`: **não é uma rota real dinâmica para lotes numéricos**. O frontend usa exportação estática; detalhes reais são abertos em painel expansível na listagem. As rotas dinâmicas anteriores permanecem reservadas ao conjunto sintético prerenderizado.
- As outras páginas operacionais (além de painel, lotes e envio permitido à fornecedora) continuam bloqueadas no modo API para impedir que informações sintéticas se misturem com as informações do backend. Na demonstração, permanecem disponíveis normalmente.
- A lista de lotes não possui competência no modelo F1; portanto o filtro de competência é ocultado no modo API. **O upload é de um arquivo por lote**, limitado a 20 MB na interface de testes (o backend possui sua própria validação). AEJ continua indisponível no upload operacional. Não há conciliação F3, auditoria real ou publicação de pareceres nesta integração.
- Se a API não responder, a interface **exibe um erro**; nunca substitui silenciosamente a resposta por dados fictícios.
- O frontend faz consultas autenticadas mas não concede acesso por conta própria: o backend decide autorizações de contrato, papel e visibilidade dos campos.

## 4. Verificações e CI

`web/scripts/smoke.cjs` continua validando a demonstração (quatro perfis).

`web/scripts/integration-smoke.cjs` simula respostas HTTP de uma API F1 no navegador Chromium e verifica: token inválido, papel derivado de `/api/me`, contratos autorizados, troca de contrato, lotes, documentos, ausência de dados sintéticos no modo API, isolamento do acesso de fornecedora, desconexão, recusa de AEJ, resposta 422 em upload inválido e criação/consulta de lote via multipart.

O GitHub Actions faz `npm ci`, TypeScript, build e exportação, além dos dois testes de navegação. **A simulação testa o cliente e a UI**. Há também um terceiro teste, `web/scripts/live-api-smoke.cjs`, que inicia o FastAPI real em loopback com `DOCRISK_DEMO_MODE=1`, usa banco SQLite efêmero, gera e processa um PDF inteiramente sintético com `AI_PROVIDER=textlayer` e confirma a consulta no navegador via CORS permitido (`http://localhost:3000`). Esse teste foi ampliado para também realizar **POST multipart pelo navegador**, confirmar o lote na API, aguardar a F2 concluir a leitura e verificar seu registro no histórico. Ele não usa Gemini nem dados pessoais e **não valida ainda as regras F3, AEJ ou produção**.

## 5. Próximas integrações

1. Reproduzir manualmente o teste Web + FastAPI local com um lote sintético e verificar o comportamento nos navegadores da equipe (o smoke do CI já cobre este fluxo no Chromium).
2. Validar a nova tela de envio e o acompanhamento do processamento em outras máquinas da equipe; limitar testes a arquivos inteiramente fictícios.
3. Corrigir a ligação da API de revisão F1 com `pipeline/revisao.py` da F2.
4. Integrar revisão, AEJ e F3 depois de seus contratos de dados estarem estáveis.

**Segurança:** antes de disponibilizar o site ou a API em ambiente público, substituir tokens demonstrativos por autenticação adequada; nunca usar `DOCRISK_DEMO_MODE=1` numa API acessível externamente.

## 6. Envio real de arquivos sintéticos

1. Inicie FastAPI e Next.js localmente conforme as seções anteriores.
2. Conecte-se em `/acesso` com o token de `u-oper-beta` ou de outro usuário da fornecedora autorizado no contrato.
3. Abra **Enviar documentos** no menu (ou pelo atalho do painel/histórico), selecione **um** PDF, PNG, JPEG ou TIFF fictício de até 20 MB e confirme que não contém dados pessoais reais.
4. Clique em **Enviar arquivo ao backend**. O frontend envia um `FormData` com `contract_id` e `file` para `POST /api/supplier/batches` usando o Bearer da sessão em memória. Não atribua manualmente `Content-Type`, pois o navegador gera o limite multipart.
5. Se receber `202`, o identificador do lote é exibido e o painel consulta `/api/batches/{id}` automaticamente a cada 2,5 segundos (por no máximo 60 verificações). Status de sucesso de recebimento **não equivale** à conclusão da F2; `CONCLUIDO` significa que a leitura terminou e não que o parecer trabalhista foi aprovado.
6. Caso a conexão falhe ou expire durante o envio, **consulte a lista de lotes antes de repetir**: o backend pode ter persistido o arquivo sem que o navegador receba a resposta.
7. Abra **Consultar histórico de lotes**, atualize a lista e inspecione os documentos consolidados.

**Limites de segurança:** esse protótipo usa tokens demonstrativos e SQLite local. Não é seguro para documentos trabalhistas reais, dados sensíveis, uso público ou ambiente de produção. A aplicação não faz inspeção antivírus nem política de retenção de produção. Arquivos AEJ exigem uma rota/normalização estruturada adicional e não devem ser enviados por esse formulário.
