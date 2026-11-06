# Integração dos seis perfis — DocRisk AI

## Composição

A branch de integração parte da main com os PRs #14, #15, #16, #17, #18, #19 e #20 já incorporados. Inclui o conteúdo do Admin Geral do PR #21, sem modificar sua branch, e as verificações consolidadas. Não faz merge na main ou deploy.

## Fluxo integrado

O teste `api/tests/test_profiles_integration.py` percorre:

1. Admin Geral cria uma nova auditora e seu administrador inicial.
2. Admin da auditora cadastra contratante, fornecedora com contrato inicial, analista e gestores empresariais.
3. Gestor da fornecedora cria dois operadores da própria organização.
4. Operador envia PDF sintético de ponto e holerite; a F2 faz a leitura offline e a conciliação registra a divergência de 4 horas. O segundo operador consulta o lote do colega.
5. Analista publica um parecer; antes da publicação, a contratante não recebe o rascunho.
6. Gestor da contratante consulta o parecer e os indicadores publicados.
7. Usuários da Bernhoeft demo, de outra fornecedora e da administração geral não acessam o lote da nova auditora. Operador não publica nem gerencia acessos; gestor da fornecedora não administra a auditora.
8. Gestor revoga o operador: o token deixa de funcionar e o lote permanece acessível ao colega.

O trabalhador T900 é previamente inserido como dado sintético de preparação do teste. O MVP ainda não possui tela própria para cadastrar trabalhadores; o teste não simula a existência dessa funcionalidade.

## Verificação de interface

O smoke offline cobre os seis perfis, a separação entre Admin Geral e Admin Bernhoeft, a equipe da fornecedora, o filtro externo “Em análise” e os pareceres da contratante. As mutações ficam desativadas na demonstração offline.

O smoke conectado reutiliza o fluxo real de envio, correção, revisão e publicação. Acrescenta cadastro/ativação/desativação de operador pelo gestor e cadastro de auditora/configuração institucional pelo Admin Geral. A configuração é conferida após recarregar a página. O smoke específico da contratante e a verificação do navegador contra FastAPI/SQLite continuam no CI existente.

## Execução consolidada

A suíte backend e o workflow frontend do PR validam a combinação. Não se repete manualmente a suíte de cada perfil. A checagem frontend inclui TypeScript, build, rotas exportadas, demonstração offline e fluxos conectados com PDF/imagem sintéticos. Os testes nunca usam documentos reais ou credenciais de produção.

## Limites mantidos

- Autenticação por token demonstrativo; cadastro corporativo, convites, recuperação de acesso e provisionamento produtivo permanecem pendentes.
- Conta geral de demonstração e mutações administrativas dependem de DOCRISK_DEMO_MODE=1.
- Indicadores da contratante derivam de pareceres publicados; dados insuficientes não atestam regularidade.
- Os três módulos futuros são informativos, sem implementação funcional.
- A identidade da fornecedora é única; contratos definem o relacionamento com as contratantes.
- Refinamento visual permanece fora desta etapa.
