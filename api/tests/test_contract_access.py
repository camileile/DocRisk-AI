"""Atribuição por pessoa, escopo organizacional, revogação e histórico."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from docrisk_core import db
from docrisk_core.api import app
from docrisk_core.pipeline import worker
from test_f2_worker import banco, BETA, pdf
from test_f1_security import headers
from test_d3_07_clerk import identity, signing_key


@pytest.fixture
def scope(banco):
    with db.tx() as conn:
        conn.execute("INSERT INTO contracts VALUES ('CT-X','Segundo contrato Beta','ORG-ALFA','ORG-BETA','ORG-BH',3)")
        conn.execute("INSERT INTO workers VALUES ('TX','Trabalhador sintético X','CT-X')")
        for uid, org, role in (("op2", "ORG-BETA", "OPERADOR_FORN"),
                               ("an2", "ORG-BH", "ANALISTA_BH")):
            conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES (?,?,?,?,?)",
                         (uid, uid, org, role, 'test-' + uid))
    batches = {}
    for cid, wid in (("CT-001", "T001"), ("CT-X", "TX")):
        bid = worker.criar_lote(BETA, cid, "sintetico.pdf", pdf(
            f"DEMONSTRATIVO DE PAGAMENTO DE SALARIO\nMatricula: {wid}\nCompetencia: 10/2026\n"
            "Horas extras 50% | Ref.: 8,00 h | R$ 160,00\nPagina 1 de 1"))
        worker.processar_lote(bid)
        with db.tx() as conn:
            doc = conn.execute("SELECT id FROM documents WHERE batch_id=?", (bid,)).fetchone()[0]
            page = conn.execute("SELECT id FROM pages WHERE batch_id=?", (bid,)).fetchone()[0]
            issue = conn.execute("SELECT id FROM issues WHERE contract_id=? LIMIT 1", (cid,)).fetchone()[0]
            report = conn.execute("INSERT INTO reports (contract_id,competencia,versao,status,autor_id,created_at) "
                                  "VALUES (?,'10/2026',1,'RASCUNHO','u-analista',?)", (cid, db.agora())).lastrowid
            batches[cid] = dict(batch=bid, doc=doc, page=page, issue=issue, report=report)
    return batches


def change(client, uid, cid, active=True, manager='u-gestor-beta', **kwargs):
    return client.put(f'/api/contract-access/users/{uid}/contracts/{cid}', headers=headers(manager),
                      json={'ativo': active, **kwargs})


def test_new_users_fail_closed_and_existing_users_do_not_inherit_new_contract(scope):
    with TestClient(app) as client:
        for uid in ('op2', 'an2'):
            assert client.get('/api/contracts', headers=headers(uid)).json() == []
        for uid in ('u-oper-beta', 'u-analista'):
            assert 'CT-X' not in {c['id'] for c in client.get('/api/contracts', headers=headers(uid)).json()}
            assert client.get(f"/api/batches/{scope['CT-X']['batch']}", headers=headers(uid)).status_code == 404


def test_individual_assignment_shared_documents_and_selective_revocation(scope):
    with TestClient(app) as client:
        for uid in ('op2', 'u-oper-beta'):
            assert change(client, uid, 'CT-X').status_code == 200
        assert change(client, 'op2', 'CT-001').status_code == 200
        for uid in ('op2', 'u-oper-beta'):
            # O lote é de outro operador; visibilidade é por contrato autorizado.
            assert client.get(f"/api/batches/{scope['CT-X']['batch']}", headers=headers(uid)).status_code == 200
        assert change(client, 'op2', 'CT-X', False).status_code == 200
        assert {c['id'] for c in client.get('/api/contracts', headers=headers('op2')).json()} == {'CT-001'}
        assert client.get(f"/api/batches/{scope['CT-X']['batch']}", headers=headers('u-oper-beta')).status_code == 200
        assert client.get(f"/api/batches/{scope['CT-X']['batch']}", headers=headers('op2')).status_code == 404
        for path in ('/api/batches', '/api/documents', '/api/supplier/issues'):
            response = client.get(path, headers=headers('op2'))
            assert response.status_code == 200
            rows = response.json()
            assert all(r['contract_id'] == 'CT-001' for r in rows)
        results = client.get('/api/search?q=TX', headers=headers('op2')).json()
        assert 'CT-X' not in str(results)
    with db.tx() as conn:
        assert conn.execute('SELECT 1 FROM batches WHERE id=?', (scope['CT-X']['batch'],)).fetchone()
        assert conn.execute("SELECT revoked_by FROM user_contract_grants WHERE user_id='op2' AND contract_id='CT-X'").fetchone()[0] == 'u-gestor-beta'
        assert conn.execute("SELECT 1 FROM audit WHERE acao='CONTRATO_ACESSO_REVOGADO' AND alvo='op2:CT-X'").fetchone()


@pytest.mark.parametrize('template', [
    '/api/batches/{batch}', '/api/batches/{batch}/source', '/api/batches/{batch}/documents',
    '/api/documents/{doc}', '/api/documents/{doc}/pages/{page}', '/api/pages/{page}/image',
    '/api/documents/{doc}/anonimizado', '/api/contracts/CT-X/workers',
    '/api/reports/{report}/preview', '/api/reports/{report}/pdf',
])
def test_direct_reads_denied_after_analyst_revocation(scope, template):
    with TestClient(app) as client:
        assert change(client, 'an2', 'CT-X', manager='u-admin').status_code == 200
        assert change(client, 'an2', 'CT-X', False, manager='u-admin').status_code == 200
        response = client.get(template.format(**scope['CT-X']), headers=headers('an2'))
        assert response.status_code == 404
        assert response.headers['X-DocRisk-Contracts-Changed'] == '1'


def test_mutations_denied_after_revocation(scope):
    with TestClient(app) as client:
        assert change(client, 'u-analista', 'CT-X', manager='u-admin').status_code == 200
        assert change(client, 'u-analista', 'CT-X', False, manager='u-admin').status_code == 200
        ids = scope['CT-X']
        assert client.patch(f"/api/documents/{ids['doc']}/review", headers=headers('u-analista'), json={'acao': 'aprovar'}).status_code == 404
        assert client.post(f"/api/batches/{ids['batch']}/reprocess", headers=headers('u-analista')).status_code == 404
        assert client.post(f"/api/reports/{ids['report']}/publish", headers=headers('u-analista'), json={'conteudo_sha256': '0' * 64}).status_code == 404
        assert change(client, 'op2', 'CT-X').status_code == 200
        assert change(client, 'op2', 'CT-X', False).status_code == 200
        assert client.post('/api/supplier/batches', headers=headers('op2'), data={'contract_id': 'CT-X'}, files={'file': ('x.pdf', b'invalid')}).status_code == 404
        assert client.post(f"/api/issues/{ids['issue']}/resubmit", headers=headers('op2'), files={'file': ('x.pdf', b'invalid')}).status_code == 404


@pytest.mark.parametrize('manager,target,cid,expected', [
    ('u-gestor-beta','u-analista','CT-001',404), ('u-admin','op2','CT-001',404),
    ('u-gestor-beta','u-oper-gama','CT-001',404), ('u-gestor-beta','op2','CT-002',404),
    ('u-oper-beta','op2','CT-001',403), ('u-analista','an2','CT-001',403),
    ('u-gestor-alfa','op2','CT-001',403), ('u-admin','u-admin','CT-001',404),
])
def test_managers_cannot_escalate_or_cross_organizations(scope, manager, target, cid, expected):
    with TestClient(app) as client:
        assert change(client, target, cid, manager=manager).status_code == expected
        assert client.get(f'/api/contract-access/users/{target}', headers=headers(manager)).status_code == (200 if expected == 404 and manager == 'u-gestor-beta' and target == 'op2' else expected)


def test_expiration_idempotency_renewal_and_restart(scope):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    with TestClient(app) as client:
        for _ in range(2):
            assert change(client, 'op2', 'CT-X', expires_at=future).status_code == 200
        with db.tx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM user_contract_grants WHERE user_id='op2'").fetchone()[0] == 1
            conn.execute("UPDATE user_contract_grants SET expires_at=? WHERE user_id='op2'", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
        assert client.get('/api/contracts', headers=headers('op2')).json() == []
        assert change(client, 'op2', 'CT-X').status_code == 200
        for _ in range(2):
            assert change(client, 'op2', 'CT-X', False).status_code == 200
        assert change(client, 'u-oper-beta', 'CT-001', False).status_code == 200
    db.init_db()
    with TestClient(app) as client:
        assert client.get('/api/contracts', headers=headers('op2')).json() == []
        assert client.get('/api/contracts', headers=headers('u-oper-beta')).json() == []
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_contract_grants WHERE user_id='op2'").fetchone()[0] == 2


@pytest.mark.parametrize('expiry', ['2020-01-01T00:00:00Z', '2099-01-01T00:00:00', 'invalid'])
def test_invalid_expiry_rejected(scope, expiry):
    with TestClient(app) as client:
        assert change(client, 'op2', 'CT-X', expires_at=expiry).status_code == 422


def test_clerk_uses_same_grants_without_token_fallback(identity):
    with TestClient(app) as client:
        manager, analyst = identity['headers'](), identity['headers']('u-analista')
        result = client.put('/api/contract-access/users/u-analista/contracts/CT-001',
                            headers=manager, json={'ativo': False})
        assert result.status_code == 200
        assert {c['id'] for c in client.get('/api/contracts', headers=analyst).json()} == {'CT-002'}
        assert client.put('/api/contract-access/users/u-analista/contracts/CT-001', headers=manager,
                          json={'ativo': True}).status_code == 200
        assert {c['id'] for c in client.get('/api/contracts', headers=analyst).json()} == {'CT-001', 'CT-002'}


def test_organization_boundary_survives_inconsistent_grant_and_other_auditor(scope):
    with db.tx() as conn:
        conn.execute("INSERT INTO organizations VALUES ('AUD-OTHER','Outra auditora','BERNHOEFT')")
        conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES ('other-admin','Outro admin','AUD-OTHER','ADMIN_BH','other-admin-test')")
        conn.execute("INSERT INTO user_contract_grants (user_id,contract_id,granted_by,granted_at) VALUES ('op2','CT-002','u-admin',?)",
                     (datetime.now(timezone.utc).isoformat(),))
    with TestClient(app) as client:
        assert change(client, 'an2', 'CT-001', manager='other-admin').status_code == 404
        assert client.get('/api/contracts', headers=headers('op2')).json() == []
        assert client.get('/api/contracts/CT-002/workers', headers=headers('op2')).status_code == 404
        platform = client.get('/api/demo/users').json()
        token = next(u['token'] for u in platform if u['id'] == 'u-plataforma')
        assert client.put('/api/contract-access/users/an2/contracts/CT-001',
                          headers={'Authorization': 'Bearer ' + token}, json={'ativo': True}).status_code == 403


def test_analyst_lists_metrics_and_aej_respect_selective_assignment(scope):
    with TestClient(app) as client:
        assert change(client, 'an2', 'CT-001', manager='u-admin').status_code == 200
        for endpoint in ('/api/documents', '/api/issues', '/api/analyses', '/api/reports', '/api/review-queue'):
            result = client.get(endpoint, headers=headers('an2'))
            assert result.status_code == 200
            assert all(item['contract_id'] == 'CT-001' for item in result.json())
        metrics = client.get('/api/bernhoeft/metrics', headers=headers('an2')).json()
        assert metrics['contratos'] == ['CT-001']
        assert client.get('/api/contracts/CT-X/aej-mappings', headers=headers('an2')).status_code == 404
        assert client.put('/api/contracts/CT-X/aej-mappings/1', headers=headers('an2'), json={'worker_id': 'TX'}).status_code == 404
        assert client.patch(f"/api/documents/{scope['CT-X']['doc']}/aej-review", headers=headers('an2'),
                            json={'horas_extras_h': 2, 'justificativa': 'Conferência sintética'}).status_code == 404


def test_existing_database_migrates_without_operational_backfill(scope, monkeypatch):
    from docrisk_core import config
    from docrisk_core.auth import Usuario, contratos_do_usuario
    from docrisk_core.contracts import Papel

    with db.tx() as conn:
        documents = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        conn.execute('DROP TABLE user_contract_grants')
        conn.execute("DELETE FROM schema_migrations WHERE version='0002_user_contract_grants.sql'")
    monkeypatch.setattr(config, 'AUTH_MODE', 'clerk')
    monkeypatch.setattr(config, 'DEMO_MODE', False)
    db.init_db(seed=False)
    db.init_db(seed=False)
    with db.tx() as conn:
        assert conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == documents
        assert conn.execute('SELECT COUNT(*) FROM user_contract_grants').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version='0002_user_contract_grants.sql'").fetchone()[0] == 1
        assert contratos_do_usuario(conn, Usuario('u-analista', 'Analista', 'ORG-BH', 'BERNHOEFT', Papel.ANALISTA_BH)) == []
