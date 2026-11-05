"""Leitor estrutural parcial de AEJ, Anexo VI da Portaria MTP 671/2021.

Apenas importa e valida um subconjunto dos registros. NÃO autentica assinatura
P7S, não calcula horas extras e não é validador fiscal/legal de AEJ.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, date
from typing import Any
import re

ALLOWED = {"01", "02", "03", "04", "05", "06", "07", "08", "99"}
MANDATORY_FIELDS = {"01": 10, "02": 4, "03": 4, "04": 5, "05": 8,
                    "06": 3, "07": 4, "08": 7, "99": 9}

class AEJError(ValueError):
    pass

def _date(value: str, kind: str, line_number: int) -> None:
    try:
        if kind == "date":
            date.fromisoformat(value)
        else:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError as exc:
        raise AEJError(f"Linha {line_number}: data inválida em campo {kind}") from exc

def parse_aej(content: bytes) -> dict[str, Any]:
    if not content or len(content) > 10 * 1024 * 1024:
        raise AEJError("AEJ vazio ou acima do limite de 10 MB desta prova de conceito")
    # Leiaute oficial exige ISO 8859-1. P7S não é processado aqui.
    text = content.decode("iso-8859-1")
    raw_lines = text.splitlines()
    if not raw_lines or any(not line.strip() for line in raw_lines):
        raise AEJError("AEJ vazio ou com linha em branco")

    warnings: list[str] = []
    rows: list[tuple[int, str, list[str]]] = []
    for number, line in enumerate(raw_lines, start=1):
        if line.startswith("ASSINATURA_DIGITAL_EM_ARQUIVO_P7S"):
            warnings.append("Marcador de assinatura P7S presente; assinatura não foi validada")
            continue
        fields = line.split("|")
        # Alguns geradores acrescentam | ao fim; tolerado, mas alertado.
        if fields and fields[-1] == "":
            fields.pop()
            warnings.append(f"Linha {number}: delimitador final extra")
        kind = fields[0] if fields else ""
        if kind not in ALLOWED:
            raise AEJError(f"Linha {number}: tipo de registro inválido")
        if len(fields) < MANDATORY_FIELDS[kind]:
            raise AEJError(f"Linha {number}: registro {kind} incompleto")
        rows.append((number, kind, fields))
    if not rows or rows[0][1] != "01" or rows[-1][1] != "99":
        raise AEJError("AEJ deve conter cabeçalho 01 e trailer 99")

    counts = Counter(kind for _, kind, _ in rows)
    if counts["01"] != 1 or counts["99"] != 1:
        raise AEJError("AEJ deve conter um cabeçalho e um trailer")
    header = rows[0][2]
    _date(header[6], "date", rows[0][0]); _date(header[7], "date", rows[0][0])
    _date(header[8], "datetime", rows[0][0])
    if header[9] != "001":
        warnings.append("Versão do leiaute diferente de 001; compatibilidade não verificada")

    worker_keys: set[str] = set()
    worker_rows: list[dict[str, str]] = []
    for number, kind, fields in rows:
        if kind == "03":
            link_id, cpf = fields[1], fields[2]
            if not link_id.isdigit() or not re.fullmatch(r"\d{11}", cpf):
                raise AEJError(f"Linha {number}: vínculo/identificador de trabalhador inválido")
            if link_id in worker_keys:
                raise AEJError(f"Linha {number}: vínculo duplicado")
            worker_keys.add(link_id)
            # Nunca expõe nome/CPF no resumo não autenticado.
            worker_rows.append({"vinculo_aej": link_id})
        elif kind == "05":
            _date(fields[2], "datetime", number)
            if fields[4] not in {"E", "S", "D"}:
                raise AEJError(f"Linha {number}: tipo de marcação inválido")
            if fields[6] not in {"O", "I", "P", "X", "T"}:
                raise AEJError(f"Linha {number}: fonte da marcação inválida")
            if fields[4] == "D" or fields[6] == "I":
                if len(fields) <= 8 or not fields[8].strip():
                    warnings.append(f"Linha {number}: motivo ausente em marcação ajustada")
        elif kind == "07":
            _date(fields[3], "date", number)
    for number, kind, fields in rows:
        if kind in {"05", "06", "07"} and fields[1] not in worker_keys:
            raise AEJError(f"Linha {number}: vínculo inexistente no registro 03")

    trailer = rows[-1][2]
    for code, reported in zip(("01", "02", "03", "04", "05", "06", "07", "08"), trailer[1:9]):
        if not reported.isdigit():
            raise AEJError(f"Trailer 99 inválido: contagem do tipo {code}")
        if int(reported) != counts[code]:
            warnings.append(f"Trailer: contagem declarada de {code} não confere")
    if counts["03"] == 0:
        warnings.append("Nenhum trabalhador declarado no registro 03")
    if counts["05"] == 0:
        warnings.append("Nenhuma marcação encontrada no registro 05")
    return {
        "file_type": "AEJ", "schema_version": header[9],
        "period_start": header[6], "period_end": header[7],
        "workers_count": len(worker_rows),
        "workers": worker_rows, "markings_count": counts["05"],
        "record_counts": dict(sorted(counts.items())),
        "validation": "STRUCTURAL_PARTIAL", "warnings": warnings,
    }
