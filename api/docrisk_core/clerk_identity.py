"""Identidade Clerk: JWT validado e sessão consultada no provedor, sem fallback demo."""
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import httpx
import jwt
from fastapi import HTTPException

from . import config


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str
    session_id: str


def validate_configuration():
    if config.AUTH_MODE != "clerk":
        return
    origin = urlsplit(config.CLERK_ISSUER)
    if (origin.scheme != "https" or not origin.hostname or origin.path not in {"", "/"}
            or origin.username or origin.password or origin.query or origin.fragment
            or not config.CLERK_SECRET_KEY or not config.CLERK_AUTHORIZED_PARTIES):
        raise RuntimeError("Configure CLERK_ISSUER, CLERK_SECRET_KEY e CLERK_AUTHORIZED_PARTIES para o login Clerk.")


def clerk_api(method: str, path: str, payload=None):
    if not config.CLERK_SECRET_KEY:
        raise HTTPException(503, "Provedor de identificação não configurado.")
    try:
        response = httpx.request(method, "https://api.clerk.com/v1" + path,
                                headers={"Authorization": "Bearer " + config.CLERK_SECRET_KEY},
                                json=payload, timeout=8, follow_redirects=False)
        response.raise_for_status()
        return response.json() if response.content else {}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403, 404} and path.startswith("/sessions/"):
            raise HTTPException(401, "Sessão inválida ou encerrada.") from exc
        raise HTTPException(503, "Não foi possível confirmar a operação no provedor de identificação.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Provedor de identificação indisponível. Tente novamente.") from exc


@lru_cache(maxsize=4)
def jwks_client(issuer: str):
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json", timeout=8, cache_keys=False, lifespan=300)


def authenticate(token: str) -> Principal:
    if config.AUTH_MODE != "clerk":
        raise HTTPException(404, "Login Clerk não está habilitado neste ambiente.")
    try:
        validate_configuration()
    except RuntimeError as exc:
        raise HTTPException(503, "Provedor de identificação não configurado.") from exc
    try:
        key = jwks_client(config.CLERK_ISSUER).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=config.CLERK_ISSUER,
                            audience=config.CLERK_AUDIENCE or None,
                            options={"require": ["exp", "iat", "sub", "sid", "azp"],
                                     "verify_aud": bool(config.CLERK_AUDIENCE)})
        if (claims["azp"] not in config.CLERK_AUTHORIZED_PARTIES
                or not isinstance(claims["sub"], str) or not claims["sub"].startswith("user_")
                or not isinstance(claims["sid"], str) or not claims["sid"].startswith("sess_")):
            raise jwt.InvalidTokenError("Invalid principal")
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(503, "Não foi possível validar a identificação agora.") from exc
    except (jwt.PyJWTError, TypeError, KeyError, ValueError) as exc:
        raise HTTPException(401, "Identificação inválida ou expirada.", headers={"WWW-Authenticate": "Bearer"}) from exc
    # Assinatura válida não comprova que a sessão ainda está ativa.
    session = clerk_api("GET", "/sessions/" + claims["sid"])
    if session.get("status") != "active" or session.get("user_id") != claims["sub"]:
        raise HTTPException(401, "Sessão encerrada ou revogada.")
    return Principal(config.CLERK_ISSUER, claims["sub"], claims["sid"])


def verified_email(principal: Principal) -> str:
    user = clerk_api("GET", "/users/" + principal.subject)
    if user.get("banned") or user.get("locked"):
        raise HTTPException(401, "Conta indisponível.")
    primary = user.get("primary_email_address_id")
    for address in user.get("email_addresses", []):
        if address.get("id") == primary and address.get("verification", {}).get("status") == "verified":
            return address["email_address"].strip().casefold()
    raise HTTPException(403, "Confirme o e-mail principal antes de aceitar o convite.")


def invitation_active(provider_id: str, email: str) -> bool:
    from urllib.parse import urlencode
    offset = 0
    while offset < 1000:
        result = clerk_api("GET", "/invitations?" + urlencode({"query": email, "limit": 100, "offset": offset}))
        rows = result.get("data", [])
        for row in rows:
            if row.get("id") == provider_id and row.get("email_address", "").casefold() == email:
                return row.get("status") in {"pending", "accepted"}
        offset += len(rows)
        if not rows or offset >= result.get("total_count", 0):
            return False
    raise HTTPException(503, "Não foi possível confirmar o convite no provedor.")
