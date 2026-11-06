"""PDF corporativo a partir do snapshot público; não consulta OCR nem observações internas."""
from html import escape
from io import BytesIO
from pathlib import Path
import pymupdf

ASSETS = Path(__file__).with_name('assets')
SUMMARY = [('trabalhadores','Trabalhadores no contrato'),('avaliados','Avaliados'),
           ('com_divergencia','Com divergência a verificar'),('dados_insuficientes','Dados insuficientes'),
           ('sem_divergencia','Sem divergência nos campos comparados'),('bloqueados','Bloqueados por pendência documental'),
           ('em_revisao','Em revisão humana'),('aguardando_documentos','Aguardando documentos')]
RESULTS = {'NAO_AVALIADO':'Não avaliado','DADOS_INSUFICIENTES':'Dados insuficientes',
           'DIVERGENCIA_A_VERIFICAR':'Divergência a verificar',
           'SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS':'Sem divergência nos campos comparados',
           'AGUARDANDO_DOCUMENTOS':'Aguardando documentos','BLOQUEADA_PENDENCIA':'Bloqueada por pendência',
           'REVISAO_HUMANA':'Em revisão humana'}
TYPES = {'ESPELHO_PONTO':'Espelho de ponto','HOLERITE':'Holerite','COMPROVANTE_PAGAMENTO':'Comprovante de pagamento'}
CSS = '''
@font-face {font-family: DocRiskBody; src: url(fonts/DMSans-Regular.ttf);}
@font-face {font-family: DocRiskBody; src: url(fonts/DMSans-Bold.ttf); font-weight: bold;}
@font-face {font-family: DocRiskHeading; src: url(fonts/Sora-Regular.ttf);}
@font-face {font-family: DocRiskHeading; src: url(fonts/Sora-Bold.ttf); font-weight: bold;}
body {font-family: DocRiskBody; font-size: 10pt; color: #27223d; line-height: 1.45;}
h1,h2,h3 {font-family: DocRiskHeading; color: #3730a3;}
h1,h2,h3 {page-break-after: avoid;} .worker-lead {page-break-inside: avoid;}
h1 {font-size: 20pt;} h2 {font-size: 14pt; margin-top: 18pt;} h3 {font-size: 11pt; margin-top: 13pt;}
p {margin: 6pt 0;} .flag {background-color: #ede9fe; padding: 8pt; color: #4c1d95;}
table {width: 100%; border-collapse: collapse;} td {border-bottom: 1px solid #ddd6fe; padding: 5pt;}
.small {font-size: 9pt; color: #554b69;}
'''


def text(value):
    return escape(str(value if value is not None else 'Não informado'))


def hours(value):
    if value is None:
        return 'Não informado'
    return f'{value:g} h'.replace('.', ',')


def evidence(item):
    label = TYPES.get(item.get('tipo'),item.get('tipo','Documento'))
    suffix = f"AEJ vínculo {item.get('vinculo_aej')}, linhas {','.join(map(str,item.get('linhas_origem',[])))}" if item.get('origem')=='AEJ' else 'p. '+','.join(map(str,item.get('paginas',[])))
    return f"{label} v{item.get('versao')} (lote {item.get('lote')}, {suffix})"


