"""D4-08 — backup consistente, verificação, restauração e reconciliação (F17/F18).

  python scripts/backup.py backup   --data-dir DATA --out BACKUPS
  python scripts/backup.py verify   BACKUPS/docrisk-AAAAMMDD-HHMMSS
  python scripts/backup.py restore  BACKUPS/docrisk-... --data-dir NOVO
  python scripts/backup.py reconcile --data-dir DATA [--repair]

Consistência: o banco é copiado com a API de backup online do SQLite (snapshot
transacional mesmo com a API ativa). Os arquivos copiados são EXATAMENTE os que
o snapshot referencia — originais (batches.arquivo) e páginas derivadas
(pages.image_path) —, cada um com SHA-256 no manifesto. Arquivos gravados depois
do snapshot não entram (seriam órfãos para esse banco). Originais são verificados
contra batches.sha256; páginas contra pages.sha256.

O banco guarda caminhos absolutos; a restauração os remapeia para o novo
DATA_DIR. A restauração recusa um DATA_DIR com API ativa (trava D4-04) ou com
banco existente, salvo --force.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

MANIFESTO = "manifest.json"
FORMATO = "docrisk-backup/1"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _rel(caminho: str, data_dir: Path) -> str | None:
    try:
        return Path(caminho).resolve().relative_to(data_dir.resolve()).as_posix()
    except ValueError:
        return None


def backup(data_dir: Path, out: Path) -> Path:
    inicio = time.monotonic()
    data_dir = data_dir.resolve()
    origem = data_dir / "docrisk.sqlite"
    if not origem.exists():
        raise SystemExit(f"Banco não encontrado em {origem}")
    destino = out / f"docrisk-{datetime.now():%Y%m%d-%H%M%S}"
    (destino / "files").mkdir(parents=True, exist_ok=False)
    snap = destino / "docrisk.sqlite"
    src = sqlite3.connect(f"file:{origem.as_posix()}?mode=ro", uri=True, timeout=30)
    dst = sqlite3.connect(snap)
    try:
        src.backup(dst)  # snapshot consistente, não bloqueia leitores/escritores por muito tempo
    finally:
        dst.close()
        src.close()

    conn = sqlite3.connect(snap)
    arquivos, problemas = [], []
    try:
        refs = [("original", r[0], r[1], r[2]) for r in conn.execute("SELECT id, arquivo, sha256 FROM batches")]
        refs += [("pagina", r[0], r[1], r[2]) for r in conn.execute("SELECT id, image_path, sha256 FROM pages")]
    finally:
        conn.close()
    for tipo, rid, caminho, sha_db in refs:
        rel = _rel(caminho, data_dir)
        fonte = Path(caminho)
        if rel is None:
            problemas.append(f"{tipo} {rid}: caminho fora do DATA_DIR")
            continue
        if not fonte.is_file():
            problemas.append(f"{tipo} {rid}: ausente no armazenamento ({rel})")
            continue
        alvo = destino / "files" / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fonte, alvo)
        sha = _sha(alvo)
        if sha_db and sha != sha_db:
            problemas.append(f"{tipo} {rid}: hash diverge do banco ({rel})")
        arquivos.append({"tipo": tipo, "id": rid, "rel": rel, "sha256": sha, "bytes": alvo.stat().st_size})
    manifesto = {
        "formato": FORMATO, "criado_em": datetime.now().isoformat(timespec="seconds"),
        "data_dir_origem": str(data_dir), "banco": {"arquivo": "docrisk.sqlite", "sha256": _sha(snap)},
        "contagens": {"lotes": sum(a["tipo"] == "original" for a in arquivos),
                      "paginas": sum(a["tipo"] == "pagina" for a in arquivos)},
        "arquivos": arquivos, "problemas": problemas,
        "segundos": round(time.monotonic() - inicio, 3),
    }
    (destino / MANIFESTO).write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def verify(pasta: Path) -> list[str]:
    m = json.loads((pasta / MANIFESTO).read_text(encoding="utf-8"))
    erros = [] if m.get("formato") == FORMATO else ["formato de backup desconhecido"]
    if _sha(pasta / "docrisk.sqlite") != m["banco"]["sha256"]:
        erros.append("banco: hash diverge do manifesto")
    conn = sqlite3.connect(f"file:{(pasta / 'docrisk.sqlite').as_posix()}?mode=ro", uri=True)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            erros.append("banco: integrity_check falhou")
    finally:
        conn.close()
    for a in m["arquivos"]:
        f = pasta / "files" / a["rel"]
        if not f.is_file():
            erros.append(f"ausente: {a['rel']}")
        elif _sha(f) != a["sha256"]:
            erros.append(f"corrompido: {a['rel']}")
    return erros


def _api_ativa(data_dir: Path) -> bool:
    lock = data_dir / "api.lock"
    if not lock.exists():
        return False
    try:  # mesma trava do D4-04 (msvcrt/fcntl)
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from docrisk_core import runtime
        with lock.open("a+b") as fh:
            if runtime._travar(fh):
                runtime._destravar(fh)
                return False
            return True
    except ImportError:
        return False


def restore(pasta: Path, data_dir: Path, force: bool = False) -> dict:
    inicio = time.monotonic()
    erros = verify(pasta)
    if erros:
        raise SystemExit("Backup inválido, restauração abortada:\n  " + "\n  ".join(erros))
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    if _api_ativa(data_dir):
        raise SystemExit("Há uma API ativa usando este DATA_DIR; encerre-a antes de restaurar.")
    banco = data_dir / "docrisk.sqlite"
    if banco.exists() and not force:
        raise SystemExit(f"{banco} já existe; use --force para substituir (o atual é renomeado).")
    if banco.exists():
        sufixo = datetime.now().strftime("%Y%m%d-%H%M%S")
        for nome in ("docrisk.sqlite", "docrisk.sqlite-wal", "docrisk.sqlite-shm"):
            if (data_dir / nome).exists():
                (data_dir / nome).rename(data_dir / f"{nome}.antes-restauracao-{sufixo}")
    m = json.loads((pasta / MANIFESTO).read_text(encoding="utf-8"))
    for a in m["arquivos"]:
        alvo = data_dir / a["rel"]
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pasta / "files" / a["rel"], alvo)
    shutil.copy2(pasta / "docrisk.sqlite", banco)
    conn = sqlite3.connect(banco)
    try:  # caminhos absolutos -> novo DATA_DIR
        for tabela, coluna in (("batches", "arquivo"), ("pages", "image_path")):
            for rid, caminho in conn.execute(f"SELECT id, {coluna} FROM {tabela}").fetchall():
                rel = _rel(caminho, Path(m["data_dir_origem"]))
                if rel is not None:
                    conn.execute(f"UPDATE {tabela} SET {coluna}=? WHERE id=?", (str(data_dir / rel), rid))
        conn.commit()
    finally:
        conn.close()
    return {"arquivos": len(m["arquivos"]), "segundos": round(time.monotonic() - inicio, 3)}


def reconcile(data_dir: Path, repair: bool = False) -> dict:
    """Banco × armazenamento. Páginas derivadas ausentes/corrompidas são re-renderizadas do
    original (determinístico, conferido pelo hash). Original ausente NÃO é recuperável: só relatado."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from docrisk_core.pipeline.render import iterar_paginas
    data_dir = data_dir.resolve()
    conn = sqlite3.connect(data_dir / "docrisk.sqlite", timeout=30)
    rel = {"originais_ausentes": [], "originais_corrompidos": [], "paginas_ausentes": [],
           "paginas_recuperadas": [], "paginas_irrecuperaveis": [], "lotes_inconsistentes": [], "orfaos": []}
    try:
        lotes = conn.execute("SELECT id, arquivo, sha256, tipo_arquivo, status FROM batches").fetchall()
        referenciados = set()
        for bid, arquivo, sha, tipo, status in lotes:
            referenciados.add(Path(arquivo).resolve())
            original = Path(arquivo)
            ok_original = original.is_file() and _sha(original) == sha
            if not original.is_file():
                rel["originais_ausentes"].append(bid)
            elif not ok_original:
                rel["originais_corrompidos"].append(bid)
            paginas = conn.execute("SELECT id, ordem, image_path, sha256 FROM pages WHERE batch_id=?", (bid,)).fetchall()
            ok_pags = {p[1] for p in conn.execute("SELECT id, ordem FROM pages WHERE batch_id=? AND status='OK'", (bid,))}
            if status == "CONCLUIDO" and tipo != "AEJ" and len(ok_pags) != len(paginas):
                rel["lotes_inconsistentes"].append(bid)
            faltando = []
            for pid, ordem, caminho, psha in paginas:
                referenciados.add(Path(caminho).resolve())
                p = Path(caminho)
                if not p.is_file() or _sha(p) != psha:
                    rel["paginas_ausentes"].append(pid)
                    faltando.append((pid, ordem, p, psha))
            if faltando and repair:
                if not ok_original:
                    rel["paginas_irrecuperaveis"] += [f[0] for f in faltando]
                    continue
                por_ordem = {f[1]: f for f in faltando}
                for pag in iterar_paginas(original.read_bytes(), tipo):
                    if pag.ordem in por_ordem:
                        pid, _, destino, psha = por_ordem[pag.ordem]
                        if hashlib.sha256(pag.png).hexdigest() == psha:
                            destino.parent.mkdir(parents=True, exist_ok=True)
                            destino.write_bytes(pag.png)
                            rel["paginas_recuperadas"].append(pid)
                        else:
                            rel["paginas_irrecuperaveis"].append(pid)
        for pasta in ("uploads", "pages"):
            for f in (data_dir / pasta).rglob("*") if (data_dir / pasta).exists() else []:
                if f.is_file() and f.resolve() not in referenciados:
                    rel["orfaos"].append(f.relative_to(data_dir).as_posix())
    finally:
        conn.close()
    return rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup"); b.add_argument("--data-dir", required=True, type=Path); b.add_argument("--out", required=True, type=Path)
    v = sub.add_parser("verify"); v.add_argument("pasta", type=Path)
    r = sub.add_parser("restore"); r.add_argument("pasta", type=Path); r.add_argument("--data-dir", required=True, type=Path)
    r.add_argument("--force", action="store_true")
    c = sub.add_parser("reconcile"); c.add_argument("--data-dir", required=True, type=Path); c.add_argument("--repair", action="store_true")
    a = ap.parse_args()
    if a.cmd == "backup":
        pasta = backup(a.data_dir, a.out)
        m = json.loads((pasta / MANIFESTO).read_text(encoding="utf-8"))
        print(json.dumps({"backup": str(pasta), **m["contagens"], "problemas": m["problemas"], "segundos": m["segundos"]}, ensure_ascii=False))
        return 1 if m["problemas"] else 0
    if a.cmd == "verify":
        erros = verify(a.pasta)
        print(json.dumps({"ok": not erros, "erros": erros}, ensure_ascii=False))
        return 1 if erros else 0
    if a.cmd == "restore":
        print(json.dumps(restore(a.pasta, a.data_dir, a.force), ensure_ascii=False))
        return 0
    rel = reconcile(a.data_dir, a.repair)
    print(json.dumps(rel, ensure_ascii=False))
    pendente = rel["originais_ausentes"] or rel["originais_corrompidos"] or rel["paginas_irrecuperaveis"] or \
        rel["lotes_inconsistentes"] or (set(rel["paginas_ausentes"]) - set(rel["paginas_recuperadas"]))
    return 1 if pendente else 0


if __name__ == "__main__":
    sys.exit(main())
