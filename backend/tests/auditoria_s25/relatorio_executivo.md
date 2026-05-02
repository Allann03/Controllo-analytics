# Relatorio Executivo — S25 Inventario Arquitetural

**Branch**: `refactor/arquitetura-estrutural` (criada sobre `528c5cb` — S24 Stone)
**Data**: 2026-05-02
**Modo**: read-only sobre codigo de producao; producao apenas em `backend/tests/auditoria_s25/`.

## §1 Sumario Executivo

A S25 mapeou exaustivamente o backend (~21.575 linhas em ~133 arquivos)
para informar a refatoracao arquitetural das proximas 13 sessoes. Sem
alterar codigo de producao, validamos:

- **Dead code**: 6 arquivos / 588 linhas DEAD CONFIRMED via pytest;
  +727 linhas em pares (Grupo B sub-A) confirmaveis em S26;
  +~989 linhas servico bloqueadas por decisao de produto (S35.5 WIP).
- **Duplicacoes**: 25 funcoes mesmo nome, 14 arquivos com `_ZERO`,
  11 com `TOLERANCIA_VALOR`, 7 parsers com `_RE_ANO` — todos extraiveis.
- **Monolitos**: `main.py` (3.010 linhas) e `extrator_pdf.py` (1.747)
  serao decompostos em S30 e S32.
- **Resultado**: refator cabe em **13 sessoes** (S26 a S35.5), reducao
  estimada de **9-13%** do backend (1.860 a 2.875 linhas), zero imports
  circulares ja hoje, pytest baseline (912/1/1/2) preservado nas 13
  execucoes da Fase 3.

## §2 Metricas finais consolidadas

| Metrica | Valor |
| --- | --- |
| Arquivos `.py` mapeados (recorte producao) | 133 |
| Arquivos `.py` mapeados (recorte completo, com tests) | 187 |
| Linhas backend (producao) | ~21.575 |
| Arestas internas — recorte producao | 257 |
| Arestas internas — recorte completo | 367 |
| Imports circulares | **0** (em ambos recortes) |
| Imports dinamicos rastreaveis em modulos internos | **0** (verificado) |
| Pytest baseline | 912 passed / 1 failed (zxcvbn flaky) / 1 skipped / 2 errors (pagbank pre-existentes) |

### Top 5 arquivos por in-degree (recorte producao) — pontos de acoplamento alto

| # | Arquivo | in-degree |
| --- | --- | --- |
| 1 | `services/parsers/base.py` | 28 |
| 2 | `services/contabil/core.py` | 18 |
| 2 | `data/database/models.py` | 18 |
| 4 | `data/database/__init__.py` | 17 |
| 5 | `data/database/config.py` | 16 |

### Top 5 arquivos por out-degree — monolitos a decompor

| # | Arquivo | out-degree | Linhas | Sessao alvo |
| --- | --- | --- | --- | --- |
| 1 | `services/extrator_pdf.py` | 30 | 1.747 | **S30** |
| 2 | `main.py` | 29 | 3.010 | **S32** |
| 3 | `services/conciliacao/matchers/__init__.py` | 13 | 20 | (registry — ok) |
| 4 | `routers/financeiro.py` | 9 | 634 | S32 |
| 5 | `routers/conciliacao.py` | 7 | 385 | S32 |

## §3 Dead code consolidado

### §3.1 GRUPO A — DEAD CONFIRMED (validado por pytest)

| Arquivo | Linhas | Veredito |
| --- | --- | --- |
| `backend/core/config.py` | 0 | DEAD CONFIRMED |
| `backend/services/parsers/itau_extrato_mensal.py` | 245 | DEAD CONFIRMED |
| `backend/services/parsers/parser_generico.py` | 77 | DEAD CONFIRMED |
| `backend/services/parsers/parser_itau_mensal.py` | 54 | DEAD CONFIRMED |
| `backend/services/parsers/parser_stone.py` | 49 | DEAD CONFIRMED (validacao manual) |
| `backend/test_parsers.py` | 163 | DEAD CONFIRMED |
| **TOTAL GRUPO A** | **588** | |

### §3.2 GRUPO B sub-A — RAMO INTEIRO MORTO (a validar em pares na S26)

| Arquivo + Teste | Linhas |
| --- | --- |
| `services/categorias.py` (`aplicar_categorias` duplicada em `extrator_pdf.py:1648`) + `tests/test_categorias.py` | 398 + 38 |
| `services/contabil/comparador.py` (endpoint nao usa) + porcao de `test_comparador_indicadores_score.py` | 191 + ~100 |
| **TOTAL sub-A** | **~727** |

### §3.3 GRUPO B sub-C — WIP NAO INTEGRADO (decisao Allan — S35.5)

