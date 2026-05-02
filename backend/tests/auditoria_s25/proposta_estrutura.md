# Proposta de Estrutura Nova — S25 Fase 5

Sintese das Fases 1-4 sobre `backend/`. **NAO toca codigo de producao.**
Documento informativo para informar S26-S35.5.

## §0 Pano de fundo numerico

| Area | Arquivos | Linhas | % do backend |
| --- | --- | --- | --- |
| `main.py` (raiz) | 1 | **3.010** | 14% |
| `services/extrator_pdf.py` | 1 | **1.747** | 8% |
| `services/parsers/` (25 arquivos uteis + 4 dead) | 29 | 7.794 | 36% |
| `services/contabil/` (10 arquivos + tabelas + Grupo B) | 14 | 2.405 | 11% |
| `services/conciliacao/` | 16 | 463 | 2% |
| `routers/` | 11 | 4.656 | 22% |
| `services/` raiz (financeiro, motor_*, etc) | ~16 | ~3.500 | 16% |
| `services/verification/` | 5 | 1.372 | 6% |
| `services/validacao/` | 3 | 354 | 2% |
| `services/tributario/` | 6 | 706 | 3% |
| `services/parsers/n2/`, `bradesco_empresas/`, `santander_empresas/` | 7 | 575 | 3% |
| `data/database/` | 3 | 679 | 3% |
| `scripts/` | 2 | 589 | 3% |
| `core/config.py` (vazio) | 1 | 0 | 0% |
| **Total backend mapeado** | **~133** | **~21.575** | 100% |

(Numeros sao linhas brutas de `wc -l`. Codigo + comentarios + docstrings + brancos.)

## §1 Estrutura proposta — alvo da refatoracao

