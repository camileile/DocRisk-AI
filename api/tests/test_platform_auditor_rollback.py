from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from docrisk_core import config, db, clerk_identity
from docrisk_core.api import app
from test_d3_07_clerk import identity, signing_key
from test_f2_worker import banco

@pytest.mark.parametrize('accepted', [False, True])
def test_failed_initial_invite_preserves_another_successful_invite(identity, monkeypatch, accepted):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    provider = clerk_identity.clerk_api
    issued = {}
    with TestClient(app) as client:
        def concurrent_provider(method, path, payload=None):
            if method == 'POST' and path == '/invitations' and payload['email_address'] == 'first@example.test':
                with db.tx() as conn:
                    issued['org'] = conn.execute("SELECT id FROM organizations WHERE nome='Auditora Concorrente'").fetchone()[0]
                second = client.post('/api/auth/invitations', headers=identity['headers']('platform'), json={
                    'email': 'second@example.test', 'nome': 'Segundo Admin',
                    'org_id': issued['org'], 'role': 'ADMIN_BH'})
                assert second.status_code == 201, second.text
                issued['id'] = second.json()['id']
                if accepted:
                    identity['email'] = 'second@example.test'
                    monkeypatch.setattr(clerk_identity, 'invitation_active',
                                        lambda provider_id, email: provider_id == 'inv_test' and email == 'second@example.test')
                    recipient = {'Authorization': 'Bearer ' + identity['token']('new')}
                    response = client.post('/api/auth/invitations/' + issued['id'] + '/accept', headers=recipient)
                    assert response.status_code == 200, response.text
                    issued['link'] = response.json()['link_id']
                raise HTTPException(503, 'Falha do primeiro envio')
            return provider(method, path, payload)
        monkeypatch.setattr(clerk_identity, 'clerk_api', concurrent_provider)
        first = client.post('/api/platform/auditors', headers=identity['headers']('platform'), json={
            'nome': 'Auditora Concorrente', 'administrador': 'Primeiro Admin', 'email': 'first@example.test'})
        assert first.status_code == 503
        with db.tx() as conn:
            row = conn.execute('SELECT status FROM identity_invitations WHERE id=?', (issued['id'],)).fetchone()
            assert row is not None, 'Rollback apagou outro convite emitido com sucesso'
            assert row['status'] == ('ACCEPTED' if accepted else 'PENDING')
            assert conn.execute('SELECT 1 FROM organizations WHERE id=?', (issued['org'],)).fetchone()
            assert conn.execute("SELECT COUNT(*) FROM identity_invitations WHERE email='first@example.test'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM users WHERE org_id=?", (issued['org'],)).fetchone()[0] == int(accepted)
            assert conn.execute("SELECT 1 FROM audit WHERE acao='AUDITORA_CADASTRO_PRESERVADO' AND alvo=? AND resultado='ERRO'", (issued['org'],)).fetchone()
        if accepted:
            me = client.get('/api/me', headers={'Authorization': 'Bearer ' + identity['token']('new'),
                                              'X-DocRisk-Link': issued['link']})
            assert me.status_code == 200, me.text
            assert me.json()['org_id'] == issued['org'] and me.json()['papel'] == 'ADMIN_BH'


def test_initial_invite_can_be_retried_after_an_isolated_failure(identity, monkeypatch):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    provider = clerk_identity.clerk_api
    failures = [True]

    def fail_once(method, path, payload=None):
        if method == 'POST' and path == '/invitations' and failures:
            failures.pop()
            raise HTTPException(503, 'Falha temporária')
        return provider(method, path, payload)

    monkeypatch.setattr(clerk_identity, 'clerk_api', fail_once)
    payload = {'nome': 'Auditora Retry', 'administrador': 'Admin Retry', 'email': 'person@example.test'}
    with TestClient(app) as client:
        headers = identity['headers']('platform')
        assert client.post('/api/platform/auditors', headers=headers, json=payload).status_code == 503
        response = client.post('/api/platform/auditors', headers=headers, json=payload)
        assert response.status_code == 201, response.text
        assert response.json()['convite_status'] == 'PENDING' and 'token_teste' not in response.json()
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM organizations WHERE nome='Auditora Retry'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM identity_invitations WHERE nome='Admin Retry' AND status='PENDING'").fetchone()[0] == 1
