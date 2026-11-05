"""Prova de conceito: UMA página fictícia lida pelo Gemini. Dono: FRENTE 2.

Uso (dentro de api/, com GEMINI_API_KEY em api/.env):
    python -m docrisk_core.ai.poc_gemini                 # gera um holerite fictício e lê
    python -m docrisk_core.ai.poc_gemini caminho.pdf     # lê a 1ª página de um arquivo
    python -m docrisk_core.ai.poc_gemini --modelos       # lista modelos disponíveis na conta

Mostra tipo, campos, indicadores e o tempo da chamada. Não imprime o texto completo
nem a chave. Uma falha é relatada sem derrubar o processo com traceback.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import fitz

from . import ErroIA
from .gemini import GeminiProvider, listar_modelos_visao
from ..pipeline.render import ArquivoInvalido, iterar_paginas


def holerite_ficticio() -> bytes:
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    linhas = [
        ("DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO", 14),
        ("Empregador: Fornecedora Beta Serviços (fictícia)", 10),
        ("Trabalhador: Trabalhador Fictício 001    Matrícula: T001", 10),
        ("Competência: 10/2026", 10),
        ("Código | Descrição | Referência | Proventos | Descontos", 10),
        ("001 Salário base | 30 dias | R$ 1.800,00 |", 10),
        ("002 Horas extras 50% | Ref.: 8,00 h | R$ 160,00 |", 10),
        ("003 INSS | | | R$ 157,30", 10),
        ("Líquido a receber: R$ 1.802,70", 11),
    ]
    y = 70
    for texto, tam in linhas:
        p.insert_text((50, y), texto, fontsize=tam, fontname="helv")
        y += tam + 12
    p.insert_text((50, 815), "DOCUMENTO FICTÍCIO — TESTE", fontsize=7, fontname="helv")
    p.insert_text((480, 815), "Página 1 de 1", fontsize=8, fontname="helv")
    data = doc.tobytes()
    doc.close()
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lê 1 página com o Gemini (dados fictícios).")
    ap.add_argument("arquivo", nargs="?", type=Path)
    ap.add_argument("--modelos", action="store_true", help="lista modelos da conta")
    args = ap.parse_args(argv)
    try:
        if args.modelos:
            for nome in listar_modelos_visao():
                print(nome)
            return 0
        data = args.arquivo.read_bytes() if args.arquivo else holerite_ficticio()
        pagina = next(iterar_paginas(data, filename=args.arquivo.name if args.arquivo else "poc.pdf"))
        provedor = GeminiProvider()
        inicio = time.monotonic()
        analise = provedor.analisar(pagina.png)
        ms = int((time.monotonic() - inicio) * 1000)
    except (ErroIA, ArquivoInvalido) as exc:
        print(f"FALHA: {exc}", file=sys.stderr)
        return 1
    print(f"modelo: {provedor.modelo}  |  tempo: {ms} ms")
    print(f"tipo: {analise.tipo.value}  (confiança {analise.confianca_tipo:.2f})")
    print(f"trabalhador: {analise.trabalhador_id}  competência: {analise.competencia}")
    print(f"página: {analise.pagina_x} de {analise.pagina_de}  início de documento: {analise.inicio_documento}")
    print(f"legível: {analise.legivel}  qualidade: {analise.qualidade:.2f}")
    print(f"campos: {analise.campos.model_dump()}")
    print(f"texto reconhecido: {len(analise.texto)} caracteres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