```
backend/
├── app/                                  # FastAPI bootstrap (S32 — ex-main.py)
│   ├── __init__.py
│   ├── main.py                           # ~150 linhas: app = FastAPI(...) + middleware
│   ├── settings.py                       # env vars, feature flags (CONTROLLO_DRE_ENGINE etc)
│   ├── dependencies.py                   # get_db, get_current_user re-exportados
│   └── lifespan.py                       # startup/shutdown handlers
│
├── api/
│   └── v1/                               # endpoints HTTP (S32 — ex-main.py + routers)
│       ├── __init__.py
│       ├── auth.py                       # login, /api/auth/*
│       ├── empresas.py                   # de routers/empresas.py + main.py:2525-2627
│       ├── extracao.py                   # endpoints de upload/extracao (ex-main.py)
│       ├── financeiro.py                 # de routers/financeiro.py
│       ├── conciliacao.py                # de routers/conciliacao.py
│       ├── classificacao.py              # de routers/classificacao.py
│       ├── importacao.py                 # de routers/importacao.py
│       ├── orcamento.py                  # de routers/orcamento.py
│       ├── relatorios.py                 # de routers/relatorios.py
│       ├── alertas.py                    # de routers/alertas.py
│       ├── auditoria.py                  # de routers/auditoria.py
│       ├── equipe.py                     # de routers/equipe.py
│       ├── master.py                     # de routers/master.py
│       └── health.py                     # /api/health (de main.py:888)
│
├── domain/
│   ├── __init__.py
│   ├── models/                           # SQLAlchemy ORM (de data/database/models.py)
│   │   ├── __init__.py
│   │   ├── usuario.py
│   │   ├── empresa.py
│   │   ├── lancamento.py
│   │   └── ... (1 arquivo por entity, S33)
│   ├── schemas/                          # Pydantic (extraidos de main.py)
│   │   ├── __init__.py
│   │   ├── usuario.py
│   │   ├── empresa.py
│   │   └── ...
│   ├── enums.py
│   └── converters.py                     # _to_dec, _to_float, _safe — extraidos da Fase 4
│
├── services/
│   ├── __init__.py
│   ├── extracao/                         # NOVO — decomposicao de extrator_pdf.py (S30)
│   │   ├── __init__.py
│   │   ├── orquestrador.py               # ~200 linhas — pos S31 unificado pipeline
│   │   ├── detector_banco.py             # _ASSINATURAS, detectar_banco (~150 linhas)
│   │   ├── leitor_pdf.py                 # pdfplumber wrapper, MAX_PAGINAS_PDF
│   │   ├── extrator_saldos.py            # _extrair_saldos_pdf (~300 linhas)
│   │   ├── ocr_fallback.py               # de services/ocr_fallback.py atual
│   │   └── normalizadores.py             # aplicar_categorias, _parse_valor_br, etc
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                       # ParserBase + _RE_ANO + _RE_DATA_VALIDA (Fase 4)
│   │   ├── _empresa_base.py              # NOVA (S27.5) — base para parsers de empresa
│   │   ├── PARSERS_REGISTRY.py           # extraido do dict de extrator_pdf.py:884
│   │   ├── bradesco/
│   │   │   ├── __init__.py
│   │   │   ├── padrao.py                 # ex-bradesco.py
│   │   │   └── net_empresas.py           # ex-bradesco_empresas/bradesco_net_empresas.py
│   │   ├── itau/
│   │   │   ├── __init__.py
│   │   │   ├── padrao.py                 # ex-itau.py
│   │   │   ├── empresas.py               # ex-itau_empresas.py
│   │   │   ├── n2.py                     # ex-n2/itau_n2.py
│   │   │   └── empresas_n2.py            # ex-n2/itau_empresas_n2.py (6 linhas — virar import?)
│   │   ├── santander/
│   │   │   ├── __init__.py
│   │   │   ├── padrao.py                 # ex-santander.py
│   │   │   ├── consolidado.py            # ex-santander_consolidado.py
│   │   │   ├── empresarial.py            # ex-santander_empresarial.py
│   │   │   ├── ib_novo.py                # ex-santander_ib_novo.py
│   │   │   └── empresas_v1.py            # ex-santander_empresas/santander_empresas_v1.py
│   │   ├── stone/
│   │   │   ├── __init__.py
│   │   │   ├── padrao.py                 # ex-stone.py
│   │   │   └── n2.py                     # ex-stone_n2.py
│   │   ├── inter/
│   │   │   ├── __init__.py
│   │   │   ├── padrao.py                 # ex-inter.py
│   │   │   └── n2.py                     # ex-n2/inter_n2.py
│   │   ├── nubank.py                     # 601 linhas, sem variantes
│   │   ├── bb.py
│   │   ├── bs2.py
│   │   ├── btg.py
│   │   ├── c6bank.py
│   │   ├── caixa.py
│   │   ├── cora.py
│   │   ├── mercado_pago.py
│   │   ├── pagbank.py
│   │   ├── safra.py
│   │   ├── sicredi.py
│   │   ├── sumup.py
│   │   ├── xp_extrato.py
│   │   └── xp_posicao.py
│   │
│   ├── pipeline/                         # NOVO — extrai pipeline_extracao.py + uso pos-extracao
│   │   ├── __init__.py
│   │   ├── orquestrador.py               # ex-services/pipeline_extracao.py
│   │   └── persistencia.py               # save_to_db logic
│   │
│   ├── validacao/                        # PRESERVADO (estrutura ja boa)
│   │   ├── __init__.py
│   │   ├── classificador_confianca.py
│   │   └── validador_saldos.py
│   │
│   ├── verification/                     # PRESERVADO
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── orchestrator.py
│   │   └── verifiers.py
│   │
│   ├── exportacao/                       # NOVO — gerador_excel*.py reorganizados
│   │   ├── __init__.py
│   │   ├── _utils.py                     # _to_float (extraido — Fase 4 §6.1)
│   │   ├── basico.py                     # ex-services/gerador_excel.py
│   │   ├── contabil.py                   # ex-services/gerador_excel_contabil.py
│   │   └── pipeline.py                   # ex-services/gerador_excel_pipeline.py (revisar uso)
│   │
│   ├── conciliacao/                      # PRESERVADO (ja em pacote)
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── excel_reader.py
│   │   └── matchers/
│   │       ├── __init__.py
│   │       ├── base.py                   # TOLERANCIA_VALOR (Fase 4 §6.2)
│   │       ├── bb.py
│   │       └── ...
│   │
│   ├── contabil/                         # PRESERVADO — decisao pendente §S35.5
│   │   ├── __init__.py
│   │   ├── core.py                       # _ZERO + _TOL extraidos (Fase 4 §6.1)
│   │   ├── balanco.py
│   │   ├── dre.py
│   │   ├── lucro_presumido.py
│   │   ├── lucro_real.py
│   │   ├── reforma.py
│   │   ├── simples_nacional.py
│   │   ├── cnae_presuncao.py
│   │   ├── indicadores.py
│   │   └── tabelas/
│   │       ├── aliquotas_icms.py
│   │       ├── reforma_tributaria.py
│   │       └── servicos_retencao.py
│   │
│   ├── tributario/                       # PRESERVADO (poderia migrar para contabil/ na S34)
│   │   ├── __init__.py
│   │   ├── constantes.py
│   │   ├── lucro_presumido.py
│   │   ├── lucro_real.py
│   │   ├── reforma.py
│   │   └── simples_nacional.py
│   │
│   ├── auditoria/                        # NOVO — funcao registrar_auditoria isolada
│   │   ├── __init__.py
│   │   └── service.py                    # ex-routers/auditoria.py:registrar_auditoria
│   │
│   ├── auth_utils.py                     # MANTIDO (12 importadores). Mover para services/auth/?
│   ├── financeiro_service.py             # MANTIDO ate S34 (refator DRE)
│   ├── simulacao_tributaria_service.py   # MANTIDO ate S34 (refator LP)
│   ├── motor_classificacao.py            # MANTIDO
│   ├── motor_narrativa.py                # MANTIDO
│   ├── score_saude.py                    # MANTIDO ate decisao §S35.5
│   ├── insights_engine.py                # MANTIDO
│   ├── categorizacao_extrato.py          # MANTIDO
│   ├── leitor_excel.py                   # MANTIDO
│   ├── importacao_service.py             # MANTIDO
│   ├── email_service.py                  # MANTIDO
│   ├── template_dashboard.py             # MANTIDO
│   ├── backup_service.py                 # MANTIDO
│   ├── cnpj_validator.py                 # MANTIDO
│   └── ocr_fallback.py                   # MOVE para services/extracao/ocr_fallback.py
│
├── infrastructure/                       # NOVO — separar IO do dominio
│   ├── __init__.py
│   ├── storage/
│   │   └── files.py                      # ex-services/storage.py
│   ├── cache/                            # se houver Redis usage no main.py
│   └── observability/                    # logs estruturados, telemetry
│
├── scripts/                              # ENTRY-POINTS CLI (preservado)
│   ├── seed_empresas_validacao_paralela.py
│   └── validacao_paralela_dre.py
│   # test_parsers.py raiz — DELETAR (S26 confirmado dead) ou mover para
│   # scripts/cli_diagnostico_parsers.py se Allan quiser preservar
│
├── data/                                 # PRESERVADO — pode renomear para infrastructure/db
│   └── database/
│       ├── __init__.py
│       ├── config.py                     # engine, get_db
│       └── models.py                     # mover gradualmente para domain/models/ (S33)
│
├── tests/
│   ├── unit/                             # testes unitarios isolados
│   ├── integration/                      # testes com DB / fixtures pesadas
│   ├── e2e/                              # testes ponta-a-ponta (test_dre_integracao etc)
│   ├── fixtures/                         # PRESERVADO
│   └── conftest.py                       # PRESERVADO
│
└── migrations/                           # NOVO — alembic (substitui migracoes ad-hoc)
```

