# D4-05 — Dependências, reprodutibilidade e supply chain (F36/F37)

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Branch | `chore/d4-05-dependency-security` (parte de `main` em `e8e5e0f`) |
| Arquivos | `api/pyproject.toml`, `api/requirements.lock` (novo), `.github/workflows/backend-tests.yml`, `.github/workflows/supply-chain.yml` (novo), `docs/dev4/sbom/*.cdx.json`, este documento |

## Gerenciadores e estado inicial

| Parte | Gerenciador | Manifesto | Lock antes |
|---|---|---|---|
| API | pip + setuptools | `api/pyproject.toml` (faixas `>=,<`) | **nenhum** — CI instalava as versões mais recentes de cada faixa |
| Web | npm | `web/package.json` | `web/package-lock.json` (v3) ✔ |

Nenhum gerenciador novo foi adicionado: `pip-tools` só gera o lock; a instalação continua via pip.

## Vulnerabilidades (pip-audit 2.10.1, npm audit)

| Pacote | Versão | Achados | Alcance no DocRisk | Classificação | Ação |
|---|---|---|---|---|---|
| **Pillow** | 12.3.0 | **39 avisos** (PYSEC-2026-4326…4343, CVE-2026-1123xx/1128xx, CVE-2026-96638/96640/96778, GHSA-78g4-xqwv-q3g8), todos corrigidos em 13.0.0 | **Alcançável**: uploads PNG/JPEG/TIFF são decodificados por `pipeline/render.py`; TIFF multipágina usa os *multi-frame loaders* (PYSEC-2026-4339) e decodificadores raw. BMP/WMF/encoder JPEG não são alcançáveis (formatos filtrados por *magic bytes*, saída é PNG) | **Alta** | `Pillow>=13,<14` (o teto `<13` impedia a correção) |
| pip | 26.1.2 | PYSEC-2026-3721 (instalador, URLs duplamente codificadas) | Só em tempo de instalação | Média | CI atualiza `pip>=26.2` antes de instalar |
| npm (web) | lock atual | **0** (info/low/moderate/high/critical = 0) | — | — | — |

Após a correção: `pip-audit -r requirements.lock --require-hashes` → **No known vulnerabilities found**.

Sugestão a Dev1 (dono de `render.py`), defesa em profundidade: `Image.open(..., formats=["PNG","JPEG","TIFF"])`
para que o Pillow nunca escolha outro plugin. Não aplicado (fora do escopo Dev4).

## Reprodutibilidade

- `api/requirements.lock`: 42 pacotes, versões exatas **com hashes** (`pip-compile --generate-hashes --extra test`).
- CI de backend: `pip install --require-hashes -r requirements.lock` + `pip install --no-deps -e .` + `pip check`.
- Instalação limpa em venv isolado (Windows, Python 3.13.14): instalou por hash, `pip check` limpo,
  **pytest 237 passed, 1 skipped** com Pillow 13.0.0. Suíte também verde no venv de desenvolvimento.
- Lock gerado no Windows/3.13; CI usa Linux/3.12 — **validação 3.12 só no CI remoto (pendente)**.
  `colorama` entra por marcador Windows e é ignorado na checagem de coerência.

## Licenças

Python (44): MIT, BSD, Apache-2.0, MPL-2.0 (certifi), PSF, MIT-CMU (Pillow) — e
**PyMuPDF: AGPL-3.0 ou licença comercial Artifex**. Para protótipo/hackathon com código público não
há conflito; **para piloto oferecido pela rede (D4-06) a AGPL exige disponibilizar o código-fonte
da aplicação aos usuários ou adquirir licença comercial — decisão humana necessária.**
O repositório **não tem arquivo LICENSE** — decisão humana necessária.

npm (61 no lock): MIT, Apache-2.0, ISC, BSD, 0BSD; LGPL-3.0 nos binários opcionais `@img/sharp-*`
(otimização de imagem do Next em servidor; não usados nem distribuídos no export estático);
CC-BY-4.0 em `caniuse-lite` (dados, atribuição).

## SBOM (CycloneDX)

- `docs/dev4/sbom/api-python.cdx.json` — CycloneDX 1.6, 44 componentes (venv limpo do lock).
- `docs/dev4/sbom/web-prod.cdx.json` — CycloneDX 1.5, 25 componentes (`npm sbom --omit dev`).

## CI de supply chain (`.github/workflows/supply-chain.yml`)

- Em PR que altere manifestos/locks, semanalmente (segunda 09:00 UTC) e manual.
- Python: lock coerente com `pyproject.toml` (regera e compara) + `pip-audit` **falhando em qualquer achado**.
- Web: `npm ci --ignore-scripts` (lock íntegro) + `npm audit --omit=dev --audit-level=high` bloqueante;
  relatório completo com dev é informativo.
- Exceções: só com análise registrada aqui e `--ignore-vuln <ID>` explícito no workflow.

## Política de atualização

1. Segurança alta/crítica alcançável: corrigir em até 2 dias úteis, PR próprio com testes completos.
2. Demais: lote quinzenal; atualizar faixa no `pyproject.toml`, `pip-compile --generate-hashes ...`, rodar suíte.
3. Majors (ex.: Pillow 14, Next 17): PR isolado, smoke front + backend, aprovação do dono do componente.
4. Nunca editar `requirements.lock` à mão; nunca `--no-verify`/`|| true` em passo bloqueante.

```bash
cd api
pip-compile --generate-hashes --extra test --strip-extras --allow-unsafe -o requirements.lock pyproject.toml
```

## Status: PARCIAL

Instalação reproduzível, lock com hashes, scans executados e classificados, licenças avaliadas,
SBOM e política definidos; vulnerabilidade alta corrigida. Pendentes: CI remoto (Linux/3.12) e
decisões humanas sobre AGPL/PyMuPDF e LICENSE do repositório.

## Reconciliação Codex — 2026-11-06
Base a1f6109; backup backup/d4-05-20261106 (dcb749f); rebase sem conflitos.
Lock regenerado com PyJWT[crypto] da autenticação Clerk; Pillow 13 preservado.
Ambiente isolado novo .venv-dev4, Windows/Python 3.13.14/Node 22.23.2.
piptools compile --generate-hashes --extra test --strip-extras --allow-unsafe;
pip install --require-hashes -r api/requirements.lock aprovado.
pip-audit --require-hashes --disable-pip: nenhuma vulnerabilidade conhecida.
npm ci / npm audit: zero vulnerabilidades. SBOMs Python e web regenerados.
pytest api/tests -q: 370 aprovados, 1 ignorado (98,75s).
TypeScript, compileall e diff --check aprovados. Não existe LICENSE na base.
Avaliação/licenciamento PyMuPDF e licença do projeto continuam pendentes de decisão.
Status: PARCIAL (validação local aprovada; licenças e CI Linux pendentes).
