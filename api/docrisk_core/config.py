"""Configuração por variáveis de ambiente (api/.env). Dono: frente 1."""
from __future__ import annotations

import os
import math
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(API_DIR / ".env")


def _bool(nome: str, padrao: str = "0") -> bool:
    return os.getenv(nome, padrao).strip() == "1"


def _opcional_tarifa(nome: str) -> float | None:
    valor = os.getenv(nome, "").strip()
    if not valor:
        return None
    tarifa = float(valor)
    if not math.isfinite(tarifa) or tarifa < 0:
        raise ValueError(f"{nome} deve ser um número finito não negativo.")
    return tarifa


def _inteiro_positivo(nome: str, padrao: str) -> int:
    valor = int(os.getenv(nome, padrao))
    if valor <= 0:
        raise ValueError(f"{nome} deve ser maior que zero.")
    return valor


DEMO_MODE = _bool("DOCRISK_DEMO_MODE")
DATA_DIR = Path(os.getenv("DOCRISK_DATA_DIR", str(API_DIR / "data"))).resolve()
DB_PATH = DATA_DIR / "docrisk.sqlite"
UPLOAD_DIR = DATA_DIR / "uploads"
PAGES_DIR = DATA_DIR / "pages"

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_RPM = int(os.getenv("GEMINI_RPM", "8"))
GEMINI_TIMEOUT_MS = _inteiro_positivo("GEMINI_TIMEOUT_MS", "60000")
GEMINI_MAX_OUTPUT_TOKENS = _inteiro_positivo("GEMINI_MAX_OUTPUT_TOKENS", "2048")
GEMINI_INPUT_USD_PER_MILLION = _opcional_tarifa("GEMINI_INPUT_USD_PER_MILLION")
GEMINI_OUTPUT_USD_PER_MILLION = _opcional_tarifa("GEMINI_OUTPUT_USD_PER_MILLION")

LIMIAR_CONFIANCA = float(os.getenv("LIMIAR_CONFIANCA", "0.75"))
LIMIAR_LEGIBILIDADE = float(os.getenv("LIMIAR_LEGIBILIDADE", "0.5"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_PAGINAS = int(os.getenv("MAX_PAGINAS", "300"))
RENDER_DPI = int(os.getenv("RENDER_DPI", "150"))
MAX_LADO_PX = int(os.getenv("MAX_LADO_PX", "2200"))

#: Processa o lote na própria requisição (testes). Em uso normal, fica 0 (worker).
SYNC = _bool("DOCRISK_SYNC")

# Login produtivo: o modo token é permitido somente com DOCRISK_DEMO_MODE=1.
AUTH_MODE = os.getenv("DOCRISK_AUTH_MODE", "token").strip().lower()
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "").strip().rstrip("/")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE", "").strip()
CLERK_AUTHORIZED_PARTIES = tuple(x.strip() for x in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",") if x.strip())
CLERK_INVITE_REDIRECT_URL = os.getenv("CLERK_INVITE_REDIRECT_URL", "").strip()
