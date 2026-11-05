"""Configuração por variáveis de ambiente (api/.env). Dono: frente 1."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(API_DIR / ".env")


def _bool(nome: str, padrao: str = "0") -> bool:
    return os.getenv(nome, padrao).strip() == "1"


DEMO_MODE = _bool("DOCRISK_DEMO_MODE")
DATA_DIR = Path(os.getenv("DOCRISK_DATA_DIR", str(API_DIR / "data"))).resolve()
DB_PATH = DATA_DIR / "docrisk.sqlite"
UPLOAD_DIR = DATA_DIR / "uploads"
PAGES_DIR = DATA_DIR / "pages"

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_RPM = int(os.getenv("GEMINI_RPM", "8"))

LIMIAR_CONFIANCA = float(os.getenv("LIMIAR_CONFIANCA", "0.75"))
LIMIAR_LEGIBILIDADE = float(os.getenv("LIMIAR_LEGIBILIDADE", "0.5"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_PAGINAS = int(os.getenv("MAX_PAGINAS", "300"))
RENDER_DPI = int(os.getenv("RENDER_DPI", "150"))
MAX_LADO_PX = int(os.getenv("MAX_LADO_PX", "2200"))

#: Processa o lote na própria requisição (testes). Em uso normal, fica 0 (worker).
SYNC = _bool("DOCRISK_SYNC")
