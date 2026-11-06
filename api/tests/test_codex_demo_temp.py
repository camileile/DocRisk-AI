import time
from pathlib import Path
from fastapi.testclient import TestClient
from docrisk_core.api import app
from test_f2_worker import banco
from test_f3_regras import _enviar, _analises, _h

def test_actual_demo(banco):
    root = Path(__file__).resolve().parents[1] / 'scripts/lote_demo'
    with TestClient(app) as c:
        for _ in range(2):
            r = _enviar(c, root / 'lote_demo.pdf')
            assert r.status_code == 202, r.text
            a = _analises(c)
            assert a['T001']['resultado']['tipo'] == 'DIVERGENCIA_A_VERIFICAR'
            assert a['T001']['resultado']['diferenca_h'] == 4
            assert a['T004']['resultado']['tipo'] == 'DADOS_INSUFICIENTES'
            assert a['T005']['resultado']['tipo'] == 'SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS'
            assert all(a[t]['status'] == 'BLOQUEADA_PENDENCIA' for t in ('T002','T003'))
        issues = c.get('/api/issues', headers=_h('u-analista')).json()
        t2 = next(i for i in issues if i['worker_id'] == 'T002' and i['status'] != 'RESOLVIDA')
        assert t2['categoria'] == 'ILEGIVEL'
        assert any(i['worker_id']=='T003' and i['categoria']=='PAGINA_FALTANTE' for i in issues)
        with (root / 'reenvio_holerite_T002.pdf').open('rb') as f:
            r = c.post(f"/api/issues/{t2['id']}/resubmit", headers=_h('u-oper-beta'), files={'file':('reenvio.pdf',f,'application/pdf')})
        assert r.status_code == 202, r.text
        assert _analises(c)['T002']['resultado']['tipo'] == 'SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS'
        r = c.post('/api/reports',headers=_h('u-analista'),json={'contract_id':'CT-001','competencia':'10/2026'})
        rid=r.json()['id']
        preview=c.get(f'/api/reports/{rid}/preview',headers=_h('u-analista')).json()
        time.sleep(1.2)
        r=c.post(f'/api/reports/{rid}/publish',headers=_h('u-analista'),json={'conteudo_sha256':preview['conteudo_sha256']})
        assert r.status_code==200,r.text

