"""Clerk sem chamadas externas: assinatura real, estado de sessão e autorização interna."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from docrisk_core import config, db, clerk_identity
from docrisk_core.api import app
from test_f2_worker import banco

ISSUER = 'https://docrisk.clerk.accounts.dev'
PARTY = 'https://docrisk.test'


@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def identity(banco, monkeypatch, signing_key):
    monkeypatch.setattr(config, 'AUTH_MODE', 'clerk')
    monkeypatch.setattr(config, 'CLERK_ISSUER', ISSUER)
    monkeypatch.setattr(config, 'CLERK_SECRET_KEY', 'test-only-not-a-real-key')
    monkeypatch.setattr(config, 'CLERK_AUTHORIZED_PARTIES', (PARTY,))
    monkeypatch.setattr(config, 'CLERK_INVITE_REDIRECT_URL', PARTY + '/entrar')
    monkeypatch.setattr(config, 'CLERK_AUDIENCE', '')
    monkeypatch.setattr(clerk_identity, 'jwks_client', lambda issuer: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=signing_key.public_key())))
    state = {'revoked': set(), 'email': 'person@example.test', 'verified': True, 'calls': []}
    def provider(method, path, payload=None):
        state['calls'].append((method,path,payload))
        if path.startswith('/sessions/'):
            uid = path.split('/')[-1].removeprefix('sess_')
            return {'status': 'revoked' if uid in state['revoked'] else 'active', 'user_id': 'user_' + uid}
        if path.startswith('/users/'):
            return {'primary_email_address_id':'email_1','email_addresses':[{'id':'email_1','email_address':state['email'], 'verification':{'status':'verified' if state['verified'] else 'unverified'}}]}
        if method == 'GET' and path.startswith('/invitations?'): return {'data':[{'id':'inv_test','email_address':'person@example.test','status':state.get('provider_invitation_status','pending')}],'total_count':1}
        if method == 'POST' and path == '/invitations': return {'id':'inv_test'}
        if path.endswith('/revoke'): return {'status':'revoked'}
        raise AssertionError((method,path))
    monkeypatch.setattr(clerk_identity, 'clerk_api', provider)
    with db.tx() as conn:
        for row in conn.execute('SELECT id FROM users').fetchall():
            uid = row['id']
            conn.execute('INSERT INTO identity_links (id,issuer,subject,user_id,created_at) VALUES (?,?,?,?,?)', ('link-'+uid,ISSUER,'user_'+uid,uid,db.agora()))
        platform = conn.execute('SELECT id FROM platform_accounts LIMIT 1').fetchone()[0]
        conn.execute('INSERT INTO identity_links (id,issuer,subject,platform_account_id,created_at) VALUES (?,?,?,?,?)', ('link-platform',ISSUER,'user_platform',platform,db.agora()))
    def token(uid='u-admin', **claims):
        current = datetime.now(timezone.utc)
        return jwt.encode({'iss':ISSUER,'sub':'user_'+uid,'sid':'sess_'+uid,'azp':PARTY,'iat':current,'exp':current+timedelta(minutes=1),**claims}, signing_key, algorithm='RS256')
    state['token'] = token
    state['headers'] = lambda uid='u-admin', link=None: {'Authorization':'Bearer '+token(uid), 'X-DocRisk-Link':link or ('link-platform' if uid=='platform' else 'link-'+uid)}
    return state


@pytest.mark.parametrize('claim', [
    {'iss':'https://attacker.test'}, {'azp':'https://attacker.test'},
    {'exp':datetime(2000,1,1,tzinfo=timezone.utc)}, {'sub':None}, {'sid':None},
])
def test_invalid_jwt_rejected(identity, claim):
    with TestClient(app) as client:
        result = client.get('/api/auth/links',headers={'Authorization':'Bearer '+identity['token'](**claim)})
    assert result.status_code == 401
    assert not identity['calls']


def test_signature_and_algorithm_are_not_trusted_from_token(identity):
    forged = jwt.encode({'iss':ISSUER,'sub':'user_u-admin'},'attacker-secret-not-a-real-credential',algorithm='HS256')
    with TestClient(app) as client:
        response = client.get('/api/auth/links',headers={'Authorization':'Bearer '+forged})
    assert response.status_code == 401


def test_current_session_and_local_binding_are_required(identity):
    with TestClient(app) as client:
        good = client.get('/api/me',headers=identity['headers']())
        assert good.status_code == 200 and good.json()['papel'] == 'ADMIN_BH'
        wrong = client.get('/api/me',headers=identity['headers'](link='link-u-oper-beta'))
        assert wrong.status_code == 403
        identity['revoked'].add('u-admin')
        assert client.get('/api/me',headers=identity['headers']()).status_code == 401
        identity['revoked'].clear()
        with db.tx() as conn: conn.execute("UPDATE identity_links SET ativo=0 WHERE id='link-u-admin'")
        assert client.get('/api/me',headers=identity['headers']()).status_code == 403


def test_seed_token_never_falls_back_in_clerk_mode(identity):
    with db.tx() as conn: legacy = conn.execute("SELECT token FROM users WHERE id='u-admin'").fetchone()[0]
    with TestClient(app) as client:
        assert client.get('/api/me',headers={'Authorization':'Bearer '+legacy}).status_code == 401
        assert client.get('/api/demo/users').status_code == 404


def test_provider_outage_fails_closed(identity, monkeypatch):
    def outage(*args, **kwargs): raise HTTPException(503,'Provider unavailable')
    monkeypatch.setattr(clerk_identity,'clerk_api',outage)
    with TestClient(app) as client:
        assert client.get('/api/me',headers=identity['headers']()).status_code == 503


def test_platform_and_admin_keep_document_restrictions(identity):
    with TestClient(app) as client:
        for uid in ['platform','u-admin']:
            assert client.get('/api/documents',headers=identity['headers'](uid)).status_code == 403
        supplier = client.get('/api/contracts',headers=identity['headers']('u-oper-beta'))
        assert all(row['fornecedora_id']=='ORG-BETA' for row in supplier.json())


def invite(client, identity, uid='u-admin', **changes):
    return client.post('/api/auth/invitations',headers=identity['headers'](uid),json={
        'email':'person@example.test','nome':'Pessoa Convidada','org_id':'ORG-BETA','role':'GESTOR_FORN',**changes})


@pytest.mark.parametrize('uid,org,role,expected',[
    ('platform','ORG-BH','ADMIN_BH',201), ('platform','ORG-BETA','OPERADOR_FORN',403),
    ('u-admin','ORG-BH','ANALISTA_BH',201), ('u-admin','ORG-BETA','GESTOR_FORN',201),
    ('u-admin','ORG-BETA','OPERADOR_FORN',403), ('u-gestor-beta','ORG-BETA','OPERADOR_FORN',201),
    ('u-gestor-beta','ORG-GAMA','OPERADOR_FORN',403), ('u-oper-beta','ORG-BETA','OPERADOR_FORN',403),
    ('u-analista','ORG-BH','ADMIN_BH',403), ('u-gestor-alfa','ORG-BETA','GESTOR_FORN',403),
])
def test_invite_permissions(identity,uid,org,role,expected):
    with TestClient(app) as client:
        response=invite(client,identity,uid,org_id=org,role=role)
    assert response.status_code==expected,response.text
    if expected==201:
        sent=[c for c in identity['calls'] if c[:2]==('POST','/invitations')]
        assert sent[0][2]['expires_in_days']==3 and sent[0][2]['redirect_url']==PARTY+'/entrar'
        assert sent[0][2]['ignore_existing'] is True


def test_accept_requires_verified_matching_email_and_is_single_use(identity):
    h={'Authorization':'Bearer '+identity['token']('new')}
    with TestClient(app) as client:
        invitation=invite(client,identity).json()['id']
        identity['verified']=False
        assert client.post(f'/api/auth/invitations/{invitation}/accept',headers=h).status_code==403
        identity['verified']=True; identity['email']='other@example.test'
        assert client.post(f'/api/auth/invitations/{invitation}/accept',headers=h).status_code==404
        identity['email']='person@example.test'
        accepted=client.post(f'/api/auth/invitations/{invitation}/accept',headers=h)
        assert accepted.status_code==200,accepted.text
        assert client.post(f'/api/auth/invitations/{invitation}/accept',headers=h).status_code==409
        links=client.get('/api/auth/links',headers=h).json()
        assert len(links)==1 and links[0]['papel']=='GESTOR_FORN'
        me=client.get('/api/me',headers={**h,'X-DocRisk-Link':links[0]['id']}).json()
        assert me['org_id']=='ORG-BETA'


@pytest.mark.parametrize('change',['expired','revoked','inviter_revoked'])
def test_invalid_invitation_cannot_activate(identity,change):
    with TestClient(app) as client:
        invitation=invite(client,identity).json()['id']
        if change=='revoked':
            assert client.post(f'/api/auth/invitations/{invitation}/revoke',headers=identity['headers']()).status_code==200
        else:
            with db.tx() as conn:
                if change=='expired': conn.execute("UPDATE identity_invitations SET expires_at='2000-01-01' WHERE id=?",(invitation,))
                else: conn.execute("UPDATE identity_links SET ativo=0 WHERE id='link-u-admin'")
        result=client.post(f'/api/auth/invitations/{invitation}/accept',headers={'Authorization':'Bearer '+identity['token']('new')})
        assert result.status_code in {403,409}
    with db.tx() as conn:
        assert conn.execute("SELECT count(*) FROM identity_links WHERE subject='user_new'").fetchone()[0]==0


def test_manager_revocation_takes_effect_next_request(identity):
    with TestClient(app) as client:
        response=client.patch('/api/auth/links/link-u-oper-beta',headers=identity['headers']('u-gestor-beta'),json={'ativo':False})
        assert response.status_code==200
        assert client.get('/api/me',headers=identity['headers']('u-oper-beta')).status_code==403
        assert client.patch('/api/auth/links/link-u-admin',headers=identity['headers']('u-gestor-beta'),json={'ativo':False}).status_code==403
        assert client.patch('/api/auth/links/link-u-gestor-beta',headers=identity['headers']('u-gestor-beta'),json={'ativo':False}).status_code==403


def test_invitation_revoked_at_provider_is_not_accepted(identity):
    with TestClient(app) as client:
        invitation=invite(client,identity).json()['id']
        identity['provider_invitation_status']='revoked'
        response=client.post(f'/api/auth/invitations/{invitation}/accept',headers={'Authorization':'Bearer '+identity['token']('new')})
    assert response.status_code==409


def test_production_startup_does_not_seed_demo_accounts(identity, monkeypatch, tmp_path):
    data = tmp_path/'productive-empty'
    monkeypatch.setattr(config,'DATA_DIR',data)
    monkeypatch.setattr(config,'DB_PATH',data/'db.sqlite')
    monkeypatch.setattr(config,'UPLOAD_DIR',data/'uploads')
    monkeypatch.setattr(config,'PAGES_DIR',data/'pages')
    with TestClient(app):
        with db.tx() as conn:
            assert conn.execute('SELECT count(*) FROM users').fetchone()[0]==0
            assert conn.execute('SELECT count(*) FROM platform_accounts').fetchone()[0]==0
            assert conn.execute('SELECT count(*) FROM organizations').fetchone()[0]==0


def test_token_mode_requires_explicit_demo_configuration(identity, monkeypatch):
    with db.tx() as conn:
        token=conn.execute("SELECT token FROM users WHERE id='u-admin'").fetchone()[0]
    monkeypatch.setattr(config,'AUTH_MODE','token')
    monkeypatch.setattr(config,'DEMO_MODE',False)
    with TestClient(app) as client:
        assert client.get('/api/me',headers={'Authorization':'Bearer '+token}).status_code==401


@pytest.mark.parametrize('uid', ['u-admin', 'platform'])
def test_clerk_identity_authenticates_without_demo_mode(identity, monkeypatch, uid):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    with TestClient(app) as client:
        response = client.get('/api/me', headers=identity['headers'](uid))
        assert response.status_code == 200, response.text
        expected = 'ADMIN_PLATAFORMA' if uid == 'platform' else 'ADMIN_BH'
        assert response.json()['papel'] == expected
        assert client.get('/api/demo/users').status_code == 404


def test_platform_creation_invites_initial_admin_without_demo_token(identity, monkeypatch):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    headers = identity['headers']('platform')
    with TestClient(app) as client:
        missing = client.post('/api/platform/auditors', headers=headers, json={
            'nome': 'Auditora Nova', 'administrador': 'Admin Inicial'})
        assert missing.status_code == 422
        denied = client.post('/api/platform/auditors', headers=identity['headers']('u-admin'), json={
            'nome': 'Auditora Nova', 'administrador': 'Admin Inicial', 'email': 'person@example.test'})
        assert denied.status_code == 403

        created = client.post('/api/platform/auditors', headers=headers, json={
            'nome': 'Auditora Nova', 'administrador': 'Admin Inicial', 'email': ' Person@Example.Test '})
        assert created.status_code == 201, created.text
        result = created.json()
        assert result['convite_status'] == 'PENDING'
        assert 'token_teste' not in result and 'administrador_id' not in result
        org = result['id']
        with db.tx() as conn:
            assert conn.execute("SELECT tipo FROM organizations WHERE id=?", (org,)).fetchone()[0] == 'BERNHOEFT'
            assert conn.execute("SELECT COUNT(*) FROM users WHERE org_id=?", (org,)).fetchone()[0] == 0
            invitation = conn.execute("SELECT * FROM identity_invitations WHERE id=?", (result['convite_id'],)).fetchone()
            assert invitation['email'] == 'person@example.test'
            assert invitation['org_id'] == org and invitation['role'] == 'ADMIN_BH'
            assert invitation['invited_by'] == 'u-plataforma'
            assert invitation['invited_link_id'] == 'link-platform'

        registry = client.get('/api/platform/registry', headers=headers).json()
        assert any(row['org_id'] == org and row['status'] == 'PENDING' for row in registry['convites_iniciais'])
        assert not any(row['org_id'] == org for row in registry['administradores'])
        assert client.get('/api/me', headers={'Authorization': 'Bearer ' + identity['token']('new')}).status_code == 403

        invite = result['convite_id']
        new_headers = {'Authorization': 'Bearer ' + identity['token']('new')}
        assert any(row['id'] == invite for row in client.get('/api/auth/invitations/pending', headers=new_headers).json())
        accepted = client.post('/api/auth/invitations/' + invite + '/accept', headers=new_headers)
        assert accepted.status_code == 200, accepted.text
        link = accepted.json()['link_id']
        me = client.get('/api/me', headers={**new_headers, 'X-DocRisk-Link': link})
        assert me.status_code == 200
        assert me.json()['nome'] == 'Admin Inicial' and me.json()['org_id'] == org
        assert me.json()['papel'] == 'ADMIN_BH' and me.json()['org_tipo'] == 'BERNHOEFT'
        admin = client.get('/api/admin/registry', headers={**new_headers, 'X-DocRisk-Link': link})
        assert admin.status_code == 200 and admin.json()['empresas'] == []
        registry = client.get('/api/platform/registry', headers=headers).json()
        assert any(row['org_id'] == org and row['nome'] == 'Admin Inicial' for row in registry['administradores'])
        assert any(row['org_id'] == org and row['status'] == 'ACCEPTED' for row in registry['convites_iniciais'])
        duplicate = client.post('/api/platform/auditors', headers=headers, json={
            'nome': ' auditora nova ', 'administrador': 'Outro', 'email': 'other@example.test'})
        assert duplicate.status_code == 409


def test_platform_invitation_failure_rolls_back_new_auditor(identity, monkeypatch):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    real_provider = clerk_identity.clerk_api

    def fail_invite(method, path, payload=None):
        if method == 'POST' and path == '/invitations':
            raise HTTPException(503, 'Falha simulada de convite')
        return real_provider(method, path, payload)

    monkeypatch.setattr(clerk_identity, 'clerk_api', fail_invite)
    with TestClient(app) as client:
        response = client.post('/api/platform/auditors', headers=identity['headers']('platform'), json={
            'nome': 'Auditora Sem Convite', 'administrador': 'Admin Sem Convite',
            'email': 'person@example.test'})
        assert response.status_code == 503
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM organizations WHERE nome='Auditora Sem Convite'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM identity_invitations WHERE nome='Admin Sem Convite'").fetchone()[0] == 0


def test_authenticated_admin_provisions_companies_and_contracts_but_never_demo_tokens(identity, monkeypatch):
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    with TestClient(app) as client:
        h = identity['headers']('u-admin')
        customer = client.post('/api/admin/companies', headers=h, json={
            'tipo': 'CONTRATANTE', 'nome': 'Cliente Sintético MVP'})
        assert customer.status_code == 201, customer.text
        client_id = customer.json()['id']
        supplier = client.post('/api/admin/companies', headers=h, json={
            'tipo': 'FORNECEDORA', 'nome': 'Fornecedora Sintética MVP',
            'contratante_id': client_id, 'contrato_nome': 'Contrato de apresentação'})
        assert supplier.status_code == 201, supplier.text
        supplier_id = supplier.json()['id']
        contract_id = supplier.json()['contract_id']
        assert contract_id.startswith('CT-')
        assert client.post('/api/admin/contracts', headers=h, json={
            'nome': 'Segundo contrato sintético', 'contratante_id': client_id,
            'fornecedora_id': supplier_id}).status_code == 201

        registry = client.get('/api/admin/registry', headers=h)
        assert registry.status_code == 200
        assert any(row['id'] == supplier_id for row in registry.json()['empresas'])
        assert any(row['id'] == contract_id for row in registry.json()['contratos'])
        # Em modo real, contas só podem ser ativadas por convites Clerk.
        assert client.post('/api/admin/users', headers=h, json={
            'nome': 'Conta demonstrativa', 'org_id': 'ORG-BH', 'papel': 'ANALISTA_BH'
        }).status_code == 403
        assert client.patch('/api/admin/users/u-oper-beta/status', headers=h,
                            json={'ativo': False}).status_code == 403
        assert client.post('/api/admin/companies', headers=identity['headers']('u-gestor-beta'), json={
            'tipo': 'CONTRATANTE', 'nome': 'Tentativa proibida'
        }).status_code == 403
        assert client.post('/api/admin/contracts', headers=identity['headers']('platform'), json={
            'nome': 'Sem permissão', 'contratante_id': client_id,
            'fornecedora_id': supplier_id,
        }).status_code == 403

    with db.tx() as conn:
        assert conn.execute('SELECT bernhoeft_id FROM contracts WHERE id=?', (contract_id,)).fetchone()[0] == 'ORG-BH'
        assert conn.execute("SELECT COUNT(*) FROM users WHERE nome='Conta demonstrativa'").fetchone()[0] == 0


def test_controlled_synthetic_worker_provisioning_is_scoped_and_reversible(identity, monkeypatch, tmp_path):
    from pathlib import Path
    from runpy import run_path

    monkeypatch.setattr(config, 'DEMO_MODE', False)
    script = run_path(str(Path(__file__).resolve().parents[1] / 'scripts' / 'provision_mvp_workers.py'))
    csv = tmp_path / 'workers.csv'
    csv.write_text('id,nome\nT8001,Trabalhador Sintético\n', encoding='utf-8')
    # O arquivo CSV é explicitamente fornecido; nenhum seed automático é usado.
    records = script['load_csv'](csv)
    with db.tx() as conn:
        conn.execute("INSERT INTO contracts (id,nome,contratante_id,fornecedora_id,bernhoeft_id) "
                     "VALUES ('CT-SYNTH','Sintético','ORG-ALFA','ORG-BETA','ORG-BH')")
    assert script['provision']('CT-SYNTH', records, False) == (1, 0)
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM workers WHERE id='T8001'").fetchone()[0] == 0
    assert script['provision']('CT-SYNTH', records, True) == (1, 0)
    assert script['provision']('CT-SYNTH', records, True) == (0, 1)
    with pytest.raises(ValueError, match='outro contrato'):
        script['provision']('CT-001', records, True)
    with db.tx() as conn:
        assert conn.execute("SELECT contract_id FROM workers WHERE id='T8001'").fetchone()[0] == 'CT-SYNTH'
        assert conn.execute("SELECT COUNT(*) FROM audit WHERE acao='TRABALHADORES_SINTETICOS_PROVISIONADOS'").fetchone()[0] == 1
