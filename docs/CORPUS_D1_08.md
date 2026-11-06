# D1-08 — corpus sintético e holdout

## Desenvolvimento

`api/scripts/gerar_corpus_d1_08.py` gera um PDF e gabarito com semente fixa para uso em testes e inventário do benchmark. A amostra tem 7 casos e 9 páginas: scan sem camada de texto, rotação, documento multipágina, página faltante, documento ausente, continuação com identidade conflitante e holerite com horas apenas em reais. Todos os documentos são fictícios.

O teste compara segmentação, tipo e roteamento com os rótulos definidos antes da execução do motor. O benchmark apenas registra a composição e o hash do PDF de desenvolvimento; os números de desempenho continuam vindo do lote separado de 100 trabalhadores.

## Holdout congelado

`api/tests/fixtures/d1_08/corpus_holdout.pdf` e `gabarito_holdout.json` são a amostra reservada de avaliação. Eles foram gerados com textos, competência, layout e rotação distintos do desenvolvimento. O benchmark e os testes funcionais não carregam nem pontuam esse conjunto. A suíte só verifica os hashes para sinalizar alteração acidental:

```text
corpus_holdout.pdf       CA3518ED74248D6AC8BFB01929C568ED916B64A5D0B930DAA745DBA79226F18C
gabarito_holdout.json    B33C7A5157083EE06F77BF7378678F5569CED65F6CF4E777A43E0AE210E4DE7C
```

Não regenere nem use o holdout para ajustar regras durante o desenvolvimento. Uma avaliação deve acontecer depois de congelar o código candidato; seus resultados devem ser registrados separadamente, com os hashes acima.

## Limites

O corpus é inteiramente sintético. Ele exercita formatos e ambiguidades estruturais, mas não representa prevalência, qualidade ou linguagem de documentos reais e não sustenta uma estimativa de precisão em produção.