**Pastas removidas/renomeadas comparado ao atual**:
- `backend/core/config.py` (vazio) — DELETE (DEAD CONFIRMED)
- `backend/test_parsers.py` raiz — DELETE
- `backend/tests_fase2/` — INVESTIGAR (orfaos no completo, parecem nao executar)
- `backend/services/parsers/parser_*.py` (parser_generico, parser_itau_mensal, parser_stone) — DELETE
- `backend/services/parsers/itau_extrato_mensal.py` — DELETE
- `backend/services/parsers/n2/`, `bradesco_empresas/`, `santander_empresas/` (subpastas) — REORGANIZAR em pastas por banco

## §2 Mapeamento arquivo-por-arquivo

### §2.1 DELETE (S26 — DEAD CONFIRMED da Fase 3)

| Arquivo atual | Linhas | Acao | Justificativa |
| --- | --- | --- | --- |
| `backend/core/config.py` | 0 | DELETE | Vazio, sem importadores |
| `backend/test_parsers.py` | 163 | DELETE (ou MOVE para scripts/) | CLI manual, 0 asserts, nao e teste pytest |
| `backend/services/parsers/parser_generico.py` | 77 | DELETE | Importa modulo inexistente `.parser_base`; orfao |
| `backend/services/parsers/parser_itau_mensal.py` | 54 | DELETE | Idem; orfao; substituido por `itau.py`+`n2/itau_n2.py` |
| `backend/services/parsers/parser_stone.py` | 49 | DELETE | Idem; substituido por `stone.py`+`stone_n2.py` |
| `backend/services/parsers/itau_extrato_mensal.py` | 245 | DELETE | Orfao; sem entrada em PARSERS dict |
| **Subtotal S26 GRUPO A** | **588** | | |