5 arquivos em `services/contabil/`: `dfc.py`, `difal.py`, `icms_st.py`, `retencoes.py`, `score_saude.py` — implementacoes contabeis-fiscais completas, validadas por testes, **mas sem endpoint que as exponha** e **sem feature flag** que as ative (verificado por grep: zero matches em `CONTROLLO_DRE_ENGINE`/`CONTROLLO_LP_ENGINE`).

| Tipo | Linhas |
| --- | --- |
| Servicos | ~989 (340 + 136 + 108 + 138 + 267) |
| Testes correspondentes | ~1.100 (porcoes de `test_dfc.py`, `test_retencoes_difal_st.py`, `test_comparador_indicadores_score.py`) |

**Decisao pendente**: ativar (qual endpoint?) ou remover.

### §3.4 Anomalias adicionais a validar na S26

- **`backend/tests_fase2/`** (`conftest_setup.py` + `validar_completo.py`) — orfaos isolados (in=0 e out=0) no recorte completo. Aplicar mesmo protocolo `.disabled` + pytest na S26. Se confirmado DEAD, **deletar a pasta inteira** junto com Grupo A.
- **`backend/tests/diagnostico_parsers.py`** e **`tests/expectativas_extratos.py`** — isolados no recorte completo. Validar similar.

### §3.5 Total potencial de remocao

| Marco | Linhas removiveis |
| --- | --- |
| S26 (GRUPO A confirmado) | 588 |
| S26 (sub-A confirmado em pares) | +727 |
| S26 (tests_fase2/, diagnostico_parsers, expectativas — se confirmados) | +~50 |
| S35.5 cenario A (REMOVER WIP) | +~989 servico + ~1.100 testes |
| **Maximo absoluto** | **~3.450 linhas** |

## §4 Duplicacoes mapeadas (Fase 4)

### §4.1 Helpers numericos (extracoes mecanicas — baixo risco)

| Caso | Arquivos | Acao | Sessao |
| --- | --- | --- | --- |
| `_to_dec` (helper Decimal, **CORPO IDENTICO** em 2 e variacoes em outros 2) | `motor_narrativa.py`, `score_saude.py`, `financeiro_service.py`, `scripts/validacao_paralela_dre.py` | EXTRAIR para `domain/converters.py` | S33 |
| `_to_float` (**CORPO IDENTICO**) | `gerador_excel.py:47-52`, `gerador_excel_contabil.py:48-53` | EXTRAIR para `services/exportacao/_utils.py` | S34 |
| `_pct`, `_pct_safe`, `_safe`, `_variacao`, `_div_safe` | `financeiro_service.py`, `insights_engine.py`, `routers/orcamento.py` | EXTRAIR para `services/contabil/_aritmetica_segura.py` | S33-S34 |

### §4.2 Constantes contabeis e tributarias

| Constante | Arquivos | Acao | Sessao |
| --- | --- | --- | --- |
| `_ZERO = Decimal("0")` | **14** arquivos `services/contabil/` | EXTRAIR para `contabil/core.py` | pos-S35.5 |
| `_TOL = money_fiscal("0.01")` | 7 arquivos `contabil/` | EXTRAIR | pos-S35.5 |
| `_TOL = money("0.01")` | 3 arquivos `contabil/` | EXTRAIR | pos-S35.5 |
| `TOLERANCIA_VALOR = Decimal('0.02')` | **11** matchers `conciliacao/` | EXTRAIR para `matchers/base.py` (in-degree 13) | **S29** |
| `_TETO_SIMPLES = Decimal("4800000")`, `ALIQUOTA_IRPJ`, etc | 2-3 arquivos `contabil/` | EXTRAIR para `tabelas/limites.py` | pos-S35.5 |

### §4.3 Regex em parsers (extracoes para `parsers/base.py` — in-degree 28)

| Regex | Arquivos | Acao | Sessao |
| --- | --- | --- | --- |
| `re.compile(r'\b(20\d{2})\b')` | **7** parsers | EXTRAIR para `base.py` | **S27** |
| `re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')` | 3 parsers de empresa | EXTRAIR para `_empresa_base.py` | **S27.5** |
| `re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')` | 3 parsers | EXTRAIR para `base.py` | S27 |
| `re.compile(r'^\d{2}/\d{2}/\d{4}$')` | 3 lugares (main.py + 2 parsers) | UNIFICAR — ja em `base.py:36` | S27 |

### §4.4 Cluster parsers de empresa (achado central da Fase 4)

