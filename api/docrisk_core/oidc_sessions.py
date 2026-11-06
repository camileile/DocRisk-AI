from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class OIDCFlowError(ValueError):
    pass


@dataclass(frozen=True)
class OIDCIdentity:
    issuer: str
    subject: str
    nonce: str
    email: str | None = None
    name: str | None = None
    mfa: bool = False


@dataclass(frozen=True)
class LoginAttempt:
    nonce: str
    code_verifier: str
    redirect_uri: str
    expires_at: datetime


@dataclass(frozen=True)
class StoredSession:
    token_hash: str
    identity: OIDCIdentity
    csrf_hash: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class SessionTicket:
    cookie_value: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class LoginRedirect:
    url: str
    state: str
    expires_at: datetime


@dataclass(frozen=True)
class SessionCookiePolicy:
    name: str = "docrisk_session"
    path: str = "/"
    http_only: bool = True
    secure: bool = True
    same_site: str = "lax"

    def __post_init__(self) -> None:
        if self.same_site not in {"lax", "strict", "none"}:
            raise ValueError("same_site deve ser lax, strict ou none")
        if self.same_site == "none" and not self.secure:
            raise ValueError("SameSite=None exige cookie Secure")


class OIDCProvider(Protocol):
    def authorization_url(self, *, redirect_uri: str, state: str, nonce: str,
                          code_challenge: str, scopes: tuple[str, ...]) -> str: ...

    def exchange_code(self, *, code: str, redirect_uri: str, code_verifier: str,
                      expected_nonce: str) -> OIDCIdentity: ...


class LoginAttemptStore(Protocol):
    def save(self, state_hash: str, attempt: LoginAttempt) -> None: ...

    def consume(self, state_hash: str, now: datetime) -> LoginAttempt | None: ...


class SessionStore(Protocol):
    def save(self, session: StoredSession) -> None: ...

    def get(self, token_hash: str, now: datetime) -> StoredSession | None: ...

    def revoke(self, token_hash: str) -> None: ...


class OIDCSessionFlow:
    def __init__(self, provider: OIDCProvider, attempts: LoginAttemptStore, sessions: SessionStore,
                 *, login_ttl: timedelta = timedelta(minutes=10),
                 session_ttl: timedelta = timedelta(hours=8)) -> None:
        if login_ttl <= timedelta(0) or session_ttl <= timedelta(0):
            raise ValueError("Os prazos de login e sessão devem ser positivos")
        self._provider = provider
        self._attempts = attempts
        self._sessions = sessions
        self._login_ttl = login_ttl
        self._session_ttl = session_ttl

    def start_login(self, redirect_uri: str, scopes: tuple[str, ...] = ("openid", "profile", "email"),
                    now: datetime | None = None) -> LoginRedirect:
        if "openid" not in scopes:
            raise ValueError("O escopo openid é obrigatório")
        instante = _utc(now)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        expiry = instante + self._login_ttl
        attempt = LoginAttempt(nonce, verifier, redirect_uri, expiry)
        self._attempts.save(_digest(state), attempt)
        url = self._provider.authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
            code_challenge=challenge,
            scopes=scopes,
        )
        return LoginRedirect(url, state, expiry)

    def complete_login(self, *, code: str, state: str, now: datetime | None = None) -> SessionTicket:
        instante = _utc(now)
        attempt = self._attempts.consume(_digest(state), instante)
        if attempt is None:
            raise OIDCFlowError("Tentativa de login inválida, expirada ou já utilizada")
        if attempt.expires_at <= instante:
            raise OIDCFlowError("Tentativa de login inválida, expirada ou já utilizada")
        identity = self._provider.exchange_code(
            code=code,
            redirect_uri=attempt.redirect_uri,
            code_verifier=attempt.code_verifier,
            expected_nonce=attempt.nonce,
        )
        if not identity.issuer or not identity.subject or not hmac.compare_digest(identity.nonce, attempt.nonce):
            raise OIDCFlowError("A resposta OIDC não corresponde à tentativa de login")
        cookie_value = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        expiry = instante + self._session_ttl
        self._sessions.save(StoredSession(
            token_hash=_digest(cookie_value),
            identity=identity,
            csrf_hash=_digest(csrf_token),
            created_at=instante,
            expires_at=expiry,
        ))
        return SessionTicket(cookie_value, csrf_token, expiry)

    def resolve_session(self, cookie_value: str, now: datetime | None = None) -> StoredSession | None:
        if not cookie_value:
            return None
        instante = _utc(now)
        session = self._sessions.get(_digest(cookie_value), instante)
        if session is None:
            return None
        if session.expires_at <= instante:
            self._sessions.revoke(session.token_hash)
            return None
        return session

    def verify_csrf(self, session: StoredSession, csrf_token: str) -> bool:
        if not csrf_token:
            return False
        return hmac.compare_digest(session.csrf_hash, _digest(csrf_token))

    def logout(self, cookie_value: str) -> None:
        if cookie_value:
            self._sessions.revoke(_digest(cookie_value))


def _utc(value: datetime | None) -> datetime:
    instante = value or datetime.now(timezone.utc)
    if instante.tzinfo is None:
        raise ValueError("A data precisa ter fuso horário")
    return instante.astimezone(timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