### §2.2 DELETE EM PARES (S26 — Grupo B sub-A da Fase 3c)

| Arquivo + Teste | Linhas | Acao | Justificativa |
| --- | --- | --- | --- |
| `services/categorias.py` + `tests/test_categorias.py` | 398 + 38 | DELETE em par | `aplicar_categorias` duplicada em `extrator_pdf.py:1648` (versao usada) |
| `services/contabil/comparador.py` + porcao de `test_comparador_indicadores_score.py` | 191 + ~100 | DELETE em par | Endpoint nao usa; motor novo nao usa; duplicata funcional |
| **Subtotal S26 sub-A** | **~727** | | |

### §2.3 PRESERVAR ate decisao Allan (Grupo B sub-C — S35.5)

| Arquivo | Linhas | Acao |
| --- | --- | --- |
| `services/contabil/dfc.py` + `tests/test_dfc.py` | 340 + 552 | PRESERVAR — DECIDIR S35.5 |
| `services/contabil/difal.py` (parte de `tests/test_retencoes_difal_st.py`) | 136 + ~150 | PRESERVAR |
| `services/contabil/icms_st.py` (idem) | 108 + ~150 | PRESERVAR |
| `services/contabil/retencoes.py` (idem) | 138 + ~100 | PRESERVAR |
| `services/contabil/score_saude.py` + porcao de testes | 267 + ~150 | PRESERVAR (concorre com legado em `services/score_saude.py`) |
| **Subtotal S35.5 (potencial)** | **~989 + ~1.100 testes** | |

### §2.4 EXTRACT (Fase 4 — extracoes mecanicas)

| O que extrair | De | Para | Sessao |
| --- | --- | --- | --- |
| `_to_float` (corpo identico) | `gerador_excel.py:47-52` + `gerador_excel_contabil.py:48-53` | `services/exportacao/_utils.py` (S34) | S34 |
| `_to_dec` (corpos identicos) | `motor_narrativa.py:20-25` + `score_saude.py:11-16` | `domain/converters.py` (S33) | S33 |
| `_RE_ANO = re.compile(r'\b(20\d{2})\b')` | 7 parsers | `parsers/base.py` (S27) | S27 |
| `_RE_VALOR = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')` | 3 parsers de empresa | `parsers/_empresa_base.py` (S27.5) | S27.5 |
| `TOLERANCIA_VALOR = Decimal('0.02')` | 11 matchers | `services/conciliacao/matchers/base.py` (S29) | S29 |
| Cluster blocos parsers empresa (4 arquivos) | bradesco_net_empresas, btg, n2/itau_n2, santander_empresas_v1 | `parsers/_empresa_base.py` | S27.5 |

### §2.5 SPLIT (decomposicao de monolitos)

