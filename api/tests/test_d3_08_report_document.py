"""D3-08: publicação da prévia exata, recomendações públicas e PDF autorizado."""
import json
from copy import deepcopy

import pymupdf
import pytest
from fastapi.testclient import TestClient

from docrisk_core import db, report_pdf
from docrisk_core.api import app
from test_f2_worker import banco


def headers(user='u-analista'):
    with db.tx() as conn:
        row=conn.execute('SELECT token FROM users WHERE id=?',(user,)).fetchone()
        if row is None: row=conn.execute('SELECT token FROM platform_accounts WHERE id=?',(user,)).fetchone()
    return {'Authorization':'Bearer '+row[0]}


def create(client, **extra):
    r=client.post('/api/reports',headers=headers(),json={'contract_id':'CT-001','competencia':'10/2026',**extra})
    assert r.status_code==201,r.text
    return r.json()['id']


def preview(client,rid,user='u-analista'):
    response=client.get(f'/api/reports/{rid}/preview',headers=headers(user))
    assert response.status_code==200,response.text
    return response.json()


def publish(client,rid,checked=None,user='u-analista'):
    checked=checked or preview(client,rid,user)
    return client.post(f'/api/reports/{rid}/publish',headers=headers(user),json={'conteudo_sha256':checked['conteudo_sha256']})


def pdf_text(response):
    assert response.status_code==200,response.text[:100] if not response.content.startswith(b'%PDF') else ''
    assert response.headers['content-type']=='application/pdf'
    with pymupdf.open(stream=response.content,filetype='pdf') as doc:
        return ' '.join(' '.join(page.get_text() for page in doc).split())


def test_exact_preview_survives_time_and_internal_notes_stay_private(banco,monkeypatch):
    with TestClient(app) as client:
        rid=create(client,observacoes='SEGREDO_INTERNO_X',recomendacoes='Conferir o ponto com a fornecedora.\nConcluir os casos pendentes.')
        monkeypatch.setattr(db,'agora',lambda:'2026-11-06T10:00:00')
        checked=preview(client,rid)
        monkeypatch.setattr(db,'agora',lambda:'2026-11-06T10:09:00')
        assert preview(client,rid)['conteudo_json']==checked['conteudo_json']
        body=checked['conteudo_json'];identity=body['parecer']
        assert identity['autor']['id']==identity['responsavel']['id']=='u-analista'
        assert identity['id']==rid and identity['versao']==1 and identity['emissor']=='Bernhoeft (demo)'
        draft_pdf=client.get(f'/api/reports/{rid}/pdf?conteudo_sha256='+checked['conteudo_sha256'],headers=headers())
        text=pdf_text(draft_pdf)
        assert 'PRÉVIA DO RASCUNHO' in text and 'Concluir os casos pendentes.' in text
        assert 'SEGREDO_INTERNO_X' not in text
        response=publish(client,rid,checked)
        assert response.status_code==200,response.text
        assert response.json()['conteudo_json']==checked['conteudo_json']
        public=client.get('/api/client/reports',headers=headers('u-gestor-alfa')).json()[0]
        assert public['conteudo_json']==body and 'observacoes' not in public
        published_pdf=client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa'))
        text=pdf_text(published_pdf)
        assert 'PARECER PUBLICADO' in text and 'PRÉVIA DO RASCUNHO' not in text
        assert 'SEGREDO_INTERNO_X' not in text and 'Analista Bernhoeft (demo)' in text
        assert 'Cache-Control' in published_pdf.headers and 'attachment;' in published_pdf.headers['Content-Disposition']