def render(report, draft=False):
    content = report['conteudo_json']
    if not isinstance(content,dict) or 'resumo' not in content:
        raise ValueError('Parecer sem conteúdo documental para exportação.')
    identity = content.get('parecer') or {}
    status = 'PRÉVIA DO RASCUNHO — não publicada' if draft else ('VERSÃO SUBSTITUÍDA — histórico' if report['status']=='SUBSTITUIDO_POR_VERSAO' else 'PARECER PUBLICADO')
    sections = ['<img src="logo-horizontal-claro.png" width="190" alt="DocRisk AI">',
                '<p class="flag">'+text(status)+'</p>',
                '<h1>Parecer documental</h1>',
                f"<p>Parecer #{report['id']} · versão {report['versao']} · competência {text(content.get('competencia'))}</p>",
                '<h2>'+text((content.get('contrato') or {}).get('nome'))+'</h2>',
                '<p>Contratante: '+text(content.get('contratante'))+'<br>Fornecedora: '+text(content.get('fornecedora'))+'</p>',
                '<p>Organização responsável: '+text(identity.get('emissor','Não registrada nesta versão'))+'<br>Autor: '+text((identity.get('autor') or {}).get('nome','Não registrado nesta versão'))+'<br>Responsável pela conferência: '+text((identity.get('responsavel') or {}).get('nome','Não registrado nesta versão'))+'</p>',
                '<p class="small">Regra: '+text(content.get('regra'))+' · Prévia gerada em: '+text(content.get('gerado_em'))+'</p>',
                '<h2>Escopo</h2><p>'+text(content.get('escopo'))+'</p>',
                '<h2>Resumo</h2><table>'+''.join('<tr><td>'+label+'</td><td>'+text(content['resumo'].get(key,0))+'</td></tr>' for key,label in SUMMARY)+'</table>',
                ]
    recommendations = content.get('recomendacoes') or ['Recomendações não registradas nesta versão.']
    sections.append('<h2>Recomendações</h2><ul>'+''.join('<li>'+text(line)+'</li>' for line in recommendations)+'</ul>')
    for index,item in enumerate(content.get('itens',[])):
        state = item.get('resultado') if item.get('situacao')=='ANALISADA' else item.get('situacao')
        sections.append('<div class="worker-lead">'+('<h2>Por trabalhador</h2>' if index==0 else '')+'<h3>Trabalhador '+text(item.get('trabalhador_id'))+' · '+text(RESULTS.get(state,state))+'</h3>'+
                        '<p>Ponto: '+text(hours(item.get('horas_ponto')))+' · Holerite: '+text(hours(item.get('horas_folha')))+' · Diferença: '+text(hours(item.get('diferenca_h')))+'</p></div>'+
                        '<p>'+text(item.get('detalhe',''))+'</p><p class="small">Evidências: '+text('; '.join(evidence(e) for e in item.get('evidencias',[])) or 'Não informadas')+'</p>')
    sections.append('<h2>Limitações</h2><ul>'+''.join('<li>'+text(line)+'</li>' for line in content.get('limitacoes',[]))+'</ul>')
    # Grupos curtos (título + conteúdo) passam juntos à página seguinte.
    # Blocos longos continuam em várias páginas, sem cortar trabalhadores/limitações.
    header = ''.join(sections[:8])
    blocks = [header,*sections[8:]]
    output = BytesIO()
    writer = pymupdf.DocumentWriter(output)
    device = None
    page_count = 0
    y = 36
    def new_page():
        nonlocal device,page_count,y
        if device is not None:
            writer.end_page()
        page_count += 1
        if page_count > 1000:
            raise ValueError('O parecer excede o limite de paginação do exportador.')
        device = writer.begin_page(pymupdf.Rect(0,0,595,842))
        y = 36
    archive = pymupdf.Archive(str(ASSETS))
    try:
        new_page()
        for block in blocks:
            story = pymupdf.Story(html=block,user_css=CSS,archive=archive)
            more,filled = story.place(pymupdf.Rect(42,y,553,792))
            if more and y > 36:
                new_page()
                story = pymupdf.Story(html=block,user_css=CSS,archive=archive)
                more,filled = story.place(pymupdf.Rect(42,y,553,792))
            while True:
                story.draw(device)
                y = pymupdf.Rect(filled).y1 + 3
                if not more:
                    break
                new_page()
                more,filled = story.place(pymupdf.Rect(42,y,553,792))
        writer.end_page()
    finally:
        writer.close()
    doc = pymupdf.open(stream=output.getvalue(),filetype='pdf')
    for index,page in enumerate(doc):
        page.insert_font(fontname='DocRiskBody',fontfile=str(ASSETS/'fonts/DMSans-Regular.ttf'))
        page.insert_text((42,816),f'DocRisk AI | Parecer #{report["id"]} v{report["versao"]} | Página {index+1} de {len(doc)}',fontname='DocRiskBody',fontsize=8,color=(.3,.24,.43))
    doc.set_metadata({'title':f'Parecer DocRisk AI #{report["id"]} v{report["versao"]}',
                      'author':(identity.get('autor') or {}).get('nome','DocRisk AI'),
                      'subject':status,'keywords':'parecer, DocRisk AI'})
    data = doc.tobytes(garbage=4,deflate=True)
    doc.close()
    return data
