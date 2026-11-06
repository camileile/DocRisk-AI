from datetime import datetime, timedelta, timezone
import base64
import hashlib

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config
from docrisk_core.api import app
from docrisk_core.oidc_sessions import (
    OIDCFlowError,
    OIDCIdentity,
    OIDCSessionFlow,
    SessionCookiePolicy,
)
from test_analyst_overview import _token
from test_f2_worker import banco  # noqa: F401


class MemoryAttemptStore:
    def __init__(self):
        self.attempts = {}

    def save(self, state_hash, attempt):
        self.attempts[state_hash] = attempt

    def consume(self, state_hash, now):
        return self.attempts.pop(state_hash, None)


class MemorySessionStore:
    def __init__(self):
        self.sessions = {}

    def save(self, session):
        self.sessions[session.token_hash] = session

    def get(self, token_hash, now):
        return self.sessions.get(token_hash)

    def revoke(self, token_hash):
        self.sessions.pop(token_hash, None)


class FakeOIDCProvider:
    def __init__(self):
        self.authorization = None
        self.exchange = None
        self.wrong_nonce = False

    def authorization_url(self, *, redirect_uri, state, nonce, code_challenge, scopes):
        self.authorization = {
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "scopes": scopes,
        }
        return "https://identity.example/authorize"

    def exchange_code(self, *, code, redirect_uri, code_verifier, expected_nonce):
        self.exchange = {
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "expected_nonce": expected_nonce,
        }
        nonce = "unexpected" if self.wrong_nonce else expected_nonce
        return OIDCIdentity("https://identity.example", "subject-123", nonce, mfa=True)


def _flow(provider=None, attempts=None, sessions=None, **kwargs):
    provider = provider or FakeOIDCProvider()
    attempts = attempts or MemoryAttemptStore()
    sessions = sessions or MemorySessionStore()
    return OIDCSessionFlow(provider, attempts, sessions, **kwargs), provider, attempts, sessions


def test_oidc_login_contract_uses_pkce_s256_and_one_time_state():
    flow, provider, attempts, sessions = _flow()
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    started = flow.start_login("https://app.example/auth/callback", now=now)
    params = provider.authorization
    attempt = next(iter(attempts.attempts.values()))
    challenge = base64.urlsafe_b64decode(params["code_challenge"] + "==")

    assert params["scopes"] == ("openid", "profile", "email")
    assert challenge == hashlib.sha256(attempt.code_verifier.encode("ascii")).digest()
    assert started.state == params["state"]
    assert started.expires_at == now + timedelta(minutes=10)
    assert len(sessions.sessions) == 0

    ticket = flow.complete_login(code="auth-code", state=started.state, now=now + timedelta(seconds=1))
    assert provider.exchange["code_verifier"] == attempt.code_verifier
    assert provider.exchange["expected_nonce"] == params["nonce"]
    assert ticket.cookie_value not in sessions.sessions
    assert list(sessions.sessions.values())[0].token_hash != ticket.cookie_value
    with pytest.raises(OIDCFlowError):
        flow.complete_login(code="auth-code", state=started.state, now=now + timedelta(seconds=2))


def test_oidc_nonce_csrf_expiration_and_logout_contracts():
    flow, provider, _, sessions = _flow(session_ttl=timedelta(minutes=1))
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    started = flow.start_login("https://app.example/auth/callback", now=now)
    ticket = flow.complete_login(code="auth-code", state=started.state, now=now)
    session = flow.resolve_session(ticket.cookie_value, now=now)
    assert session is not None and session.identity.mfa
    assert flow.verify_csrf(session, ticket.csrf_token)
    assert not flow.verify_csrf(session, "wrong")
    assert flow.resolve_session(ticket.cookie_value, now=now + timedelta(minutes=1)) is None
    assert sessions.sessions == {}

    flow2, provider2, _, sessions2 = _flow()
    provider2.wrong_nonce = True
    started2 = flow2.start_login("https://app.example/auth/callback", now=now)
    with pytest.raises(OIDCFlowError, match="não corresponde"):
        flow2.complete_login(code="auth-code", state=started2.state, now=now)
    assert sessions2.sessions == {}

    started3 = flow.start_login("https://app.example/auth/callback", now=now)
    ticket3 = flow.complete_login(code="auth-code", state=started3.state, now=now)
    flow.logout(ticket3.cookie_value)
    assert flow.resolve_session(ticket3.cookie_value, now=now) is None


def test_cookie_policy_requires_http_only_secure_and_valid_samesite():
    policy = SessionCookiePolicy()
    assert policy.http_only and policy.secure and policy.same_site == "lax"
    with pytest.raises(ValueError, match="Secure"):
        SessionCookiePolicy(secure=False, same_site="none")
    with pytest.raises(ValueError, match="same_site"):
        SessionCookiePolicy(same_site="invalid")


def test_demo_bearer_authentication_is_rejected_in_operational_mode(banco, monkeypatch):
    monkeypatch.setattr(config, "AUTH_MODE", "token")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    with TestClient(app) as client:
        response = client.get("/api/me", headers={"Authorization": f"Bearer {_token('u-analista')}"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
