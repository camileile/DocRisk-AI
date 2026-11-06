# Adendo final de verificação — migração 06/11/2026

Foram preservadas e conferidas 124 branches de código/histórico/documentação (123 já registradas anteriormente mais backup/migration-20261106/loose-file-history). Essa branch adicional mantém 49 versões intermediárias de arquivos sem commit associado, sem alterar código funcional. O conteúdo de cada blob mantém seu SHA original.

O relatório principal contém a tabela das 122 referências de payload e o guia foi publicado depois dessa fotografia; ambos continuam válidos. O SHA atual do guia é obtido por git ls-remote origin refs/heads/backup/migration-20261106/notebook-guide. A referência de história solta tem SHA e1569ff75c70ea30f784772fc9e32c9bf079e532.

Código e evidências publicáveis estão no GitHub. Continuam SOMENTE NESTE COMPUTADOR: api/.env, api/data e os seis diretórios de dados privados listados no guia; estados temporários/caches permanecem locais e são geralmente recriáveis. Não se declara completa a transferência privada. Nenhuma main foi alterada, nenhum merge/rebase/force push/PR/deploy foi executado nesta operação.

Guia: RECUPERAR_NO_NOTEBOOK.md. Relatório: RELATORIO_BACKUP.md. Os dois testes D4-09 continuam intactos e falhando no estado histórico. O backup não aprova integração/release.
