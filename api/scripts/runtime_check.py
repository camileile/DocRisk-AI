"""D4-04 — verificação do ambiente conectado local com PROCESSOS REAIS.

Sobe a API (uvicorn) em portas livres e DATA_DIR temporário, com o leitor offline
(AI_PROVIDER=textlayer: não é IA e não chama serviços externos), e mede:

  C01 configuração inválida recusada com mensagem clara
  C02 DATA_DIR inutilizável recusado
  C03 banco corrompido recusado (arquivo preservado)
  C04 inicialização limpa (tempo até /health)
  C05 segunda instância no mesmo DATA_DIR recusada
  C06 CORS permitido / negado
  C07 job sintético ponta a ponta (lote_demo.pdf -> CONCLUIDO)
  C08 queda abrupta durante processamento (kill) + reinício + retomada sem duplicidade
  C09 encerramento controlado (sinal) com liberação da trava
  C10 reinicialização sobre o mesmo DATA_DIR preserva dados

Uso:  python scripts/runtime_check.py [--json saida.json]
Nada aqui usa a chave do Gemini: o ambiente do filho é montado sem GEMINI_*.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

API_DIR = Path(__file__).resolve().parent.parent
LOTE = API_DIR / "scripts" / "lote_demo" / "lote_demo.pdf"
ORIGEM_OK = "http://127.0.0.1:4173"
resultados: list[dict] = []


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def env_filho(data_dir: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GEMINI", "DOCRISK", "CORS", "AI_"))}
    env.update({
        "AI_PROVIDER": "textlayer", "GEMINI_API_KEY": "", "DOCRISK_DATA_DIR": str(data_dir),
        "DOCRISK_DEMO_MODE": "1", "DOCRISK_SYNC": "0", "CORS_ORIGINS": ORIGEM_OK,
        "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
    })
    env.update(extra)
    return env


def subir(data_dir: Path, porta: int, log: Path, **extra: str) -> subprocess.Popen:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "docrisk_core.api:app", "--host", "127.0.0.1", "--port", str(porta)],
        cwd=API_DIR, env=env_filho(data_dir, **extra), stdout=log.open("wb"), stderr=subprocess.STDOUT,
        creationflags=flags)


def esperar_saude(porta: int, proc: subprocess.Popen, limite: float = 40) -> float | None:
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        if proc.poll() is not None:
            return None
        try:
            if httpx.get(f"http://127.0.0.1:{porta}/health", timeout=1).status_code == 200:
                return time.monotonic() - inicio
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    return None


def esperar_saida(proc: subprocess.Popen, limite: float = 30) -> int | None:
    try:
        return proc.wait(limite)
    except subprocess.TimeoutExpired:
        return None


def matar(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.kill()  # TerminateProcess / SIGKILL: simula queda abrupta
        proc.wait(10)


def encerrar(proc: subprocess.Popen) -> int | None:
    if proc.poll() is not None:
        return proc.returncode
    proc.send_signal(signal.CTRL_BREAK_EVENT if sys.platform == "win32" else signal.SIGTERM)
    return esperar_saida(proc, 20)


def registrar(cid: str, nome: str, ok: bool, **dados) -> None:
    resultados.append({"id": cid, "cenario": nome, "ok": ok, **dados})
    detalhe = ", ".join(f"{k}={v}" for k, v in dados.items())
    print(f"{'OK  ' if ok else 'FAIL'} {cid} {nome} {detalhe}", flush=True)


def ler_log(log: Path) -> str:
    return log.read_text(encoding="utf-8", errors="replace")


def recusa(cid: str, nome: str, base: Path, esperado: str, data_dir: Path | None = None, **extra) -> None:
    log = base / f"{cid}.log"
    inicio = time.monotonic()
    proc = subir(data_dir or base / f"{cid}-data", porta_livre(), log, **extra)
    codigo = esperar_saida(proc, 30)
    if codigo is None:
        matar(proc)
    texto = ler_log(log)
    registrar(cid, nome, codigo not in (None, 0) and esperado in texto,
              saida=codigo, segundos=round(time.monotonic() - inicio, 2), mensagem_encontrada=esperado in texto)


def token(porta: int, uid: str) -> dict[str, str]:
    users = httpx.get(f"http://127.0.0.1:{porta}/api/demo/users", timeout=10).json()
    return {"Authorization": "Bearer " + next(u["token"] for u in users if u["id"] == uid)}


def enviar_lote(porta: int, h: dict) -> int:
    r = httpx.post(f"http://127.0.0.1:{porta}/api/supplier/batches", headers=h, timeout=60,
                   data={"contract_id": "CT-001"},
                   files={"file": ("lote_demo.pdf", LOTE.read_bytes(), "application/pdf")})
    assert r.status_code == 202, r.text
    return int(r.json()["batch_id"])


def esperar_lote(porta: int, h: dict, batch: int, limite: float = 120) -> tuple[str, float]:
    inicio = time.monotonic()
    status = "?"
    while time.monotonic() - inicio < limite:
        status = httpx.get(f"http://127.0.0.1:{porta}/api/batches/{batch}", headers=h, timeout=10).json()["status"]
        if status in {"CONCLUIDO", "FALHA_PROCESSAMENTO"}:
            break
        time.sleep(0.25)
    return status, time.monotonic() - inicio


def consulta(data_dir: Path, sql: str, *args):
    conn = sqlite3.connect(data_dir / "docrisk.sqlite")
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    base = Path(tempfile.mkdtemp(prefix="docrisk-d4-04-"))
    print(f"diretório de trabalho: {base}\n", flush=True)

    recusa("C01", "configuração inválida recusada", base, "AI_PROVIDER='xyz' inválido", AI_PROVIDER="xyz")
    arquivo = base / "data-e-arquivo"
    arquivo.write_text("x")
    recusa("C02", "DATA_DIR inutilizável recusado", base, "DOCRISK_DATA_DIR", data_dir=arquivo)
    corrompido = base / "C03-data"
    corrompido.mkdir()
    (corrompido / "docrisk.sqlite").write_bytes(b"corrompido" * 500)
    recusa("C03", "banco corrompido recusado", base, "ilegível", data_dir=corrompido)
    registrar("C03b", "banco corrompido preservado", (corrompido / "docrisk.sqlite").read_bytes().startswith(b"corrompido"))

    data = base / "data"
    porta = porta_livre()
    t0 = time.monotonic()
    api = subir(data, porta, base / "api-1.log")
    t_saude = esperar_saude(porta, api)
    registrar("C04", "inicialização limpa", t_saude is not None, segundos_ate_health=round(t_saude or -1, 2))
    if t_saude is None:
        print(ler_log(base / "api-1.log"))
        return 1

    dup = subir(data, porta_livre(), base / "api-dup.log")
    codigo = esperar_saida(dup, 30)
    if codigo is None:
        matar(dup)
    registrar("C05", "segunda instância recusada", codigo not in (None, 0) and
              "Já existe uma instância da API" in ler_log(base / "api-dup.log"), saida=codigo)

    pre = {"Access-Control-Request-Method": "GET"}
    ok = httpx.options(f"http://127.0.0.1:{porta}/api/me", headers={"Origin": ORIGEM_OK, **pre})
    neg = httpx.options(f"http://127.0.0.1:{porta}/api/me", headers={"Origin": "https://atacante.example", **pre})
    registrar("C06", "CORS permitido e negado",
              ok.headers.get("access-control-allow-origin") == ORIGEM_OK and neg.status_code == 400
              and "access-control-allow-origin" not in neg.headers, permitido=ok.status_code, negado=neg.status_code)

    h = token(porta, "u-oper-beta")
    t = time.monotonic()
    b1 = enviar_lote(porta, h)
    status, dur = esperar_lote(porta, h, b1)
    docs_b1 = consulta(data, "SELECT COUNT(*) FROM documents WHERE batch_id=?", b1)[0][0]
    registrar("C07", "job sintético ponta a ponta", status == "CONCLUIDO" and docs_b1 > 0,
              lote=b1, status=status, segundos=round(dur, 2), documentos=docs_b1,
              upload_ate_concluido=round(time.monotonic() - t, 2))

    b2 = enviar_lote(porta, h)
    time.sleep(0.3)
    matar(api)
    estado = consulta(data, "SELECT status FROM batches WHERE id=?", b2)[0][0]
    paginas_ok = consulta(data, "SELECT COUNT(*) FROM pages WHERE batch_id=? AND status='OK'", b2)[0][0]
    t_rein = time.monotonic()
    api = subir(data, porta, base / "api-2.log")
    t_saude2 = esperar_saude(porta, api)
    status2, dur2 = esperar_lote(porta, h, b2) if t_saude2 else ("SEM_API", 0)
    docs_b2 = consulta(data, "SELECT COUNT(*) FROM documents WHERE batch_id=?", b2)[0][0]
    pags_b2 = consulta(data, "SELECT COUNT(*), COUNT(DISTINCT ordem) FROM pages WHERE batch_id=?", b2)[0]
    registrar("C08", "queda abrupta + retomada sem duplicidade",
              status2 == "CONCLUIDO" and docs_b2 == docs_b1 and pags_b2[0] == pags_b2[1],
              estado_ao_matar=estado, paginas_ok_ao_matar=paginas_ok, status_final=status2,
              documentos=docs_b2, paginas=pags_b2[0], paginas_distintas=pags_b2[1],
              segundos_reinicio_ate_concluido=round(time.monotonic() - t_rein, 2))

    codigo = encerrar(api)
    texto = ler_log(base / "api-2.log")
    limpo = "Application shutdown complete" in texto
    registrar("C09", "encerramento controlado", codigo is not None and limpo, saida=codigo, shutdown_limpo=limpo)
    if api.poll() is None:
        matar(api)

    api = subir(data, porta, base / "api-3.log")
    t_saude3 = esperar_saude(porta, api)
    lotes = consulta(data, "SELECT COUNT(*) FROM batches WHERE status='CONCLUIDO'")[0][0]
    registrar("C10", "reinicialização preserva dados", t_saude3 is not None and lotes == 2,
              segundos_ate_health=round(t_saude3 or -1, 2), lotes_concluidos=lotes)
    encerrar(api)
    if api.poll() is None:
        matar(api)

    falhas = [r for r in resultados if not r["ok"]]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} verificações OK")
    if args.json:
        Path(args.json).write_text(json.dumps({"python": sys.version.split()[0], "plataforma": sys.platform,
                                               "resultados": resultados}, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