4 parsers (`bradesco_net_empresas`, `btg`, `n2/itau_n2`, `santander_empresas_v1`) compartilham:
- 4 blocos identicos de 11 linhas cada
- 3 helpers privados (`_e_linha_skip`, `_limpar_descricao`, `_normalizar_float`)
- 2 regex (`_RE_VALOR`, `_RE_TRAILING_INTS`)
- 1 regex `_RE_DATA_LINHA` em 2 deles

**Acao**: criar `services/parsers/_empresa_base.py` em **S27.5** — reduz **~120 linhas** sem perda de funcionalidade.

### §4.5 Endpoints duplicados main.py vs routers/

| Endpoint | main.py | router |
| --- | --- | --- |
| `aprovar_usuario` | `main.py:1190` | `routers/master.py:443` |
| `excluir_usuario` | `main.py:1296` | `routers/master.py:512` |
| `criar_empresa` | `main.py:2525` | `routers/empresas.py:232` |
| `atualizar_empresa` | `main.py:2592` | `routers/empresas.py:292` |

Mais bloco identico em `main.py:2425-2435` vs `routers/empresas.py:201-211` — sintoma de refator parcial. Resolvido em **S32** (decompor main.py). Reducao: ~150-200 linhas.

### §4.6 Auth helpers triplicados

`get_current_user`, `get_gestor_or_admin`, `_get_user`, `_get_admin` aparecem em:
- `services/auth_utils.py` (versao oficial, in-degree=12)
- `main.py:818`
- `routers/equipe.py:28-58`, `routers/auditoria.py:24`, `routers/empresas.py:33,495`

**Acao**: consolidar em `services/auth_utils.py` durante S32. ~40-60 linhas.

## §5 Estrutura nova proposta (resumo)

```
backend/
├── app/                    # FastAPI bootstrap (S32 — ex-main.py)
├── api/v1/                 # endpoints HTTP (ex-routers + endpoints de main.py)
├── domain/                 # models/ + schemas/ + converters.py + enums.py
├── services/
│   ├── extracao/           # NOVO — decompor extrator_pdf.py (S30)
│   ├── parsers/            # reorganizado por banco (S28) + _empresa_base.py (S27.5)
│   ├── pipeline/           # ex-pipeline_extracao.py (S31)
│   ├── exportacao/         # ex-gerador_excel*.py (S34)
│   ├── conciliacao/        # PRESERVADO (matchers/base.py recebe TOLERANCIA — S29)
│   ├── validacao/, verification/  # PRESERVADO
│   ├── contabil/           # PRESERVADO ate S35.5
│   ├── tributario/         # PRESERVADO; avaliar fundir em contabil/ (S34)
│   ├── auditoria/          # NOVO — registrar_auditoria isolado
│   └── auth_utils.py + N servicos raiz mantidos
├── infrastructure/         # NOVO — storage/, cache/, observability/
├── scripts/                # PRESERVADO — entry-points CLI
├── data/database/          # PRESERVADO ate S33 (depois → domain/models/)
├── tests/{unit,integration,e2e}/  # categorizar S35
└── migrations/             # NOVO — alembic
```

Detalhes em `proposta_estrutura.md`.

## §6 Plano de 13 sessoes (S26-S35.5)

| Sessao | Foco | Linhas removidas | Risco | Pre-requisito |
| --- | --- | --- | --- | --- |
| **S26** | DEAD GRUPO A + sub-A + tests_fase2 + diagnostico/expectativas | -1.315 a -1.365 | baixo | Pytest 912/1/1/2 (S25 confirmado) |
| **S27** | `_RE_ANO` em `parsers/base.py` (7 parsers reusam) | -30 | medio | S26 |
| **S27.5** | `parsers/_empresa_base.py` (cluster 4 parsers) | -120 | medio-alto | S27 |
| **S28** | Reorganizar `parsers/` por banco | 0 (mecanico) | alto | S27.5 |
| **S29** | `TOLERANCIA_VALOR` em `matchers/base.py` (11 matchers) | -25 | baixo | S26 |
| **S30** | Decompor `extrator_pdf.py` (1.747 linhas) → `services/extracao/` | 0 (split) | alto | S29 |
| **S31** | Unificar `pipeline_extracao.py` (774) com `extracao/` | -100 | alto | S30 |
| **S32** | Decompor `main.py` (3.010) → `app/` + `api/v1/`; remover endpoints duplicados | -200 | altissimo | S31 |
| **S33** | Split `data/database/models.py` (633) → `domain/models/`; `domain/converters.py` | -30 | medio | S32 |
| **S34** | Reorganizar `services/exportacao/` + `services/tributario/`; `infrastructure/storage/` | -40 | baixo-medio | S33 |
| **S35** | Categorizar `tests/` em `unit/`, `integration/`, `e2e/` | 0 | baixo | S34 |
| **S35.5** | Decisao Allan: REMOVER ou ATIVAR `contabil/* WIP` (5 arquivos) | -1.015 (A) ou +185 (B) | depende | S35 + decisao produto |

