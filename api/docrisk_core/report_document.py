"""Documento corporativo: dados públicos e cópia exata da prévia conferida."""
import hashlib
import json
from . import db
from .rules import parecer


def content_hash(content):
    # Mantém o contrato D2-08: a passagem do tempo não invalida a conferência.
    checked = {k: v for k, v in content.items() if k != 'gerado_em'}
    canonical = json.dumps(checked, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def editorial(conn, report_id):
    row = conn.execute('SELECT recomendacoes FROM report_editorial WHERE report_id=?', (report_id,)).fetchone()
    return row[0] if row else ''


def suggestions(summary):
    result = []
    if summary.get('com_divergencia', 0):
        result.append('Conferir as diferenças de horas extras com a fornecedora, incluindo compensações, banco de horas e competência de pagamento.')
    if any(summary.get(key, 0) for key in ('bloqueados','em_revisao','aguardando_documentos','dados_insuficientes')):
        result.append('Completar a documentação e concluir a revisão dos casos não avaliados ou com dados insuficientes antes de concluir a conferência.')
    if not result:
        result.append('Manter a conferência documental das competências seguintes. O resultado se limita ao escopo e aos campos comparados.')
    return result


def current_content(conn, report, user):
    content = parecer.snapshot_parecer(conn, report['contract_id'], report['competencia'])
    author = conn.execute('SELECT id,nome FROM users WHERE id=?', (report['autor_id'],)).fetchone()
    auditor = conn.execute('SELECT o.nome FROM contracts c JOIN organizations o ON o.id=c.bernhoeft_id WHERE c.id=?', (report['contract_id'],)).fetchone()
    content['parecer'] = {
        'id': report['id'], 'versao': report['versao'],
        'autor': dict(author) if author else {'id': report['autor_id'] or '', 'nome': 'Não registrado'},
        'responsavel': {'id': user.id, 'nome': user.nome},
        'emissor': auditor[0] if auditor else 'Não registrado',
    }
    text = editorial(conn, report['id'])
    content['recomendacoes'] = [line.strip() for line in text.splitlines() if line.strip()] or suggestions(content.get('resumo', {}))
    return content


def cache_preview(conn, report, user):
    content = current_content(conn, report, user)
    sha = content_hash(content)
    # Duas abas com o mesmo conteúdo recebem a mesma prévia, inclusive o horário.
    conn.execute('INSERT OR IGNORE INTO report_previews (report_id,user_id,conteudo_sha256,conteudo_json,created_at) VALUES (?,?,?,?,?)',
                 (report['id'],user.id,sha,json.dumps(content,ensure_ascii=False),db.agora()))
    row = conn.execute('SELECT conteudo_json FROM report_previews WHERE report_id=? AND user_id=? AND conteudo_sha256=?',
                       (report['id'],user.id,sha)).fetchone()
    return json.loads(row[0]), sha
