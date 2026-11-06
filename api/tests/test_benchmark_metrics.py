from docrisk_core.benchmark_metrics import calcular_metricas


def test_metrics_report_perfect_classification_fields_and_review():
    gold = [{
        "pages": [1], "tipo": "HOLERITE", "trabalhador_id": "T001", "status_esperado": "APTO",
        "campos_esperados": {"horas_extras_h": 8.0, "horas_extras_valor": 160.0},
    }]
    predicted = [{
        "pages": [1], "tipo": "HOLERITE", "trabalhador_id": "T001", "status": "APTO",
        "campos": {"horas_extras_h": 8.0, "horas_extras_valor": 160.0},
    }]

    metrics = calcular_metricas(gold, predicted)

    assert metrics["boundaries"]["precision"] == metrics["boundaries"]["recall"] == 1
    assert metrics["types"]["HOLERITE"]["precision"] == metrics["types"]["HOLERITE"]["recall"] == 1
    assert metrics["association"]["precision"] == metrics["association"]["recall"] == 1
    assert metrics["fields"]["horas_extras_h"]["mae"] == 0
    assert metrics["review"]["rate"] == metrics["review"]["false_alert_rate"] == 0


def test_metrics_count_missing_extractions_false_alerts_and_wrong_association():
    gold = [
        {"pages": [1], "tipo": "HOLERITE", "trabalhador_id": "T001", "status_esperado": "APTO",
         "campos_esperados": {"horas_extras_h": 8.0}},
        {"pages": [2], "tipo": "HOLERITE", "trabalhador_id": "T002", "status_esperado": "PENDENTE_CORRECAO",
         "campos_esperados": {"horas_extras_h": 6.0}},
    ]
    predicted = [
        {"pages": [1], "tipo": "HOLERITE", "trabalhador_id": "T003", "status": "REVISAO_HUMANA",
         "campos": {"horas_extras_h": 10.0}},
        {"pages": [2], "tipo": "HOLERITE", "trabalhador_id": None, "status": "APTO", "campos": {}},
    ]

    metrics = calcular_metricas(gold, predicted)

    assert metrics["association"]["tp"] == 0
    assert metrics["association"]["fp"] == 1 and metrics["association"]["fn"] == 2
    assert metrics["fields"]["horas_extras_h"]["fp"] == 1
    assert metrics["fields"]["horas_extras_h"]["fn"] == 2
    assert metrics["fields"]["horas_extras_h"]["mae"] == 2
    assert metrics["review"]["fp"] == metrics["review"]["fn"] == 1
    assert metrics["review"]["false_negatives"] == 1
    assert metrics["review"]["rate"] == 0.5
    assert metrics["review"]["false_alert_rate"] == 1


def test_boundary_metrics_include_extra_and_missing_segments():
    gold = [{"pages": [1, 2], "tipo": "ESPELHO_PONTO", "trabalhador_id": "T001",
             "status_esperado": "APTO", "campos_esperados": {}}]
    predicted = [
        {"pages": [1], "tipo": "ESPELHO_PONTO", "trabalhador_id": "T001", "status": "APTO", "campos": {}},
        {"pages": [2], "tipo": "DESCONHECIDO", "trabalhador_id": None, "status": "REVISAO_HUMANA", "campos": {}},
    ]

    metrics = calcular_metricas(gold, predicted)

    assert metrics["boundaries"]["precision"] == metrics["boundaries"]["recall"] == 0
    assert metrics["boundaries"]["fp"] == 2 and metrics["boundaries"]["fn"] == 1
    assert metrics["types"]["ESPELHO_PONTO"]["tp"] == 1
    assert metrics["types"]["DESCONHECIDO"]["fp"] == 1


def test_numeric_field_metrics_apply_tolerance_and_count_missing_and_extra_values():
    gold = [
        {"pages": [1], "tipo": "HOLERITE", "campos_esperados": {"horas_extras_h": 10.0}},
        {"pages": [2], "tipo": "HOLERITE", "campos_esperados": {"horas_extras_h": 20.0}},
        {"pages": [3], "tipo": "HOLERITE", "campos_esperados": {"horas_extras_h": 30.0}},
    ]
    predicted = [
        {"pages": [1], "tipo": "HOLERITE", "campos": {"horas_extras_h": 10.005}},
        {"pages": [2], "tipo": "HOLERITE", "campos": {"horas_extras_h": 20.02}},
        {"pages": [4], "tipo": "HOLERITE", "campos": {"horas_extras_h": 40.0}},
    ]

    field = calcular_metricas(gold, predicted)["fields"]["horas_extras_h"]

    assert field["tolerance"] == 0.01
    assert field["tp"] == 1 and field["fp"] == 2 and field["fn"] == 2
    assert field["precision"] == 1 / 3
    assert field["recall"] == 1 / 3
    assert abs(field["mae"] - 0.0125) < 1e-9
