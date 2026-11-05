import pytest
from docrisk_core.aej import parse_aej, AEJError
from docrisk_core.importer import import_bytes

def example_aej() -> bytes:
    # Um único vínculo fictício para TESTE UNITÁRIO, não a base de 100 pessoas.
    rows = [
        "01|1|12345678000190|||Empresa Demonstrativa|2026-10-01|2026-10-31|2026-11-02T08:00:00-0300|001",
        "02|1|3|12345678901234567",
        "03|1|00000000000|Pessoa Teste",
        "04|J08|480|0800|1200|1300|1700",
        "05|1|2026-10-01T08:00:00-0300|1|E|1|O|J08|",
        "05|1|2026-10-01T12:00:00-0300|1|S|1|O||",
        "05|1|2026-10-01T13:00:00-0300|1|E|2|O||",
        "05|1|2026-10-01T17:00:00-0300|1|S|2|O||",
        "06|1|MAT-TESTE-1",
        "07|1|3|2026-10-01|30|1",
        "08|Programa Teste|1.0|1|12345678000190|Desenvolvedora Teste|teste@example.invalid",
        "99|1|1|1|1|4|1|1|1",
        "ASSINATURA_DIGITAL_EM_ARQUIVO_P7S" + " " * (100-len("ASSINATURA_DIGITAL_EM_ARQUIVO_P7S"))
    ]
    return ("\r\n".join(rows) + "\r\n").encode("iso-8859-1")

def test_aej_summary_and_privacy():
    result = import_bytes("jornada.aej", example_aej())
    assert result["workers_count"] == 1
    assert result["markings_count"] == 4
    assert result["file_type"] == "AEJ"
    assert "Pessoa Teste" not in str(result)
    assert "00000000000" not in str(result)
    assert result["period_start"] == "2026-10-01"

def test_rejects_invalid_link():
    data = example_aej().replace(b"05|1|", b"05|8|")
    with pytest.raises(AEJError, match="vínculo inexistente"):
        parse_aej(data)

def test_rejects_invalid_timestamp():
    data = example_aej().replace(b"2026-10-01T08:00:00-0300", b"2026-77-01T08:00:00-0300")
    with pytest.raises(AEJError, match="data inválida"):
        parse_aej(data)
