# Acesso individual a contratos — DR-03 / DR-08

Analistas e operadores precisam de concessão individual vigente **e** de contrato pertencente à sua organização. Vínculo Clerk, cadastro por token de teste e convite aceito não concedem contratos automaticamente.

| Quem gerencia | Destinatário | Contratos disponíveis |
| --- | --- | --- |
| ADMIN_BH | ANALISTA_BH da própria auditora | Contratos da auditora |
| GESTOR_FORN | OPERADOR_FORN da própria fornecedora | Contratos da fornecedora |

Não é permitido delegar a outro papel, outra organização ou à própria identidade administrativa. ADMIN_PLATAFORMA/ADMIN_BH mantêm as restrições documentais existentes. Gestores mantêm o escopo organizacional que já possuíam; esta entrega restringe analistas e operadores, sem criar novos papéis.

## Operação na interface

1. O usuário aceita o convite Clerk e aparece na equipe.
2. ADMIN_BH abre **Gestão de Usuários → Gerenciar contratos de [analista]**. GESTOR_FORN abre **Operadores → Gerenciar contratos de [operador]**.
3. A gestão atribui um ou mais contratos, com validade opcional. O horário digitado usa o fuso do dispositivo; a API armazena UTC. Campo vazio significa sem data de expiração.
4. **Revogar contrato** remove apenas aquela permissão. Colegas autorizados continuam vendo os documentos, independentemente do remetente original. Outros contratos do destinatário continuam disponíveis.

Novos usuários sem concessão entram na sua identidade, mas consultam uma lista de contratos vazia. É necessário atribuir acessos depois do aceite; não se concede automaticamente um contrato novo a toda a equipe.

## API e histórico

- `GET /api/contract-access/users/{user_id}`: contratos que a gestão pode atribuir, estado efetivo e expiração.
- `PUT /api/contract-access/users/{user_id}/contracts/{contract_id}`: `{"ativo": true, "expires_at": null}` concede sem prazo. Uma data ISO 8601 com fuso define expiração futura; `{"ativo": false}` revoga.
- A decisão acontece sob transação de escrita. Repetir o mesmo PUT não duplica concessões/auditoria. Renovar validade encerra a concessão anterior e cria outra; o histórico fica em `user_contract_grants` e os eventos em `audit`.
- A função central `contratos_do_usuario` aplica as concessões em listagens, pesquisa, indicadores e recursos por ID. Revogação/expiração bloqueiam a próxima requisição autorizada; nenhum documento, análise, versão, envio ou parecer é apagado.
- O banco impõe uma única concessão não revogada por pessoa/contrato. Datas são armazenadas normalizadas em UTC.

Uma consulta direta não autorizada mantém o retorno 404 e o sinal `X-DocRisk-Contracts-Changed: 1`, exposto no CORS. O cliente atualiza contratos após esse sinal, ao ganhar foco ou a cada 30 s. Quando a lista muda, cancela requisições antigas, remonta telas e escolhe um contrato ainda autorizado; não encerra a identidade. Sem concessões restantes, limpa a seleção. A verificação da API não depende desse intervalo da interface. Uma operação já iniciada antes da revogação não é cancelada retroativamente no servidor.

## Atualização de banco existente

O startup cria a tabela e o índice de forma aditiva; não modifica dados documentais. **Não há backfill automático de acessos operacionais.** Depois de atualizar uma instalação Clerk, os responsáveis devem atribuir os contratos aos analistas e operadores existentes pelas telas acima. Até isso acontecer, ficam sem contratos.

Somente a inicialização demo/token prepara concessões explícitas para as personas sintéticas fixas (`u-analista`, `u-oper-beta`, `u-oper-gama`) e seus contratos originais. Reiniciar não reativa uma concessão já revogada/expirada nem concede outros contratos. Nenhuma concessão é criada pelo seed em modo Clerk.

## Verificação

`api/tests/test_contract_access.py` cobre usuários novos sem acesso, contratos da mesma organização com permissões distintas, colegas, revogação seletiva, expiração, renovação, repetição de PUT, persistência após reinício, auditoria, organização externa, administrador da plataforma, listagens, métricas, AEJ, originais, páginas, revisão, reprocessamento, reenvio e publicação. A cobertura Clerk usa JWT RSA e provedor simulado, sem e-mails reais.

Os testes existentes de integração e colaboração passam agora pela concessão explícita. Regressões de transporte e sessão cobrem respostas antigas, limpeza de contratos e ausência de logout ou ciclo de remontagem em recusas repetidas.

O smoke `web/scripts/contract-access-smoke.cjs`, incluído no CI frontend, usa navegador + FastAPI + SQLite reais e dados sintéticos: atribuição por gestor/Admin BH, acesso a envio de colega, revogação com documento aberto, limpeza da tela e preservação de outro contrato/histórico. Requer a instalação local de demonstração descrita nos demais smokes. `CHROMIUM_EXECUTABLE_PATH` é opcional para usar Chromium já instalado.

O build Clerk e a autorização simulada não substituem o aceite na instância Clerk real. Essa ativação permanece uma pendência separada do MVP.