| Arquivo monolito | Linhas | Para onde | Sessao |
| --- | --- | --- | --- |
| `services/extrator_pdf.py` | 1.747 | `services/extracao/{detector_banco, leitor_pdf, extrator_saldos, normalizadores}.py` | **S30** |
| `services/pipeline_extracao.py` | 774 | `services/pipeline/{orquestrador, persistencia}.py` | **S31** (unificar com S30) |
| `main.py` | 3.010 | `app/main.py` (~200) + `api/v1/*.py` (extracoes nao cobertas pelos routers atuais) + `domain/schemas/*.py` | **S32** |
| `data/database/models.py` | 633 | `domain/models/{usuario, empresa, lancamento, ...}.py` | **S33** |

### §2.6 MOVE (renomear/realocar sem split)

| De | Para | Sessao |
| --- | --- | --- |
| `services/parsers/n2/inter_n2.py` (6 linhas) | `services/parsers/inter/n2.py` | S28 |
| `services/parsers/n2/itau_n2.py` | `services/parsers/itau/n2.py` | S28 |
| `services/parsers/n2/itau_empresas_n2.py` (6 linhas) | `services/parsers/itau/empresas_n2.py` | S28 |
| `services/parsers/bradesco_empresas/bradesco_net_empresas.py` | `services/parsers/bradesco/net_empresas.py` | S28 |
| `services/parsers/santander_empresas/santander_empresas_v1.py` | `services/parsers/santander/empresas_v1.py` | S28 |
| `services/parsers/santander_empresas/santander_empresas_v2.py` (6 linhas) | `services/parsers/santander/empresas_v2.py` | S28 |
| `services/parsers/santander_consolidado.py` | `services/parsers/santander/consolidado.py` | S28 |
| `services/parsers/santander_empresarial.py` | `services/parsers/santander/empresarial.py` | S28 |
| `services/parsers/santander_ib_novo.py` | `services/parsers/santander/ib_novo.py` | S28 |
| `services/parsers/itau_empresas.py` | `services/parsers/itau/empresas.py` | S28 |
| `services/parsers/bradesco.py` | `services/parsers/bradesco/padrao.py` | S28 |
| `services/parsers/itau.py` | `services/parsers/itau/padrao.py` | S28 |
| `services/parsers/stone.py` | `services/parsers/stone/padrao.py` | S28 |
| `services/parsers/stone_n2.py` | `services/parsers/stone/n2.py` | S28 |
| `services/parsers/inter.py` | `services/parsers/inter/padrao.py` | S28 |
| `services/parsers/santander.py` | `services/parsers/santander/padrao.py` | S28 |
| `services/storage.py` | `infrastructure/storage/files.py` | S34 |
| `services/ocr_fallback.py` | `services/extracao/ocr_fallback.py` | S30 |
| `services/gerador_excel.py` | `services/exportacao/basico.py` | S34 |
| `services/gerador_excel_contabil.py` | `services/exportacao/contabil.py` | S34 |
| `services/gerador_excel_pipeline.py` | `services/exportacao/pipeline.py` | S34 |
| `routers/*.py` (todos) | `api/v1/*.py` | S32 |

## §3 Plano de sessoes atualizado (S26 - S35.5)

### S26 — Remocao de Dead Code (PR1)
**Pastas tocadas**: `services/parsers/`, `core/`, raiz `backend/`.
**Pre-req**: nenhum (pytest baseline 912/1/1/2 confirmado em S25).
**Mudancas**:
- DELETE: 6 arquivos do GRUPO A confirmados (588 linhas)
- DELETE em pares: `services/categorias.py` + `tests/test_categorias.py` + `services/contabil/comparador.py` + porcao de `test_comparador_indicadores_score.py` (~727 linhas)
- Confirmar pytest pos-deletes (912 passed esperado, ate 6-10 testes a menos pelo deleted test_categorias)
**Riscos**:
- baixo. Tudo validado em S25.

### S27 — Limpeza parsers/base.py (PR2)
**Pastas tocadas**: `services/parsers/`.
**Pre-req**: S26.
**Mudancas**:
- ADD: `_RE_ANO` em `parsers/base.py`
- ADD: helpers `_extrair_ano_referencia` reusable
- REPLACE: 7 parsers (bb, bradesco, c6bank, itau, itau_empresas, nubank, stone) reusam `_RE_ANO` da base
- Remover declaracoes locais
**Riscos**:
- medio. Testes de cada parser tocado precisam re-rodar.

