"""Comando CLI para inspecionar arquivos localmente."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .importer import import_bytes

def main() -> None:
    parser = argparse.ArgumentParser(description="DocRisk AI - leitura local (POC)")
    parser.add_argument("file", type=Path, help="PDF, PNG, JPEG ou AEJ")
    args = parser.parse_args()
    result = import_bytes(args.file.name, args.file.read_bytes())
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
