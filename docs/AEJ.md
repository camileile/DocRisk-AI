# Integração de AEJ

AEJ entra como dado estruturado. O worker não cria páginas rasterizadas e não chama Gemini, Tesseract nem TextLayer. O lote recebe total_pages=0; a quantidade de registros é consultada em aej_imports.validation_json.

## Preservação e rastreabilidade

- O arquivo original permanece em DATA_DIR/uploads, com o SHA-256 já registrado em batches.
- Cada linha decodificada é preservada em aej_records, com tipo, número da linha, vínculo AEJ e texto original da linha. O arquivo original conserva também os bytes e finais de linha exatos.
- aej_imports guarda o período, a versão do parser, os avisos estruturais e se havia marcador P7S.
- Cada ESPELHO_PONTO aponta para aej_documents, que guarda a derivação, avisos, dias, pares de marcação e linhas de origem, inclusive horário contratual e eventos de compensação. Os insumos da conciliação também carregam a origem e as linhas de referência.
- O arquivo original pode ser baixado por GET /api/batches/{id}/source, para usuários da fornecedora do contrato ou da Bernhoeft com acesso ao lote.

As linhas AEJ podem conter dados pessoais; ficam no armazenamento privado da aplicação e não são devolvidas pela API de documentos. O endpoint de download devolve o original aos papéis que já podem ler o lote.

## Mapeamento de trabalhadores

O identificador de vínculo AEJ não é inferido por nome ou CPF. Um usuário Bernhoeft associa explicitamente vínculo e trabalhador do contrato:

    PUT /api/contracts/CT-001/aej-mappings/1
    Authorization: Bearer <token>
    Content-Type: application/json

    {"worker_id":"T001"}

GET /api/contracts/{contract_id}/aej-mappings lista os mapeamentos existentes. O vínculo não mapeado permanece em revisão. É possível mapear depois do upload; documentos pendentes são associados e recalculados. Um trabalhador não pode ser ligado a dois vínculos no mesmo contrato.

## Estimativa e revisão

O parser agrupa as marcações pelo vínculo, data e sequência entrada/saída. Compara o tempo observado nos pares com durJornada do horário contratual, em minutos, e soma apenas excedentes diários observados. É uma medida de triagem, não uma conclusão legal de horas extras: o cálculo não apura banco de horas semanal ou regras externas ao arquivo.

O leiaute oficial define durJornada em minutos e associa as marcações ao vínculo e à sequência do par entrada/saída ([Anexo VI da Portaria MTP 671/2021, compilada pelo MTE](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/legislacao/portarias-1/portarias-vigentes-3/PDFPortarian671de8denovembrode2021compilada07.01.2026.pdf)).

Marcações desconsideradas, incluídas manualmente, pré-assinaladas, por exceção, pares incompletos/ambíguos, horário não identificado, registros de ausência/compensação e vínculo não mapeado exigem revisão. Nesses casos o sistema não envia um total presumido à conciliação. A revisão mostra datas, marcações, linhas de origem e permite ao analista confirmar horas com justificativa; o valor confirmado e o revisor ficam registrados sem apagar o cálculo original.

O parser não valida criptograficamente a assinatura P7S. O documento e a interface identificam essa limitação. O resultado STRUCTURAL_PARTIAL continua indicando validação estrutural parcial.