**Total esperado**:
- Cenario conservador (S26-S35): **-1.860 linhas (-9%)**
- Cenario com remocao WIP (cenario A): **-2.875 linhas (-13%)**
- Cenario com ativacao WIP (cenario B): **-1.675 linhas (-8%)**

## §7 Riscos transversais

### §7.1 Compat shims temporarios

Para nao quebrar imports a cada PR, **toda sessao que MOVE codigo deve manter compat shim por 1 sessao**:

```python
# services/parsers/__init__.py durante S28
from .bradesco.padrao import ParserBradesco  # noqa: F401 — compat S28
# remove na S29 apos pytest verde
```

### §7.2 Lazy imports em main.py (5 ocorrencias)

Detectados na correcao do extrator (Fase 1.b) — `from services import financeiro_service as _fs` dentro de funcoes:
- `main.py:2378`, `main.py:2450` (financeiro_service)
- `main.py:1417` (pipeline_extracao)
- `main.py:1523, 2494, 2587` (auth_utils)
- `main.py:1526, 1527, 2158, 2177, 2377, 2449` (varios)

Esses imports nao sao exercitados por todos os testes pytest. **Validar manualmente em S32** (cada ramo).

### §7.3 Imports em massa

| Sessao | Imports a atualizar |
| --- | --- |
| S28 (reorganizar parsers) | ~30 imports |
| S30 (decompor extrator_pdf) | ~10 imports |
| S31 (unificar pipeline) | ~5 imports |
| S32 (decompor main.py) | ~40 imports |
| S33 (split models) | ~25 imports |
| **Total** | **~110 atualizacoes** |

### §7.4 Anomalias arquiteturais detectadas (registrar para futuro)

1. `tests_fase2/` (2 arquivos isolados) — pode ser dead.
2. 4 endpoints duplicados main.py vs routers/* — refator parcial.
3. Auth helpers em 4 lugares — consolidar.
4. `services/score_saude.py` (LEGADO ATIVO) vs `services/contabil/score_saude.py` (NOVO sem integracao) — decisao S35.5.
5. PARSERS dict em `extrator_pdf.py:884` precisara virar registry explicito apos S30.

## §8 Estimativa final

| Marco | Backend | Frontend | Total |
| --- | --- | --- | --- |
| Pre-S25 (atual) | ~21.575 | ~28.000 (intocado) | ~50.200 (auditoria mestre) |
| Pos-S26 | ~20.260 | 28.000 | ~48.260 |
| Pos-S27.5 | ~20.110 | 28.000 | ~48.110 |
| Pos-S32 | ~19.785 | 28.000 | ~47.785 |
| Pos-S35 (cenario conservador) | ~19.715 | 28.000 | **~47.715** (-2.485 vs base) |
| Pos-S35.5 cenario A (REMOVER WIP) | ~18.700 | 28.000 | **~46.700** (-3.500 vs base) |
| Pos-S35.5 cenario B (ATIVAR WIP) | ~19.900 | 28.000 | ~47.900 |

Frontend permanece intocado ao longo dos refators. Total projeto reduz **~5-7%** dependendo do cenario S35.5.

## §9 Recomendacao para S26 (proxima sessao)

**Escopo**:
1. **Atacar GRUPO A** primeiro (DEAD CONFIRMED) — 6 arquivos / 588 linhas. Sem risco.
2. **Em seguida GRUPO B sub-A** (validar em pares antes de deletar):
   - `services/categorias.py` + `tests/test_categorias.py`
   - `services/contabil/comparador.py` + porcao de `test_comparador_indicadores_score.py`
3. **Em seguida `tests_fase2/`** + `tests/diagnostico_parsers.py` + `tests/expectativas_extratos.py` (validacao similar via `.disabled` + pytest).
4. **NAO atacar** Grupo B sub-C (5 arquivos `contabil/`) — bloqueado por decisao S35.5.

**Pytest gate**:
- Antes de cada deletar: rodar pytest, confirmar baseline (912/1/1/2 ou +zxcvbn flutuando).
- Apos cada deletar (ou par de deletes): pytest novamente.
- Total esperado pos-S26: **906-908 passed** (perda dos 6 testes em `test_categorias.py` se ele for deletado).

**Branch**: continuar em `refactor/arquitetura-estrutural` ou criar `refactor/s26-dead-code` filha.

**Tempo estimado S26**: ~30-45 min (varios pytest runs + deletes em pares).

**Riscos S26**:
- baixo. Tudo validado em S25.
- Confirmar que `test_categorias.py` so testa `categorias.py` (e nao tem dependencia oculta) — verificado em S25.