### S27.5 — _empresa_base.py (PR3)
**Pastas tocadas**: `services/parsers/`.
**Pre-req**: S27.
**Mudancas**:
- NEW: `services/parsers/_empresa_base.py` com helpers comuns + regex `_RE_VALOR`, `_RE_TRAILING_INTS`, `_RE_DATA_LINHA`
- REPLACE: `bradesco_net_empresas`, `btg`, `n2/itau_n2`, `santander_empresas_v1` — herdar de `_EmpresaBase` (em vez de `ParserBase`)
- DELETE helpers locais duplicados (`_e_linha_skip`, `_limpar_descricao`, `_normalizar_float`)
**Riscos**:
- medio-alto. Heranca em duplo nivel pode esconder bugs.
- 4 PDFs reais devem rodar para confirmar que parsers funcionam.

### S28 — Reorganizacao parsers/ por banco (PR4)
**Pastas tocadas**: `services/parsers/` (rename massivo).
**Pre-req**: S27.5.
**Mudancas**:
- MOVES da §2.6 (15+ arquivos)
- Atualizar TODOS os imports em `extrator_pdf.py` (~25 linhas) e em testes
- Manter `__init__.py` re-exportando classes para nao quebrar `from services.parsers.X import ParserY` antigos (compat shim — temporario, ate S29)
**Riscos**:
- alto. Cadeia de imports massiva.
- Risco de teste passar mas runtime quebrar (import lazy nao testado).

### S29 — Conciliacao + matchers/base (PR5)
**Pastas tocadas**: `services/conciliacao/matchers/`.
**Pre-req**: S26.
**Mudancas**:
- ADD: `TOLERANCIA_VALOR` em `matchers/base.py`
- REPLACE: 11 matchers usam constante da base
- Remover compat shims criados na S28 (limpa imports antigos parsers)
**Riscos**:
- baixo. Mudanca isolada.

### S30 — Decompor extrator_pdf.py (PR6 — gigante)
**Pastas tocadas**: novo `services/extracao/`.
**Pre-req**: S29.
**Mudancas**:
- SPLIT: `services/extrator_pdf.py` (1.747 linhas) em:
  * `extracao/detector_banco.py` (~200 linhas — `_ASSINATURAS`, `_NOME_BANCO_EXIBICAO`, `detectar_banco()`)
  * `extracao/leitor_pdf.py` (~150 linhas — pdfplumber wrapper, `MAX_PAGINAS_PDF`)
  * `extracao/extrator_saldos.py` (~400 linhas — `_extrair_saldos_pdf`)
  * `extracao/normalizadores.py` (~200 linhas — `aplicar_categorias`, `_parse_valor_br`)
  * `extracao/orquestrador.py` (~300 linhas — fluxo `extrair_de_pdf`)
  * `extracao/__init__.py` re-exporta para compat
- MOVE: `services/ocr_fallback.py` → `services/extracao/ocr_fallback.py`
- Atualizar imports em `pipeline_extracao.py`
**Riscos**:
- alto. Monolito tem out-degree=30; mudanca afeta todo o codebase.

### S31 — Unificar pipeline com extracao (PR7)
**Pastas tocadas**: `services/pipeline/`, `services/extracao/`.
**Pre-req**: S30.
**Mudancas**:
- SPLIT: `services/pipeline_extracao.py` (774 linhas) em `pipeline/orquestrador.py` + `pipeline/persistencia.py`
- Eliminar duplicacao orquestrador `extracao/` vs `pipeline/`; fundir em um fluxo unificado
**Riscos**:
- alto. Logica de orquestracao tem ramificacoes.

