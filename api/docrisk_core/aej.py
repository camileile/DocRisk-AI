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
    period_start, period_end = date.fromisoformat(header[6]), date.fromisoformat(header[7])
    _date(header[8], "datetime", rows[0][0])
    if header[9] != "001":
        warnings.append("Versão do leiaute diferente de 001; compatibilidade não verificada")

    worker_keys: set[str] = set()
    worker_rows: list[dict[str, str]] = []
    schedule_codes: set[str] = set()
    seen_timestamps: set[tuple[str, datetime]] = set()
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
        elif kind == "04":
            if fields[1] in schedule_codes:
                warnings.append(f"Linha {number}: código de horário contratual duplicado ({fields[1]})")
            schedule_codes.add(fields[1])
        elif kind == "05":
            _date(fields[2], "datetime", number)
            stamp = datetime.strptime(fields[2], "%Y-%m-%dT%H:%M:%S%z")
            timestamp_key = (fields[1], stamp)
            if timestamp_key in seen_timestamps:
                warnings.append(f"Linha {number}: horário duplicado para o vínculo {fields[1]}")
            seen_timestamps.add(timestamp_key)
            if not period_start <= stamp.date() <= period_end:
                warnings.append(f"Linha {number}: marcação fora do período AEJ para o vínculo {fields[1]}")
            if fields[4] not in {"E", "S", "D"}:
                raise AEJError(f"Linha {number}: tipo de marcação inválido")
            if fields[6] not in {"O", "I", "P", "X", "T"}:
                raise AEJError(f"Linha {number}: fonte da marcação inválida")
            if fields[4] == "D" or fields[6] == "I":
                if len(fields) <= 8 or not fields[8].strip():
                    warnings.append(f"Linha {number}: motivo ausente em marcação ajustada")
        elif kind == "07":
            _date(fields[3], "date", number)
            compensation_date = date.fromisoformat(fields[3])
            if not period_start <= compensation_date <= period_end:
                warnings.append(f"Linha {number}: ausência/compensação fora do período AEJ para o vínculo {fields[1]}")
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
    horarios_duplicados: set[str] = set()
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
            if fields[1] in horarios:
                horarios_duplicados.add(fields[1])
            else:
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
    period_start = date.fromisoformat(resumo["period_start"])
    period_end = date.fromisoformat(resumo["period_end"])
    for link, pessoa in vinculos.items():
        avisos: list[str] = []
        marks = marcacoes.get(link, [])
        ordered = sorted(marks, key=lambda mark: (datetime.fromisoformat(mark["at"]), mark["line_number"]))
        for warning in resumo["warnings"]:
            if warning.startswith("Marcador de assinatura P7S") or "delimitador final extra" in warning:
                continue
            if f"vínculo {link}" in warning or "vínculo " not in warning:
                avisos.append(f"Aviso estrutural: {warning}")
        if not marks:
            avisos.append("Nenhuma marcação recebida para o vínculo.")

        descartadas: dict[str, list[dict[str, Any]]] = defaultdict(list)
        entradas: list[dict[str, Any]] = []
        saidas: list[dict[str, Any]] = []
        days_to_build: set[str] = set()
        unpaired_lines: set[int] = set()
        for mark in ordered:
            stamp = datetime.fromisoformat(mark["at"])
            mark["day"] = stamp.date().isoformat()
            if not period_start <= stamp.date() <= period_end:
                avisos.append(f"Marcação da linha {mark['line_number']} fora do período AEJ.")
            if mark["type"] == "D":
                avisos.append(f"Marcação desconsiderada na linha {mark['line_number']}.")
                descartadas[mark["day"]].append(mark)
                days_to_build.add(mark["day"])
            elif mark["type"] == "E":
                entradas.append(mark)
            else:
                saidas.append(mark)
            if mark["source"] in {"P", "X"}:
                avisos.append(f"Marcação pré-assinalada ou por exceção na linha {mark['line_number']}; cálculo requer conferência.")
            if mark["source"] == "I":
                avisos.append(f"Marcação incluída manualmente na linha {mark['line_number']}; cálculo requer conferência.")

        # Emparelha cada entrada com a saída posterior mais próxima do mesmo número de par,
        # permitindo a saída no dia seguinte. Cada marcação continua no registro de origem.
        usados_saida: set[int] = set()
        pares: list[dict[str, Any]] = []
        for entrada in entradas:
            start = datetime.fromisoformat(entrada["at"])
            candidates = []
            for saida in saidas:
                if saida["line_number"] in usados_saida or saida["sequence"] != entrada["sequence"]:
                    continue
                end = datetime.fromisoformat(saida["at"])
                minutes = int((end - start).total_seconds() // 60)
                if 0 < minutes <= 24 * 60:
                    has_intervening_entry = any(
                        other["line_number"] != entrada["line_number"]
                        and other["sequence"] == entrada["sequence"]
                        and start < datetime.fromisoformat(other["at"]) < end
                        for other in entradas
                    )
                    if has_intervening_entry:
                        continue
                    candidates.append((minutes, saida))
            if not candidates:
                avisos.append(f"Entrada da linha {entrada['line_number']} sem saída compatível no período de 24 horas.")
                unpaired_lines.add(entrada["line_number"])
                continue
            minutes, saida = min(candidates, key=lambda item: (item[0], item[1]["line_number"]))
            usados_saida.add(saida["line_number"])
            dia = start.date().isoformat()
            days_to_build.add(dia)
            pares.append({"day": dia, "sequence": entrada["sequence"], "entry": entrada, "exit": saida,
                          "start": start, "end": datetime.fromisoformat(saida["at"]), "minutes": minutes})
        for saida in saidas:
            if saida["line_number"] not in usados_saida:
                avisos.append(f"Saída da linha {saida['line_number']} sem entrada compatível.")
                unpaired_lines.add(saida["line_number"])

        duplicadas: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
        for mark in ordered:
            duplicadas[datetime.fromisoformat(mark["at"])].append(mark)
        linhas_duplicadas = {mark["line_number"] for group in duplicadas.values() if len(group) > 1 for mark in group}
        invalid_days: set[str] = set()
        for stamp, group in duplicadas.items():
            if len(group) > 1:
                linhas = ", ".join(str(item["line_number"]) for item in group)
                avisos.append(f"Horário duplicado nas linhas {linhas}; não contabilizado automaticamente.")
                invalid_days.update(item["day"] for item in group)

        # Intervalos sobrepostos não podem ser somados duas vezes.
        pares_ordenados = sorted(pares, key=lambda pair: (pair["start"], pair["end"]))
        for index, first in enumerate(pares_ordenados):
            for second in pares_ordenados[index + 1:]:
                if second["start"] >= first["end"]:
                    break
                if first["start"] < second["end"] and second["start"] < first["end"]:
                    avisos.append(
                        f"Sobreposição entre os pares {first['sequence']} (linha {first['entry']['line_number']}) "
                        f"e {second['sequence']} (linha {second['entry']['line_number']})."
                    )
                    invalid_days.update((first["day"], second["day"]))

        for pair in pares:
            if pair["entry"]["line_number"] in linhas_duplicadas or pair["exit"]["line_number"] in linhas_duplicadas:
                invalid_days.add(pair["day"])
            for mark in (pair["entry"], pair["exit"]):
                stamp_day = datetime.fromisoformat(mark["at"]).date()
                if not period_start <= stamp_day <= period_end:
                    invalid_days.add(pair["day"])
        for mark in ordered:
            if mark["line_number"] in unpaired_lines:
                days_to_build.add(mark["day"])
                invalid_days.add(mark["day"])

        by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for pair in pares:
            by_day[pair["day"]].append(pair)
        dias: list[dict[str, Any]] = []
        total_excedente = 0
        calculavel = True
        for dia in sorted(days_to_build):
            day_pairs = by_day.get(dia, [])
            day_marks = [mark for pair in day_pairs for mark in (pair["entry"], pair["exit"])]
            codes = {mark["schedule_code"] for mark in day_marks if mark["schedule_code"]}
            codigo = next(iter(codes)) if len(codes) == 1 else None
            day_valid = bool(day_pairs) and dia not in invalid_days
            if len(codes) > 1:
                avisos.append(f"Mais de um horário contratual nas marcações da jornada iniciada em {dia}.")
                day_valid = False
            if codigo is None or codigo not in horarios:
                avisos.append(f"Horário contratual não identificado para a jornada iniciada em {dia}.")
                day_valid = False
            elif codigo in horarios_duplicados:
                avisos.append(f"Código de horário contratual {codigo} duplicado; duração ambígua em {dia}.")
                day_valid = False
            contratada = horarios[codigo][0] if codigo in horarios else None
            if contratada is not None and (contratada <= 0 or contratada > 24 * 60):
                avisos.append(f"Duração contratual inválida no registro 04 para {dia}.")
                day_valid = False
            minutos = sum(pair["minutes"] for pair in day_pairs)
            excedente = max(0, minutos - contratada) if day_valid and contratada is not None else None
            if day_valid and excedente is not None:
                total_excedente += excedente
            else:
                calculavel = False
            linha_horario = horarios[codigo][1] if codigo in horarios else None
            excluded = descartadas.get(dia, [])
            source_lines = {mark["line_number"] for mark in day_marks}
            source_lines.update(mark["line_number"] for mark in excluded)
            if linha_horario is not None:
                source_lines.add(linha_horario)
            if any(mark["source"] in {"P", "X", "I"} for mark in day_marks) or excluded:
                day_valid = False
                excedente = None
                calculavel = False
            pair_details = [{"sequence": pair["sequence"], "entrada_line": pair["entry"]["line_number"],
                             "saida_line": pair["exit"]["line_number"], "minutes": pair["minutes"],
                             "crosses_midnight": pair["entry"]["day"] != pair["exit"]["day"]}
                            for pair in day_pairs]
            dias.append({"date": dia, "schedule_code": codigo, "schedule_line": linha_horario,
                         "contract_minutes": contratada, "worked_minutes": minutos if day_valid else None,
                         "observed_daily_excess_minutes": excedente, "pairs": pair_details,
                         "markings": day_marks, "excluded_markings": excluded,
                         "source_lines": sorted(source_lines)})

        if compensacoes.get(link):
            avisos.append("Há registros de ausência/compensação; a conciliação exige revisão humana.")
        for compensation in compensacoes.get(link, []):
            comp_day = date.fromisoformat(compensation["date"])
            if not period_start <= comp_day <= period_end:
                avisos.append(f"Ausência/compensação da linha {compensation['line_number']} fora do período AEJ.")
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
            "method": "Soma do excedente diário observado por jornada iniciada em cada data, permitindo virada de dia; não apura banco semanal nem conclusão legal.",
        }

    return {"summary": resumo, "records": registros, "calculations": calculos}
