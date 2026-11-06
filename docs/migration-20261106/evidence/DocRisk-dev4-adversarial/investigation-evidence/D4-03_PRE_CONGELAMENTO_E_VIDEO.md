# D4-03 — Pré-congelamento e vídeo de contingência — 06/11/2026

Status: PARCIAL. Este documento prepara o procedimento; não há vídeo gravado nem SHA de release congelado.

## Evidência preservada

Ensaio conectado anterior: base f085df4, branch D4-03 fd97fd3, 7/7 etapas em 70,8s. O JSON original permanece em ../DocRisk-dev4-reconcile/dev4-evidence/d4-03-final-rehearsal.json. Não substituir esse resultado por uma execução de outra revisão. A main consultada nesta etapa é 1148e76 (PR #49), posterior ao ensaio; a evidência antiga não valida automaticamente o novo parecer corporativo.

## Condições para escolher o SHA

- Correção D4-09 revisada por Dev1/Dev2, regressões determinísticas e suíte completa aprovadas, sem apenas suprimir IntegrityError.
- PRs autorizados, CI remoto aprovado e integração autorizada concluída. As branches Dev4 são irmãs: aprovar cada uma separadamente não valida a combinação.
- Selecionar o commit de integração exato e registrar SHA completo, versões Python/Node, dependências, comando de build, configuração sem segredos, hash dos artefatos e resultados de teste. Não usar nome móvel de branch como identificação da release.
- Repetir o ensaio das sete etapas no commit candidato integrado, incluindo comportamento do PR #49, demo isolada e restauração aplicável. Somente depois aprovar congelamento; sem tag, push ou deploy nesta etapa.
- Decidir escopo da apresentação: TextLayer offline não representa uma chamada Gemini. Piloto real continua condicionado a identidade/provisionamento, infraestrutura e licenças.
- Definir destino e responsável pelo vídeo e ter arquivo local disponível sem rede. Este item ainda não foi executado.

## Procedimento de gravação (roteiro executável, ainda não realizado)

1. Em worktree próprio do commit candidato, criar dados inteiramente sintéticos em diretório temporário novo. Usar TextLayer e configuração demo local. Usar somente portas livres; nunca encerrar processo que não pertença ao ensaio.
2. Executar o orquestrador release-rehearsal.cjs com saída JSON, guardar logs e conferir as sete etapas. Registrar o SHA e os hashes antes de iniciar a captura.
3. No gravador local disponível, selecionar apenas a janela da apresentação. Mostrar uma cartela com projeto, SHA curto, data e indicação de dados sintéticos/leitor offline. Não enquadrar formulários com tokens, .env ou console que exponha credenciais.
4. Gravar o roteiro: demonstração offline sem API; operação conectada e consulta do lote; simulação de queda da API do ensaio; mensagem de indisponibilidade; reinício; consulta mostrando persistência e processamento consistente. Se a captura exigir repetição manual, usar nova execução com os mesmos parâmetros, sem encenar um resultado diferente do verificado.
5. Encerrar captura e reproduzir o arquivo inteiro. Conferir legibilidade, sequência, ausência de dados reais/credenciais e funcionamento sem internet. Documentar duração, resolução e formato efetivos; MP4 reproduzível localmente é uma opção, não requisito já atendido.
6. Registrar SHA-256 do vídeo, tamanho, duração, SHA do código, relatório do ensaio e local da cópia de contingência. Conservar vídeo e manifesto juntos. Não publicar nem anexar externamente sem autorização.

## Critério de conclusão

Pré-requisitos aprovados + commit candidato integrado e identificado + ensaio nesse commit + vídeo gravado e reproduzido integralmente + evidências vinculadas. Até isso ocorrer, D4-03 permanece PARCIAL, mesmo com o ensaio histórico 7/7.
