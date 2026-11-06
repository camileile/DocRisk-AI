from docrisk_core.rules.comprovantes import (
    EstadoComprovante,
    calcular_metricas_comprovante,
    classificar_comprovante,
)


def test_comprovante_received_is_not_counted_as_reviewed():
    assert classificar_comprovante([{"id": 1, "status": "APTO", "versao": 1}]) == EstadoComprovante.RECEBIDO
    assert classificar_comprovante([{"id": 1, "status": "APTO", "revisado_por": "analista"}]) == EstadoComprovante.CONFERIDO


def test_comprovante_states_use_only_the_current_version():
    documents = [
        {"id": 10, "status": "SUBSTITUIDO", "versao": 1, "revisado_por": "analista"},
        {"id": 11, "status": "REVISAO_HUMANA", "versao": 2},
    ]
    assert classificar_comprovante(documents) == EstadoComprovante.EM_REVISAO
    assert classificar_comprovante([{"id": 12, "status": "PENDENTE_CORRECAO"}]) == EstadoComprovante.INSUFICIENTE
    assert classificar_comprovante([{"id": 13, "status": "REJEITADO"}]) == EstadoComprovante.REJEITADO
    assert classificar_comprovante([]) == EstadoComprovante.NAO_RECEBIDO


def test_comprovante_metrics_exclude_non_applicable_and_keep_denominators_explicit():
    result = calcular_metricas_comprovante([
        {"exigivel": True, "documentos": [{"id": 1, "status": "APTO"}]},
        {"exigivel": True, "documentos": [{"id": 2, "status": "APTO", "revisado_por": "a"}]},
        {"exigivel": True, "documentos": [{"id": 3, "status": "PENDENTE_CORRECAO"}], "reenvios": 2},
        {"exigivel": True, "documentos": [{"id": 4, "status": "REJEITADO"}]},
        {"exigivel": False, "documentos": []},
    ])

    assert result["populacao_exigivel"] == 4
    assert result["por_estado"] == {
        "NAO_RECEBIDO": 0,
        "RECEBIDO": 1,
        "EM_REVISAO": 0,
        "CONFERIDO": 1,
        "INSUFICIENTE": 1,
        "REJEITADO": 1,
    }
    assert result["taxa_recebimento"] == 0.75
    assert result["taxa_conferencia"] == 0.25
    assert result["taxa_insuficiencia"] == 0.3333
    assert result["pendencias"] == 3
    assert result["reenvios"] == 2


def test_comprovante_metrics_return_null_rates_for_zero_denominators():
    result = calcular_metricas_comprovante([])
    assert result["populacao_exigivel"] == 0
    assert result["taxa_recebimento"] is None
    assert result["taxa_conferencia"] is None
    assert result["taxa_insuficiencia"] is None
    assert result["pendencias"] == 0