def test_author_and_conference_responsible_are_snapshot_identities(banco):
    with db.tx() as conn:
        conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES ('second','Segunda Analista','ORG-BH','ANALISTA_BH','synthetic-second-token')")
    with TestClient(app) as client:
        rid=create(client)
        author_preview=preview(client,rid)
        assert publish(client,rid,author_preview,'second').status_code==409
        checked=preview(client,rid,'second')
        assert checked['conteudo_json']['parecer']['autor']['id']=='u-analista'
        assert checked['conteudo_json']['parecer']['responsavel']['id']=='second'
        assert publish(client,rid,checked,'second').status_code==200
        before=pdf_text(client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa')))
        with db.tx() as conn:
            conn.execute("UPDATE users SET nome='Nome alterado depois' WHERE id IN ('u-analista','second')")
            conn.execute("INSERT INTO workers (id,nome,contract_id) VALUES ('T999','Novo trabalhador','CT-001')")
        after=pdf_text(client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa')))
        assert before==after and 'Segunda Analista' in after and 'Nome alterado depois' not in after
        assert preview(client,rid)['conteudo_json']==checked['conteudo_json']


def test_edit_invalidates_previous_preview_and_published_is_immutable(banco):
    with TestClient(app) as client:
        rid=create(client)
        old=preview(client,rid)
        patch={'recomendacoes':'Solicitar documentação complementar.','conteudo_sha256':old['conteudo_sha256']}
        assert client.patch(f'/api/reports/{rid}',headers=headers(),json=patch).status_code==200
        assert publish(client,rid,old).status_code==409
        assert client.patch(f'/api/reports/{rid}',headers=headers(),json=patch).status_code==409
        checked=preview(client,rid)
        assert checked['conteudo_sha256']!=old['conteudo_sha256']
        assert checked['conteudo_json']['recomendacoes']==['Solicitar documentação complementar.']
        assert client.get(f'/api/reports/{rid}/pdf?conteudo_sha256='+old['conteudo_sha256'],headers=headers()).status_code==409
        assert publish(client,rid,checked).status_code==200
        assert client.patch(f'/api/reports/{rid}',headers=headers(),json={**patch,'conteudo_sha256':checked['conteudo_sha256']}).status_code==409


def test_changed_data_blocks_export_and_publication_until_new_preview(banco):
    with TestClient(app) as client:
        rid=create(client)
        assert client.get(f'/api/reports/{rid}/pdf',headers=headers()).status_code==422
        checked=preview(client,rid)
        with db.tx() as conn: conn.execute("INSERT INTO workers (id,nome,contract_id) VALUES ('T999','Novo','CT-001')")
        assert publish(client,rid,checked).status_code==409
        assert client.get(f'/api/reports/{rid}/pdf?conteudo_sha256='+checked['conteudo_sha256'],headers=headers()).status_code==409
        fresh=preview(client,rid)
        assert publish(client,rid,fresh).status_code==200


@pytest.mark.parametrize('user',['u-admin','u-gestor-beta','u-oper-beta','u-oper-gama','platform'])
def test_forbidden_roles_cannot_export_or_edit(banco,user):
    with db.tx() as conn:
        if user=='platform': user=conn.execute('SELECT id FROM platform_accounts LIMIT 1').fetchone()[0]
    with TestClient(app) as client:
        rid=create(client)
        checked=preview(client,rid)
        assert client.get(f'/api/reports/{rid}/pdf',headers=headers(user)).status_code==403
        assert client.patch(f'/api/reports/{rid}',headers=headers(user),json={'recomendacoes':'x','conteudo_sha256':checked['conteudo_sha256']}).status_code==403


def test_contractor_only_downloads_current_published_own_contract(banco):
    with db.tx() as conn:
        conn.execute("INSERT INTO organizations (id,nome,tipo) VALUES ('OTHER','Outra Contratante','CONTRATANTE')")
        conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES ('other','Gestor Outro','OTHER','GESTOR_CONTR','synthetic-other-token')")
    with TestClient(app) as client:
        rid=create(client)
        assert client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa')).status_code==404
        assert publish(client,rid).status_code==200
        assert client.get(f'/api/reports/{rid}/pdf',headers=headers('other')).status_code==404
        newer=create(client)
        assert publish(client,newer).status_code==200
        assert client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa')).status_code==404
        old_pdf=pdf_text(client.get(f'/api/reports/{rid}/pdf',headers=headers()))
        assert 'VERSÃO SUBSTITUÍDA' in old_pdf


def test_large_report_pdf_paginates_and_keeps_last_worker_and_escaped_text(banco):
    with TestClient(app) as client:
        rid=create(client,recomendacoes='<b>Texto literal</b> & orientação pública.')
        report=preview(client,rid)
    content=report['conteudo_json']
    example=deepcopy(content['itens'][0])
    content['itens']=[{**example,'trabalhador_id':f'T{i:03d}','detalhe':'Conferir a documentação e os campos antes de concluir a análise.'} for i in range(120)]
    data=report_pdf.render(report,True)
    with pymupdf.open(stream=data,filetype='pdf') as doc:
        assert len(doc)>2
        text=' '.join(' '.join(page.get_text() for page in doc).split())
        assert 'T119' in text and '<b>Texto literal</b> & orientação pública.' in text
        assert f'Página {len(doc)} de {len(doc)}' in text


def test_legacy_publication_is_exported_without_inventing_author(banco):
    with TestClient(app) as client:
        rid=create(client)
        checked=preview(client,rid)
        assert publish(client,rid,checked).status_code==200
        legacy=checked['conteudo_json'];legacy.pop('parecer');legacy.pop('recomendacoes')
        with db.tx() as conn: conn.execute('UPDATE reports SET conteudo_json=? WHERE id=?',(json.dumps(legacy),rid))
        text=pdf_text(client.get(f'/api/reports/{rid}/pdf',headers=headers('u-gestor-alfa')))
        assert 'Não registrado nesta versão' in text and 'Recomendações não registradas nesta versão.' in text


def test_three_consecutive_report_publications_persist_without_artificial_wait(banco):
    with TestClient(app) as client:
        for version in (1, 2, 3):
            created = client.post('/api/reports', headers=headers(), json={
                'contract_id': 'CT-001', 'competencia': '10/2026',
                'recomendacoes': f'Recomendação sintética {version}',
            })
            assert created.status_code == 201, created.text
            rid = created.json()['id']
            with db.tx() as independent:
                row = independent.execute('SELECT status,versao FROM reports WHERE id=?', (rid,)).fetchone()
                assert row['status'] == 'RASCUNHO' and row['versao'] == version

            checked = client.get(f'/api/reports/{rid}/preview', headers=headers())
            assert checked.status_code == 200, checked.text
            sha = checked.json()['conteudo_sha256']
            with db.tx() as independent:
                cached = independent.execute(
                    'SELECT COUNT(*) FROM report_previews WHERE report_id=? AND conteudo_sha256=?',
                    (rid, sha)).fetchone()[0]
                assert cached == 1
            published = client.post(f'/api/reports/{rid}/publish', headers=headers(),
                                    json={'conteudo_sha256': sha})
            assert published.status_code == 200, published.text
            with db.tx() as independent:
                row = independent.execute(
                    'SELECT status,conteudo_json FROM reports WHERE id=?', (rid,)).fetchone()
                assert row['status'] == 'APROVADO_PUBLICADO'
                assert json.loads(row['conteudo_json']) == checked.json()['conteudo_json']
            contractor = client.get('/api/client/reports', headers=headers('u-gestor-alfa'))
            assert contractor.status_code == 200
            assert any(item['id'] == rid for item in contractor.json())
            pdf_response = client.get(f'/api/reports/{rid}/pdf', headers=headers('u-gestor-alfa'))
            assert pdf_response.status_code == 200
            assert pdf_response.content.startswith(b'%PDF')

