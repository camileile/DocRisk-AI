# D2-12 — Estados e fórmulas de comprovantes

`docrisk_core.rules.comprovantes` define a classificação e as fórmulas puras, sem alterar os estados públicos de documentos.

| Estado do comprovante | Regra no classificador |
|---|---|
| Não recebido | Nenhuma versão vigente apresentada |
| Recebido | Versão vigente recebida, ainda sem aprovação humana |
| Em revisão | Documento em `REVISAO_HUMANA` |
| Conferido | Documento `APTO` com `revisado_por` preenchido |
| Insuficiente | Documento em `PENDENTE_CORRECAO` |
| Rejeitado | Estado futuro de obrigação; não existe ação correspondente no fluxo atual |

Versões `SUBSTITUIDO` são excluídas; por obrigação, usa-se apenas a versão vigente de maior versão e ID. Obrigações não exigíveis não entram na população. Reenvios são contados à parte e não aumentam o denominador.

- Recebimento = recebido + em revisão + conferido + insuficiente, dividido pelas obrigações exigíveis. Rejeitado não conta como evidência válida recebida.
- Conferência = conferidos / obrigações exigíveis.
- Insuficiência = insuficientes / obrigações avaliadas (conferidos + insuficientes + rejeitados).
- Pendências = obrigações exigíveis menos conferidas.
- Denominadores zero retornam `null` nas taxas.

## Integração ainda pendente

O banco atual não possui calendário/tabela de obrigações nem validade temporal de trabalhadores. Por isso, este PR entrega o dicionário, o cálculo puro e os testes de fórmula, mas não liga as taxas a um dashboard: preencher a população a partir de documentos enviados faria períodos sem envio desaparecerem do denominador e poderia tratar comprovante opcional como exigível. A ligação precisa aguardar D2-11/D2-13 e a confirmação de quando comprovante de pagamento é obrigatório.

`REJEITADO` também não pode ser gravado pela API até a equipe aprovar a mudança do contrato compartilhado de estados. O classificador suporta o valor como entrada futura, sem mudar `contracts.py` ou `schema.sql`.