### S32 — Decompor main.py (PR8 — gigante)
**Pastas tocadas**: novo `app/`, novo `api/v1/`.
**Pre-req**: S31.
**Mudancas**:
- SPLIT: `main.py` (3.010 linhas) em:
  * `app/main.py` (~200 linhas — bootstrap FastAPI)
  * `app/settings.py` (~80 linhas — env vars, flags)
  * `app/dependencies.py` (~50 linhas — Depends)
  * `app/lifespan.py` (~100 linhas — startup/shutdown)
  * `api/v1/health.py` (~30 linhas — `/api/health`)
  * `api/v1/auth.py` (~150 linhas — login + refresh)
  * Pydantic schemas → `domain/schemas/*.py` (~500 linhas redistribuidas)
- MOVE: `routers/*.py` → `api/v1/*.py` (preservar nomes, ajustar imports relativos)
- DELETE em `api/v1/*` os endpoints duplicados ja em routers (criar_empresa, atualizar_empresa, aprovar_usuario, excluir_usuario)
- Consolidar auth helpers em `services/auth_utils.py`
**Riscos**:
- altissimo. Monolito tem 28 imports out + ~30 endpoints.
- Quebra de URL e risco real (teste de cada rota).

### S33 — Decompor data/database/models.py (PR9)
**Pastas tocadas**: novo `domain/models/`, `data/database/`.
**Pre-req**: S32.
**Mudancas**:
- SPLIT: `data/database/models.py` (633 linhas) em `domain/models/{usuario, empresa, lancamento, ...}.py`
- Adicionar `domain/converters.py` com `_to_dec`, `_to_float` extraidos
- Re-exports em `domain/__init__.py` para compat
**Riscos**:
- medio. Imports de SQLAlchemy precisam ordem correta.

### S34 — Reorganizar exportacao/ + tributario/ (PR10)
**Pastas tocadas**: `services/exportacao/` (novo), `services/tributario/`.
**Pre-req**: S33.
**Mudancas**:
- MOVES de `services/gerador_excel*.py` → `services/exportacao/`
- ADD `services/exportacao/_utils.py` com `_to_float`
- Avaliar fundir `services/tributario/` com `services/contabil/` (4 arquivos `calcular()` + `constantes.py`)
- MOVE `services/storage.py` → `infrastructure/storage/files.py`
**Riscos**:
- baixo-medio. Tributario tem 6 importadores — mudanca de path simples.

### S35 — Reorganizar testes (PR11)
**Pastas tocadas**: `tests/` (renomear em `unit/`, `integration/`, `e2e/`).
**Pre-req**: S34.
**Mudancas**:
- Categorizar 50+ test_*.py por nivel
- DELETE `backend/tests_fase2/` (verificar primeiro se algum CLI usa)
- DELETE `tests/diagnostico_parsers.py`, `tests/expectativas_extratos.py` se forem dead
**Riscos**:
- baixo. Testes nao tem importadores externos.

### S35.5 — Decisao Allan: contabil/* WIP (PR12 — opcional)
**Pastas tocadas**: `services/contabil/`.
**Pre-req**: S35 + decisao explicita Allan.
**Mudancas (cenario A — REMOVER WIP)**:
- DELETE: `dfc.py`, `difal.py`, `icms_st.py`, `retencoes.py`, `score_saude.py` (~989 linhas)
- DELETE: testes correspondentes (~1.100 linhas)
- ADD `_ZERO`, `_TOL` em `contabil/core.py` para os arquivos remanescentes (Fase 4 §6.2)
**Mudancas (cenario B — ATIVAR WIP)**:
- ADD: novos endpoints `/api/financeiro/dfc`, `/api/tributario/retencoes-difal-st`
- Migrar `score_saude.py` legado → `contabil/score_saude.py` novo (deprecar legado)
**Riscos**:
- B: alto (novos endpoints, integracao com testes existentes)
- A: medio (perdemos 989 linhas de logica contabil que pode ser reativada)

## §4 Riscos gerais transversais

### §4.1 Re-exports temporarios necessarios

Para nao quebrar imports externos a cada PR, **todas as sessoes que MOVE codigo devem manter compat shim** durante uma sessao:

```python
# services/parsers/__init__.py durante S28
from .bradesco.padrao import ParserBradesco  # noqa: F401 — compat S28
from .itau.padrao import ParserItau  # noqa: F401 — compat S28
# ... etc
```

Compat shims removidos APOS a sessao seguinte confirmar pytest verde.

