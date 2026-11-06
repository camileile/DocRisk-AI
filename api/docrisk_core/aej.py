"""Parser estrutural AEJ e estimador de excedente diario.
A estimativa nao valida P7S, nao apura banco de horas semanal nem conclui juridicamente horas extras.
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
    if date.fromisoformat(header[6]) > date.fromisoformat(header[7]):
        raise AEJError(f"Linha {rows[0][0]}: período do AEJ invertido")
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


def parse_aej_detalhado(content: bytes) -> dict[str, Any]:
    """Valida e devolve os registros com rastreabilidade para uso interno do pipeline.

    `parse_aej` continua sendo a interface de inspeção sem dados pessoais. Esta função
    preserva as linhas exatas (além do arquivo original) e cria uma estimativa diária
    explícita, sem chamar o resultado de apuração legal de horas extras.
    """
    resumo = parse_aej(content)
    text = content.decode("iso-8859-1")
    registros: list[dict[str, Any]] = []
    horarios: dict[str, tuple[int, int]] = {}
    vinculos: dict[str, dict[str, Any]] = {}
    marcacoes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    compensacoes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for numero, linha in enumerate(text.splitlines(), start=1):
        if linha.startswith("ASSINATURA_DIGITAL_EM_ARQUIVO_P7S"):
            registros.append({"line_number": numero, "record_type": "P7S_MARKER", "worker_link_id": None,
                              "raw_line": linha, "fields": [linha]})
            continue
        fields = linha.split("|")
        if fields and fields[-1] == "":
            fields.pop()
        kind = fields[0]
        link = fields[1] if kind in {"03", "05", "06", "07"} and len(fields) > 1 else None
        record = {"line_number": numero, "record_type": kind, "worker_link_id": link,
                  "raw_line": linha, "fields": fields}
        registros.append(record)
        if kind == "03":
            vinculos[fields[1]] = {"line_number": numero, "name": fields[3] if len(fields) > 3 else ""}
        elif kind == "04":
            try:
                duration = int(fields[2])
            except (ValueError, IndexError):
                duration = 0
            horarios[fields[1]] = (duration, numero)
        elif kind == "05":
            mark_time = datetime.strptime(fields[2], "%Y-%m-%dT%H:%M:%S%z")
            mark = {"line_number": numero, "at": mark_time.isoformat(), "type": fields[4],
                    "sequence": fields[5], "source": fields[6],
                    "schedule_code": fields[7] if len(fields) > 7 else "",
                    "reason": fields[8] if len(fields) > 8 else ""}
            marcacoes[fields[1]].append(mark)
        elif kind == "07":
            compensacoes[fields[1]].append({"line_number": numero, "type": fields[2],
                                             "date": fields[3],
                                             "minutes": fields[4] if len(fields) > 4 else ""})

    calculos: dict[str, dict[str, Any]] = {}
    for link, pessoa in vinculos.items():
        por_dia: dict[str, list[dict[str, Any]]] = defaultdict(list)
        descartadas: dict[str, list[dict[str, Any]]] = defaultdict(list)
        avisos: list[str] = []
        for warning in resumo["warnings"]:
            if (not warning.startswith("Marcador de assinatura P7S") and
                    "delimitador final extra" not in warning):
                avisos.append(f"Aviso estrutural: {warning}")
        if not marcacoes.get(link):
            avisos.append("Nenhuma marcação recebida para o vínculo.")
        for marca in marcacoes.get(link, []):
            stamp = datetime.fromisoformat(marca["at"])
            marca["day"] = stamp.date().isoformat()
            if marca["type"] == "D":
                avisos.append(f"Marcação desconsiderada na linha {marca['line_number']}.")
                descartadas[marca["day"]].append(marca)
                continue
            por_dia[marca["day"]].append(marca)

        dias: list[dict[str, Any]] = []
        total_excedente = 0
        calculavel = True
        for dia, marks in sorted(por_dia.items()):
            codigos = {m["schedule_code"] for m in marks if m["schedule_code"]}
            codigo = next(iter(codigos)) if len(codigos) == 1 else None
            if len(codigos) > 1:
                avisos.append(f"Mais de um horário contratual nas marcações de {dia}.")
            if any(m["source"] in {"P", "X"} for m in marks):
                avisos.append(f"Marcação pré-assinalada ou por exceção em {dia}; cálculo requer conferência.")
            if any(m["source"] == "I" for m in marks):
                avisos.append(f"Há marcação incluída manualmente em {dia}; cálculo requer conferência.")

            pares: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for mark in marks:
                pares[mark["sequence"]].append(mark)
            minutos = 0
            linhas_pares: list[dict[str, Any]] = []
            dia_valido = codigo is not None and codigo in horarios
            if codigo is None or codigo not in horarios:
                avisos.append(f"Horário contratual não identificado para {dia}.")
                dia_valido = False
            elif horarios[codigo][0] <= 0 or horarios[codigo][0] > 24 * 60:
                avisos.append(f"Duração contratual inválida no registro 04 para {dia}.")
                dia_valido = False
            for seq, par in sorted(pares.items()):
                entradas = [m for m in par if m["type"] == "E"]
                saidas = [m for m in par if m["type"] == "S"]
                if len(entradas) != 1 or len(saidas) != 1 or len(par) != 2:
                    avisos.append(f"Par de marcações {seq} incompleto ou ambíguo em {dia}.")
                    dia_valido = False
                    continue
                entrada = datetime.fromisoformat(entradas[0]["at"])
                saida = datetime.fromisoformat(saidas[0]["at"])
                duracao = int((saida - entrada).total_seconds() // 60)
                if duracao <= 0 or duracao > 24 * 60:
                    avisos.append(f"Duração inválida no par {seq} de {dia}.")
                    dia_valido = False
                    continue
                minutos += duracao
                linhas_pares.append({"sequence": seq, "entrada_line": entradas[0]["line_number"],
                                     "saida_line": saidas[0]["line_number"], "minutes": duracao})

            contratada = horarios[codigo][0] if codigo in horarios else None
            excedente = max(0, minutos - contratada) if dia_valido and contratada is not None else None
            if not dia_valido:
                calculavel = False
            elif excedente is not None:
                total_excedente += excedente
            linha_horario = horarios[codigo][1] if codigo in horarios else None
            linhas_origem = {m["line_number"] for m in marks}
            linhas_origem.update(m["line_number"] for m in descartadas.get(dia, []))
            if linha_horario is not None:
                linhas_origem.add(linha_horario)
            dias.append({"date": dia, "schedule_code": codigo, "schedule_line": linha_horario,
                         "contract_minutes": contratada,
                         "worked_minutes": minutos if dia_valido else None,
                         "observed_daily_excess_minutes": excedente, "pairs": linhas_pares,
                         "markings": marks, "excluded_markings": descartadas.get(dia, []),
                         "source_lines": sorted(linhas_origem)})

        if compensacoes.get(link):
            avisos.append("Há registros de ausência/compensação; a conciliação exige revisão humana.")
        if avisos:
            calculavel = False
        calculos[link] = {
            "worker_link_id": link,
            "worker_record_line": pessoa["line_number"], "days": dias,
            "observed_daily_excess_minutes": total_excedente if calculavel else None,
            "observed_daily_excess_hours": round(total_excedente / 60, 2) if calculavel else None,
            "calculation_status": "CALCULATED" if calculavel else "REVIEW_REQUIRED",
            "warnings": list(dict.fromkeys(avisos)),
            "validation_warnings": resumo["warnings"],
            "compensations": compensacoes.get(link, []),
            "method": "Soma do excedente diário observado sobre durJornada; não apura banco semanal nem conclusão legal.",
        }

    return {"summary": resumo, "records": registros, "calculations": calculos}
