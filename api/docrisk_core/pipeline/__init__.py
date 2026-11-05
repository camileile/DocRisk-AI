"""Motor documental. Dono: FRENTE 2.

Fluxo: render (lote -> páginas) -> leitura (ai/) -> segmentation (páginas -> documentos)
-> routing (APTO / PENDENTE_CORRECAO / REVISAO_HUMANA) -> worker grava e chama as
regras da frente 3 (pendências e conciliação).
"""
