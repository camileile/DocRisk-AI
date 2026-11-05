"""Gera o lote SINTÉTICO de demonstração + gabarito. Dono: FRENTE 3.

Uso: python scripts/gerar_lote_demo.py [pasta_saida]   (padrão: scripts/lote_demo)

Saídas planejadas:
- lote_demo.pdf            16 páginas, 14 documentos, competência 10/2026
- reenvio_holerite_T002.pdf  holerite legível do T002 (6 h extras)
- arquivo_corrompido.pdf   para o teste de recusa
- gabarito.json            fronteiras, tipos, trabalhador, competência, campos e
                           resultado esperado da conciliação por trabalhador

Cenários (todos com o aviso "DOCUMENTO FICTÍCIO" no rodapé):
| Páginas | Documento                                  | Esperado                          |
| 1-2     | Contrato de prestação (2 págs)             | organizado, sem análise           |
| 3-4     | Espelho de ponto T001, 12 h extras (2 págs)| —                                 |
| 5       | Holerite T001, 8 h extras                  | T001: divergência de 4 h a conferir |
| 6       | Espelho de ponto T002, 6 h                 | —                                 |
| 7       | Holerite T002 com corpo ilegível           | pendência à fornecedora; T002 bloqueado |
| 8       | Comprovante de pagamento T001              | evidência presente                |
| 9       | Espelho de ponto T003 "Página 1 de 2" só   | página faltante; T003 bloqueado   |
| 10      | Holerite T003, 2 h                         | —                                 |
| 11      | Documento de identidade FICTÍCIO           | organizado                        |
| 12      | Espelho de ponto T004, 10 h                | —                                 |
| 13      | Holerite T004 com horas extras só em R$    | T004: dados insuficientes         |
| 14      | Anotação solta sem título                  | desconhecido -> revisão humana    |
| 15-16   | Ponto e holerite T005, 4 h e 4 h           | T005: sem divergência             |

"Página X de Y" no RODAPÉ (como em documento real). A base de 100 trabalhadores
(spec seção 10) vem depois, com o mesmo gerador parametrizado.
"""
from __future__ import annotations

import sys
from pathlib import Path


def gerar(saida: Path) -> dict[str, Path]:
    """Cria os arquivos acima em `saida` e devolve {nome: caminho}."""
    raise NotImplementedError("Frente 3: gerar")


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("lote_demo")
    for nome, caminho in gerar(destino).items():
        print(f"{nome}: {caminho}")