### §4.2 Imports a atualizar em massa

| Sessao | Arquivos com imports a atualizar | Quantidade |
| --- | --- | --- |
| S28 | extrator_pdf.py + tests/* parsers + matchers (uniformizacao chaves) | ~30 imports |
| S30 | pipeline_extracao.py + main.py | ~10 imports |
| S31 | main.py + 1-2 routers | ~5 imports |
| S32 | TUDO que importa main:* | ~40 imports |
| S33 | TUDO que importa `data.database.models` | ~25 imports |

### §4.3 Possiveis breaking changes em testes

- S28 (parsers reorganizados): testes usam `from services.parsers.bradesco import ParserBradesco`. Apos S28 vira `from services.parsers.bradesco.padrao import ParserBradesco` (ou compat shim no `__init__`).
- S32 (decompor main.py): `tests/conftest.py` importa `main` — precisa atualizar para `from app.main import app`.

### §4.4 Riscos de regressao silenciosa

- **Lazy imports em main.py (5 ocorrencias detectadas em Fase 1.b)** podem nao ser exercitados por pytest e quebrar em runtime.
- **PARSERS_REGISTRY dict**: o dict atual e populado em ordem por `import` no topo de `extrator_pdf.py`. Apos S30, registry deve ser explicito (nao implicit `dict[str, type]` cheio de imports).

## §5 Estimativa de linhas

Linhas brutas atuais: **~21.575** (backend mapeado).
(Fonte: §0. Numero ~50.200 da auditoria mestre inclui frontend.)

| Marco | Linhas backend | Delta |
| --- | --- | --- |
| Pre-S25 | 21.575 | — |
| Pos-S26 (DEAD GRUPO A + sub-A) | ~20.260 | **-1.315** |
| Pos-S27 (`_RE_ANO` extraido) | ~20.230 | -30 |
| Pos-S27.5 (`_empresa_base.py`) | ~20.110 | -120 |
| Pos-S28 (reorganizacao) | ~20.110 | 0 (mecanico) |
| Pos-S29 (TOLERANCIA_VALOR) | ~20.085 | -25 |
| Pos-S30 (decompor extrator_pdf) | ~20.085 | 0 (split, mesmo total) |
| Pos-S31 (unificar pipeline) | ~19.985 | -100 (eliminacao orquestracao duplicada) |
| Pos-S32 (decompor main.py + endpoints duplicados) | ~19.785 | -200 |
| Pos-S33 (split models + converters) | ~19.755 | -30 |
| Pos-S34 (exportacao + tributario) | ~19.715 | -40 |
| Pos-S35 (testes reorganizados) | ~19.715 | 0 |
| Pos-S35.5 cenario A (REMOVER WIP) | ~18.700 | -1.015 |
| Pos-S35.5 cenario B (ATIVAR WIP) | ~19.900 | +185 (novos endpoints) |

**Reducao total esperada**:
- Cenario conservador (S26 a S35): **~1.860 linhas** (-9%)
- Cenario com remocao WIP (S35.5 A): **~2.875 linhas** (-13%)

## §6 Sintese para o relatorio executivo (Fase 6)

1. **Estrutura proposta acomoda**: dead code removido + duplicacao tratada + 2 monolitos decompostos.
2. **Reducao estimada**: 9-13% de linhas (1.860 a 2.875 linhas), sem contar testes movidos.
3. **Sessoes de alto risco**: S30 (extrator_pdf), S32 (main.py), S35.5 cenario B (ATIVAR WIP).
4. **Sessoes de baixo risco**: S26 (DELETE validados), S29 (constantes), S35 (mover testes).
5. **Bloqueios pendentes**:
   - S35.5 depende de decisao de produto Allan sobre contabil/* WIP (~989 linhas em jogo).
   - S32 depende de exposicao explicita das URL paths (auditar antes).
6. **Anomalias arquiteturais detectadas**:
   - `tests_fase2/` pode ser dead (orfaos completo)
   - 4 endpoints duplicados main.py vs routers/ — sintoma de refator parcial
   - Auth helpers espalhados em 4 lugares — consolidar em `auth_utils.py`
