from docrisk_core.aej import parse_aej_detalhado


def aej_with_marks(marks, *, start="2026-10-01", end="2026-10-31", schedules=None, compensations=()):
    schedules = schedules or ["04|J08|480|0800|1200|1300|1700"]
    rows = [
        f"01|1|12345678000190|||Empresa Demonstrativa|{start}|{end}|2026-11-02T08:00:00-0300|001",
        "02|1|3|12345678901234567",
        "03|1|00000000000|Pessoa Teste",
        *schedules,
        *marks,
        *compensations,
        "08|Programa Teste|1.0|1|12345678000190|Desenvolvedora Teste|teste@example.invalid",
    ]
    kinds = ("01", "02", "03", "04", "05", "06", "07", "08")
    counts = {kind: sum(line.startswith(kind + "|") for line in rows) for kind in kinds}
    rows.append("99|" + "|".join(str(counts[kind]) for kind in kinds))
    return ("\r\n".join(rows) + "\r\n").encode("iso-8859-1")


def mark(timestamp, kind, sequence, schedule_code=""):
    return f"05|1|{timestamp}|1|{kind}|{sequence}|O|{schedule_code}|"


def test_overnight_pair_is_calculated_on_start_date():
    data = aej_with_marks([
        mark("2026-10-01T22:00:00-0300", "E", "1", "J08"),
        mark("2026-10-02T06:00:00-0300", "S", "1"),
    ])
    result = parse_aej_detalhado(data)["calculations"]["1"]

    assert result["calculation_status"] == "CALCULATED"
    assert len(result["days"]) == 1 and result["days"][0]["date"] == "2026-10-01"
    assert result["days"][0]["worked_minutes"] == 480
    assert result["days"][0]["pairs"][0]["crosses_midnight"] is True
    assert result["days"][0]["source_lines"] == [4, 5, 6]


def test_overlapping_intervals_require_review():
    data = aej_with_marks([
        mark("2026-10-01T08:00:00-0300", "E", "1", "J08"),
        mark("2026-10-01T11:00:00-0300", "E", "2"),
        mark("2026-10-01T12:00:00-0300", "S", "1"),
        mark("2026-10-01T15:00:00-0300", "S", "2"),
    ])
    result = parse_aej_detalhado(data)["calculations"]["1"]

    assert result["calculation_status"] == "REVIEW_REQUIRED"
    assert result["observed_daily_excess_minutes"] is None
    assert any("Sobreposição" in warning for warning in result["warnings"])


def test_duplicate_marking_time_is_not_counted_automatically():
    data = aej_with_marks([
        mark("2026-10-01T08:00:00-0300", "E", "1", "J08"),
        mark("2026-10-01T08:00:00-0300", "E", "2"),
        mark("2026-10-01T12:00:00-0300", "S", "1"),
        mark("2026-10-01T16:00:00-0300", "S", "2"),
    ])
    result = parse_aej_detalhado(data)["calculations"]["1"]

    assert result["calculation_status"] == "REVIEW_REQUIRED"
    assert any("Horário duplicado" in warning for warning in result["warnings"])


def test_markings_outside_header_period_require_review_and_are_preserved():
    data = aej_with_marks([
        mark("2026-09-30T22:00:00-0300", "E", "1", "J08"),
        mark("2026-10-01T06:00:00-0300", "S", "1"),
    ], start="2026-10-01")
    result = parse_aej_detalhado(data)
    calculation = result["calculations"]["1"]

    assert calculation["calculation_status"] == "REVIEW_REQUIRED"
    assert any("fora do período" in warning for warning in calculation["warnings"])
    preserved_marks = [record for record in result["records"] if record["record_type"] == "05"]
    assert len(preserved_marks) == 2
    assert preserved_marks[0]["raw_line"].startswith("05|1|2026-09-30")


def test_compensation_outside_header_period_requires_review_and_is_preserved():
    data = aej_with_marks(
        [
            mark("2026-10-01T08:00:00-0300", "E", "1", "J08"),
            mark("2026-10-01T12:00:00-0300", "S", "1"),
            mark("2026-10-01T13:00:00-0300", "E", "2"),
            mark("2026-10-01T17:00:00-0300", "S", "2"),
        ],
        compensations=["07|1|3|2026-11-01|60|1|"],
    )
    result = parse_aej_detalhado(data)
    calculation = result["calculations"]["1"]

    assert calculation["calculation_status"] == "REVIEW_REQUIRED"
    assert any("compensação" in warning and "fora do período" in warning
               for warning in calculation["warnings"])
    [record] = [record for record in result["records"] if record["record_type"] == "07"]
    assert record["raw_line"].startswith("07|1|3|2026-11-01")


def test_duplicate_schedule_definition_is_explicitly_ambiguous():
    data = aej_with_marks(
        [
            mark("2026-10-01T08:00:00-0300", "E", "1", "J08"),
            mark("2026-10-01T16:00:00-0300", "S", "1"),
        ],
        schedules=["04|J08|480|0800|1200|1300|1700", "04|J08|420|0900|1200|1300|1700"],
    )
    result = parse_aej_detalhado(data)["calculations"]["1"]

    assert result["calculation_status"] == "REVIEW_REQUIRED"
    assert any("horário contratual duplicado" in warning for warning in result["warnings"])
