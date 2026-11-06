"""Configuração por variáveis de ambiente (api/.env). Dono: frente 1."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(API_DIR / ".env")


def _bool(nome: str, padrao: str = "0") -> bool:
    return os.getenv(nome, padrao).strip() == "1"


def _num(tipo: type, nome: str, padrao: str):
    """Converte a variável com mensagem clara (sem traceback de int()/float() cru)."""
    bruto = os.getenv(nome, padrao).strip()
    try:
        return tipo(bruto)
    except ValueError:
        raise ValueError(f"Variável {nome} deve ser {'inteiro' if tipo is int else 'número'}; "
                         f"recebido {bruto!r}. Ver .env.example.") from None


DEMO_MODE = _bool("DOCRISK_DEMO_MODE")
DATA_DIR = Path(os.getenv("DOCRISK_DATA_DIR", str(API_DIR / "data"))).resolve()
DB_PATH = DATA_DIR / "docrisk.sqlite"
UPLOAD_DIR = DATA_DIR / "uploads"
PAGES_DIR = DATA_DIR / "pages"

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_RPM = _num(int, "GEMINI_RPM", "8")

LIMIAR_CONFIANCA = _num(float, "LIMIAR_CONFIANCA", "0.75")
LIMIAR_LEGIBILIDADE = _num(float, "LIMIAR_LEGIBILIDADE", "0.5")

MAX_UPLOAD_MB = _num(int, "MAX_UPLOAD_MB", "50")
MAX_PAGINAS = _num(int, "MAX_PAGINAS", "300")
RENDER_DPI = _num(int, "RENDER_DPI", "150")
MAX_LADO_PX = _num(int, "MAX_LADO_PX", "2200")

#: Processa o lote na própria requisição (testes). Em uso normal, fica 0 (worker).
SYNC = _bool("DOCRISK_SYNC")

# Login produtivo: o modo token é permitido somente com DOCRISK_DEMO_MODE=1.
AUTH_MODE = os.getenv("DOCRISK_AUTH_MODE", "token").strip().lower()
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "").strip().rstrip("/")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE", "").strip()
CLERK_AUTHORIZED_PARTIES = tuple(x.strip() for x in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",") if x.strip())
CLERK_INVITE_REDIRECT_URL = os.getenv("CLERK_INVITE_REDIRECT_URL", "").strip()
