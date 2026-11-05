# DocRisk AI · Sprint 01 — Núcleo de importação (POC)

Primeiro pacote **executável**, ainda **não é um MVP completo nem é seguro para produção**.
A base sintética de 100 trabalhadores **não foi criada**.

## O que está implementado

- Um ponto de entrada para **PDF, PNG, JPEG e AEJ**; validação simples do formato real do arquivo e hash SHA-256.
- PDF: extração do texto digital quando disponível; **Tesseract** local em páginas escaneadas. Imagem: OCR local.
- Classificação inicial por títulos conhecidos (ponto, folha/holerite, comprovante, contrato etc.).
- **Segmentação apenas heurística**, com agrupamentos de páginas candidatos e `needs_review = true`; nunca apresentada como resultado final automático.
- AEJ: parser dos registros do Anexo VI 671/2021 com verificação estrutural parcial, vínculos, marcações, cabeçalho, trailer e referências. AEJ não passa por OCR.
- Resposta normalizada de inspeção, sem conteúdo de OCR nem nome/CPF do AEJ expostos na API.
- Testes automatizados de ingestão básica, agrupamento, AEJ e bloqueio do endpoint fora do modo demo.

## Requisitos locais

Python 3.11+; Tesseract instalado com idiomas `por` e `eng`.

```bash
cd docrisk_ai_sprint01
python -m venv .venv
source .venv/bin/activate     # no Windows: .venv\\Scripts\\activate
pip install -e '.[test]'
pytest -q
```

### Inspeção em terminal

```bash
docrisk-inspect caminho/para/lote.pdf
# ou
python -m docrisk_core.cli caminho/para/jornada.aej
```

### API local, somente para desenvolvimento

```bash
DOCRISK_DEMO_MODE=1 uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000
# Interface Swagger local: http://127.0.0.1:8000/docs
# POST /api/v1/inspect, multipart 'file'
```

**Não utilizar `--host 0.0.0.0` nem publicar esta API:** ainda faltam autenticação,
RBAC por empresa/contrato, criptografia, filas duráveis, armazenamento privado,
proteção contra abuso e gestão de arquivos sensíveis. A API trabalha só em memória.

## Limitações reconhecidas

1. OCR não é IA multimodal; a integração visual-linguística permanece para a próxima etapa.
2. Heurística de fronteiras NÃO resolve PDFs reais de forma robusta; todos os grupos requerem revisão.
3. Nenhuma pontuação estatística de confiança é calculada nesta etapa.
4. Parser AEJ é **parcial**: não valida assinaturas P7S nem cobre toda a conformidade legal ou o cálculo da jornada.
5. Nenhum trabalho de análise salarial, bloqueio de trabalhador, indicadores e parecer foi implementado ainda.
6. Nenhum documento real ou base de 100 trabalhadores foi gerado ou usado.

## Próxima entrega e divisão para equipe

| Frente | Próxima tarefa técnica | Critério de aceite |
|---|---|---|
| Processamento | Substituir heurísticas por detector de fronteiras e agrupamento com testes de múltiplas páginas | Revisão visual e gabarito de limites |
| Document AI | Integrar modelo multimodal para layouts controlados e extração estruturada | Campos de ponto/folha com evidências por página |
| AEJ | Completar parser e validação de records 01..08, 99 e assinatura | Testes com amostras oficiais compatíveis |
| Identidade | Vincular trabalhador e competência com correspondência única | Ambiguidade bloqueia associação automática |
| Plataforma | Implementar autenticação e RBAC antes de disponibilizar upload remoto | Usuário de uma empresa não lê dados de outra |
| Qualidade | Testar PDFs mistos, OCR, rejeições e falhas | Medições com gabarito e registro de falhas |

## Referência oficial AEJ

- Ministério do Trabalho e Emprego — [Leiaute do AEJ, Anexo VI da Portaria 671](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/fiscalizacao-do-trabalho/leiaute-do-arquivo-eletronico-de-jornada-aej.pdf)

## Licenciamento / colaboração

Código de ponto de partida do grupo; definir licença e responsável pelo repositório antes de publicá-lo em nome da equipe.
