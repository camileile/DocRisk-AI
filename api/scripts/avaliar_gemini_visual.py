"""Avalia o Gemini real em 16 páginas sintéticas, sem fallback para mocks/TextLayer.

Execução com chamadas remotas e possível cobrança:
    python scripts/avaliar_gemini_visual.py --executar

Sem --executar, apenas valida e informa o corpus, sem chamada de rede.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = API_DIR.parent
sys.path.insert(0, str(API_DIR))

from docrisk_core import config  # noqa: E402
from docrisk_core.ai import ErroIA, VERSAO_PROMPT  # noqa: E402
from docrisk_core.ai.gemini import GeminiProvider  # noqa: E402
from docrisk_core.pipeline.render import iterar_paginas  # noqa: E402
from gerar_lote_demo import gerar  # noqa: E402

GABARITO_PATH = REPO_DIR / "docs" / "GABARITO_AVALIACAO_GEMINI.json"
RELATORIO_PATH = REPO_DIR / "docs" / "AVALIACAO_VISUAL_GEMINI.md"
RESULTADO_PATH = REPO_DIR / "docs" / "AVALIACAO_VISUAL_GEMINI.json"
CAMPOS = ("tipo", "inicio_documento", "pagina_x", "pagina_de", "trabalhador_id",
          "competencia", "legivel", "campos.horas_extras_h", "campos.horas_extras_valor",
          "campos.valor_pago", "campos.data_pagamento")


def _pegar(dados: dict[str, Any], caminho: str) -> Any:
    atual: Any = dados
    for parte in caminho.split("."):
        atual = atual.get(parte) if isinstance(atual, dict) else None
    return atual


def _igual(esperado: Any, obtido: Any) -> bool:
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        return isinstance(obtido, (int, float)) and abs(float(esperado) - float(obtido)) <= 0.01
    return esperado == obtido


def _analise_json(analise: Any) -> dict[str, Any]:
    return {
        "tipo": analise.tipo.value,
        "inicio_documento": analise.inicio_documento,
        "pagina_x": analise.pagina_x,
        "pagina_de": analise.pagina_de,
        "trabalhador_id": analise.trabalhador_id,
        "competencia": analise.competencia,
        "legivel": analise.legivel,
        "campos": {
            "horas_extras_h": analise.campos.horas_extras_h,
            "horas_extras_valor": analise.campos.horas_extras_valor,
            "valor_pago": analise.campos.valor_pago,
            "data_pagamento": analise.campos.data_pagamento,
        },
    }


def _gerar_pdf() -> bytes:
    with tempfile.TemporaryDirectory(prefix="docrisk-gemini-visual-") as tmp:
        arquivos = gerar(Path(tmp))
        return arquivos["lote_demo.pdf"].read_bytes()


def _comparar(esperado: dict[str, Any], obtido: dict[str, Any]) -> list[str]:
    return [campo for campo in CAMPOS
            if not _igual(_pegar(esperado, campo), _pegar(obtido, campo))]


def _markdown(resultado: dict[str, Any]) -> str:
    linhas = [
        "# Avaliação visual Gemini — corpus sintético",
        "",
        f"- Status: **{resultado['status']}**",
        f"- Data UTC: {resultado['created_at']}",
        f"- Leitor: Gemini real via `GeminiProvider`; nenhum mock ou fallback.",
        f"- Modelo configurado: `{resultado['model']}`",
        "- Corpus: 16 páginas de documentos fictícios renderizados do PDF a 150 DPI.",
        "- Casos: contrato multipágina, ponto multipágina, holerite borrado, comprovante, identidade, página faltante, horas apenas em R$ e anotação sem tipo claro.",
        "- Dados pessoais reais: nenhum.",
        "",
    ]
    if resultado["status"] in {"BLOQUEADA_SEM_CREDENCIAL", "PREPARADO_SEM_CHAMADAS"}:
        if resultado["status"] == "PREPARADO_SEM_CHAMADAS":
            linhas.extend([
                "## Execução não solicitada",
                "",
                "Nenhuma chamada foi enviada. Para iniciar a avaliação multimodal, configure credencial, modelo e cota e execute o comando abaixo:",
                "",
            ])
        else:
            linhas.extend([
                "## Bloqueio",
                "",
                "Não foi encontrada `GEMINI_API_KEY` no ambiente nem em `api/.env`. Nenhuma chamada foi enviada; não existem tempos ou acurácia Gemini nesta execução.",
                "O identificador de modelo é o valor configurado localmente; não foi validado na conta. Cota e cobrança também não foram consultadas.",
                "",
                "Para executar quando houver credencial, modelo e cota autorizados:",
                "",
            ])
        linhas.extend([
            "```powershell",
            "cd api",
            ".\\.venv\\Scripts\\python.exe scripts/avaliar_gemini_visual.py --executar",
            "```",
            "",
            "`--executar` opta por chamadas reais, uma por página, e pode gerar cobrança da conta configurada. Sem essa opção, o script não chama a rede.",
            "",
        ])
        return "\n".join(linhas)

    linhas.extend([
        f"- Páginas concluídas: {resultado['completed_pages']}/16",
        f"- Tempo total: {resultado['elapsed_seconds']:.2f} s (inclui limitador de RPM e retentativas).",
        f"- Latência por página: média {resultado['latency_ms']['mean']:.0f} ms; mediana {resultado['latency_ms']['median']:.0f} ms; máximo {resultado['latency_ms']['max']:.0f} ms.",
        "",
        "## Acerto por campo",
        "",
        "| Campo | Acertos | Total |",
        "|---|---:|---:|",
    ])
    for campo, medicao in resultado["field_accuracy"].items():
        linhas.append(f"| `{campo}` | {medicao['correct']} | {medicao['total']} |")
    linhas.extend(["", "## Comparação por página", "",
                   "| Página | Caso | Tipo esperado → obtido | Trabalhador esperado → obtido | Campos incorretos | Latência (ms) | Erro |",
                   "|---:|---|---|---|---|---:|---|"])
    for pagina in resultado["pages"]:
        linhas.append(
            f"| {pagina['page']} | {pagina['document']} | {pagina['expected']['tipo']} → {pagina.get('actual', {}).get('tipo', '—')} "
            f"| {pagina['expected']['trabalhador_id']} → {pagina.get('actual', {}).get('trabalhador_id', '—')} "
            f"| {', '.join(pagina.get('mismatches', [])) or '—'} | {pagina.get('latency_ms', '—')} | {pagina.get('error', '—')} |"
        )
    linhas.extend([
        "",
        "A comparação usa o gabarito manual versionado em `GABARITO_AVALIACAO_GEMINI.json`; valores numéricos têm tolerância de 0,01. Os resultados medem apenas este corpus sintético e esta configuração, sem estimar desempenho em documentos reais.",
        "",
        "O JSON completo, com valores esperados e extraídos por página e sem o texto OCR, está em `AVALIACAO_VISUAL_GEMINI.json`.",
        "",
    ])
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avaliação multimodal Gemini em corpus fictício.")
    parser.add_argument("--executar", action="store_true", help="autoriza as chamadas reais à API; pode haver cobrança")
    args = parser.parse_args(argv)

    gabarito = json.loads(GABARITO_PATH.read_text(encoding="utf-8"))
    pdf = _gerar_pdf()
    paginas = list(iterar_paginas(pdf, "PDF", filename="lote_demo.pdf"))
    if len(paginas) != len(gabarito["pages"]):
        raise RuntimeError(f"Corpus mudou: esperado {len(gabarito['pages'])} páginas, obtido {len(paginas)}.")
    if [r["page"] for r in gabarito["pages"]] != list(range(1, len(paginas) + 1)):
        raise RuntimeError("Gabarito manual deve cobrir, em ordem, todas as páginas do corpus.")

    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    resultado: dict[str, Any] = {
        "status": "PREPARADO_SEM_CHAMADAS" if not args.executar else "",
        "created_at": agora, "provider": "gemini", "model": config.GEMINI_MODEL,
        "prompt_version": VERSAO_PROMPT, "corpus": gabarito["corpus"], "pages_total": len(paginas),
        "completed_pages": 0, "pages": [], "field_accuracy": {}, "elapsed_seconds": 0.0,
        "latency_ms": None,
    }

    if not args.executar:
        resultado["status"] = "PREPARADO_SEM_CHAMADAS"
        resultado["note"] = "Modo de preparação; nenhuma chamada remota foi feita."
    elif not config.GEMINI_API_KEY:
        resultado["status"] = "BLOQUEADA_SEM_CREDENCIAL"
        resultado["note"] = "GEMINI_API_KEY ausente; nenhuma chamada remota foi feita."
    else:
        provider = GeminiProvider()
        inicio_total = time.perf_counter()
        tempos: list[int] = []
        acertos = {campo: 0 for campo in CAMPOS}
        totais = {campo: 0 for campo in CAMPOS}
        for renderizada, rotulo in zip(paginas, gabarito["pages"], strict=True):
            item: dict[str, Any] = {"page": renderizada.ordem, "document": rotulo["document"],
                                    "expected": rotulo["expected"]}
            inicio = time.perf_counter()
            try:
                analise = provider.analisar(renderizada.png)
                latencia = int((time.perf_counter() - inicio) * 1000)
                tempos.append(latencia)
                item["latency_ms"] = latencia
                item["actual"] = _analise_json(analise)
                item["mismatches"] = _comparar(item["expected"], item["actual"])
                for campo in CAMPOS:
                    totais[campo] += 1
                    acertos[campo] += int(campo not in item["mismatches"])
                resultado["completed_pages"] += 1
            except ErroIA as exc:
                item["error"] = type(exc).__name__
                item["latency_ms"] = int((time.perf_counter() - inicio) * 1000)
                tempos.append(item["latency_ms"])
                item["mismatches"] = list(CAMPOS)
                for campo in CAMPOS:
                    totais[campo] += 1
            resultado["pages"].append(item)
        resultado["elapsed_seconds"] = time.perf_counter() - inicio_total
        resultado["latency_ms"] = {
            "mean": statistics.mean(tempos) if tempos else 0,
            "median": statistics.median(tempos) if tempos else 0,
            "max": max(tempos, default=0),
        }
        resultado["field_accuracy"] = {
            campo: {"correct": acertos[campo], "total": totais[campo]}
            for campo in CAMPOS
        }
        resultado["status"] = "EXECUTADA" if resultado["completed_pages"] == len(paginas) else "PARCIAL_COM_ERROS"

    if resultado["status"] == "PREPARADO_SEM_CHAMADAS":
        print(_markdown(resultado))
        return 0

    RESULTADO_PATH.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    relatorio = _markdown(resultado)
    RELATORIO_PATH.write_text(relatorio, encoding="utf-8")
    print(relatorio)
    print(f"Relatório: {RELATORIO_PATH}")
    print(f"Dados: {RESULTADO_PATH}")
    return 2 if resultado["status"] == "BLOQUEADA_SEM_CREDENCIAL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
