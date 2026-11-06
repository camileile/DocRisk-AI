"""Benchmark reproduzível do lote_100 com o leitor determinístico textlayer."""
from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
os.environ["AI_PROVIDER"] = "textlayer"

import pymupdf as fitz

from docrisk_core import config, db
from docrisk_core.auth import Usuario
from docrisk_core.contracts import Papel
from docrisk_core.pipeline import worker
from gerar_lote_demo import gerar_parametrizado


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="docrisk-benchmark-") as tmp:
        raiz = Path(tmp)
        os.environ["DOCRISK_DATA_DIR"] = str(raiz / "data")
        config.DATA_DIR = raiz / "data"
        config.DB_PATH = config.DATA_DIR / "docrisk.sqlite"
        config.UPLOAD_DIR = config.DATA_DIR / "uploads"
        config.PAGES_DIR = config.DATA_DIR / "pages"
        db.init_db()
        with db.tx() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO workers (id, nome, contract_id) VALUES (?, ?, ?)",
                [(f"T{i:03d}", f"Trabalhador Fictício {i:03d}", "CT-001") for i in range(6, 101)],
            )
        pasta = raiz / "lote_100"
        arquivos = gerar_parametrizado(100, pasta)
        gabarito = json.loads(arquivos["gabarito.json"].read_text(encoding="utf-8"))
        pdf = arquivos["lote_100.pdf"].read_bytes()
        pdf_doc = fitz.open(stream=pdf, filetype="pdf")
        try:
            if pdf_doc.page_count != 300:
                raise RuntimeError("O PDF não contém 300 páginas.")
        finally:
            pdf_doc.close()

        tempos = {"segmentacao": 0.0, "conciliacao": 0.0}
        segmentar_original, conciliar_original = worker.segmentar, worker.f3.conciliar

        def medir_segmentacao(*args, **kwargs):
            inicio = time.perf_counter()
            try:
                return segmentar_original(*args, **kwargs)
            finally:
                tempos["segmentacao"] += time.perf_counter() - inicio

        def medir_conciliacao(*args, **kwargs):
            inicio = time.perf_counter()
            try:
                return conciliar_original(*args, **kwargs)
            finally:
                tempos["conciliacao"] += time.perf_counter() - inicio

        worker.segmentar = medir_segmentacao
        worker.f3.conciliar = medir_conciliacao
        inicio = time.perf_counter()
        lote_id = worker.criar_lote(Usuario(id="u-oper-beta", nome="Benchmark", org_id="ORG-BETA",
                                             org_tipo="FORNECEDORA", papel=Papel.OPERADOR_FORN),
                                    "CT-001", "lote_100.pdf", pdf)
        worker.processar_lote(lote_id)
        decorrido = time.perf_counter() - inicio
        with db.tx() as conn:
            lote = conn.execute("SELECT status, erro, total_pages FROM batches WHERE id=?", (lote_id,)).fetchone()
            docs = conn.execute(
                "SELECT d.tipo, d.worker_id, d.competencia, d.status, GROUP_CONCAT(p.ordem) AS paginas "
                "FROM documents d JOIN doc_pages dp ON dp.document_id=d.id JOIN pages p ON p.id=dp.page_id "
                "WHERE d.batch_id=? GROUP BY d.id ORDER BY MIN(p.ordem)", (lote_id,)).fetchall()
            analyses = {r["worker_id"]: (r["status"], json.loads(r["resultado_json"]))
                        for r in conn.execute("SELECT worker_id,status,resultado_json FROM analyses WHERE atual=1")}
            page_states = conn.execute("SELECT COUNT(*), SUM(status='OK') FROM pages WHERE batch_id=?", (lote_id,)).fetchone()

        if lote["status"] != "CONCLUIDO" or page_states[0] != 300 or page_states[1] != 300:
            raise RuntimeError(f"Lote não concluiu: status={lote['status']}, erro={lote['erro']}")
        esperado_por_pag = {p: d for d in gabarito["documentos"] for p in d["paginas"]}
        encontrado_por_pag = {}
        fronteiras = tipos = 0
        for d in docs:
            paginas = sorted(int(x) for x in d["paginas"].split(","))
            esperado = esperado_por_pag[paginas[0]]
            fronteiras += paginas == esperado["paginas"]
            tipos += d["tipo"] == esperado["tipo"]
            for p in paginas:
                encontrado_por_pag[p] = d["tipo"]
        conciliacoes = sum(
            t in analyses and analyses[t][0] == esperado["status"] and
            analyses[t][1]["tipo"] == esperado["resultado"]
            for t, esperado in gabarito["conciliacao"].items()
        )
        if (fronteiras != len(gabarito["documentos"]) or
                tipos != len(gabarito["documentos"]) or
                conciliacoes != len(gabarito["conciliacao"])):
            raise RuntimeError(
                f"Divergência com gabarito: fronteiras {fronteiras}/{len(gabarito['documentos'])}, "
                f"tipos {tipos}/{len(gabarito['documentos'])}, "
                f"conciliações {conciliacoes}/{len(gabarito['conciliacao'])}."
            )
        # Render padrão: 595x842 pt a 150 DPI = aprox. 1240x1754 px.
        # Fórmula publicada pelo Google: crop=floor(min(lado)/1,5), 258 tokens/crop.
        largura, altura = 595 * 150 / 72, 842 * 150 / 72
        crop = int(min(largura, altura) // 1.5)
        tiles = int(-(-largura // crop)) * int(-(-altura // crop))
        tokens_imagem = tiles * 258
        preco_milhao = 1.50  # Gemini 3.5 Flash, input padrão, USD/1M tokens
        custo_pagina = tokens_imagem * preco_milhao / 1_000_000
        custo_lote = custo_pagina * 300
        paginas_min = 300 / (decorrido / 60)
        media = decorrido / 300
        pct = lambda n, total: f"{100*n/total:.1f}% ({n}/{total})"
        conteudo = f"""# Benchmark TextLayer do lote de 100 trabalhadores

## Escopo e amostra

- Medido: processamento local com `AI_PROVIDER=textlayer`; não houve chamada ao Gemini.
- Amostra: lote totalmente sintético, gerado por `gerar_parametrizado`; semente {gabarito['semente']}.
- Distribuição: {json.dumps(gabarito['distribuicao'], ensure_ascii=False, sort_keys=True)}.
- Uso correto: medição de vazão local e conferência contra o gabarito gerado para este lote.
- Limite: os acertos neste conjunto sintético não medem precisão visual nem generalização para documentos reais.

## Execução

- Data: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
- Leitor: `textlayer` (determinístico, sem chamadas de IA remotas)
- Ambiente: Python {platform.python_version()}, {platform.platform()}, processador `{platform.processor() or 'não informado'}`
- Lote: 300 páginas, 100 trabalhadores, 300 documentos; status `{lote['status']}`
- Tempo total medido: {decorrido:.2f} s
- Vazão: {paginas_min:.1f} páginas/min
- Tempo médio: {media*1000:.1f} ms/página
- Segmentação: {tempos['segmentacao']*1000:.1f} ms
- Conciliação: {tempos['conciliacao']*1000:.1f} ms
- Páginas lidas sem erro: {page_states[1]}/{page_states[0]}

## Acurácia contra `gabarito.json`

- Fronteiras de documento exatas: {pct(fronteiras, len(gabarito['documentos']))}
- Tipos de documento: {pct(tipos, len(gabarito['documentos']))}
- Conciliação (status e resultado): {pct(conciliacoes, len(gabarito['conciliacao']))}

## Estimativa de custo Gemini (não medida)

- Resolução de renderização: aproximadamente {int(largura)}×{int(altura)} px (150 DPI)
- Tokens visuais estimados: {tokens_imagem} por página ({tiles} blocos × 258 tokens)
- Modelo/preço: Gemini 3.5 Flash, entrada padrão, US$ {preco_milhao:.2f}/1M tokens
- Estimativa: US$ {custo_pagina:.6f}/página; US$ {custo_lote:.4f}/300 páginas
- A estimativa inclui apenas tokens visuais; prompt e saída JSON não estão incluídos. Não é resultado de execução do Gemini. Preço e regra visual consultados em 2026-11-06 na [tabela oficial](https://ai.google.dev/gemini-api/docs/pricing) e na [documentação de tokens de imagem](https://ai.google.dev/gemini-api/docs/tokens).

## Reprodução

```powershell
cd api
python scripts/benchmark.py
```

O benchmark falha com exceção se o PDF não tiver 300 páginas, se houver erro de leitura ou se o lote não chegar a `CONCLUIDO`.
"""
        destino = API_DIR.parent / "docs" / "BENCHMARK.md"
        destino.write_text(conteudo, encoding="utf-8")
        print(conteudo)
        print(f"Resultado salvo em {destino}")


if __name__ == "__main__":
    main()
