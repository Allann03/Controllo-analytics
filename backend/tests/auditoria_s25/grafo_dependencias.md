# Grafo de Dependencias — S25 Fase 1

Gerado por `audit_grafo.py`. Read-only.

Dois recortes:

- **producao**: backend/main.py + services/ + routers/ + data/ + scripts/
- **completo**: producao + tests/ + tests_fase2/ + test_parsers.py raiz

Entry-points (in-degree=0 esperado por design):

- `backend/main.py`
- `backend/scripts/seed_empresas_validacao_paralela.py`
- `backend/scripts/validacao_paralela_dre.py`

## Recorte PRODUCAO

- Total de arquivos .py mapeados: **133**
- Total de arestas (imports internos): **257**
- Imports circulares detectados: **0**
- Arquivos sem in-degree (orfaos): **21**
  - dos quais entry-points (esperado): **3**
  - dos quais NAO entry-points (suspeitos): **18**
- Arquivos com in-degree=1: **89**
- Modulos isolados (in=0 E out=0): **11**

### Top 10 Mais Importados (Recorte PRODUCAO)

| Arquivo | in-degree |
| --- | --- |
| `backend/services/parsers/base.py` | 28 |
| `backend/data/database/models.py` | 18 |
| `backend/services/contabil/core.py` | 18 |
| `backend/data/database/__init__.py` | 17 |
| `backend/data/database/config.py` | 16 |
| `backend/services/conciliacao/matchers/base.py` | 13 |
| `backend/services/auth_utils.py` | 12 |
| `backend/services/tributario/constantes.py` | 6 |
| `backend/routers/auditoria.py` | 5 |
| `backend/services/extrator_pdf.py` | 4 |

### Top 10 Que Mais Importam (Recorte PRODUCAO)

| Arquivo | out-degree |
| --- | --- |
| `backend/services/extrator_pdf.py` | 30 |
| `backend/main.py` | 29 |
| `backend/services/conciliacao/matchers/__init__.py` | 13 |
| `backend/routers/financeiro.py` | 9 |
| `backend/routers/conciliacao.py` | 7 |
| `backend/routers/importacao.py` | 7 |
| `backend/routers/classificacao.py` | 6 |
| `backend/services/financeiro_service.py` | 6 |
| `backend/services/simulacao_tributaria_service.py` | 6 |
| `backend/routers/alertas.py` | 5 |

### Imports Circulares (Recorte PRODUCAO)

Nenhum ciclo detectado.

### Arquivos sem In-Degree NAO entry-point (Recorte PRODUCAO)

Sao candidatos a dead code (validar em Fase 2/3).

- `backend/core/config.py` (out-degree=0)
- `backend/routers/__init__.py` (out-degree=0)
- `backend/services/categorias.py` (out-degree=0)
- `backend/services/contabil/comparador.py` (out-degree=5)
- `backend/services/contabil/dfc.py` (out-degree=3)
- `backend/services/contabil/difal.py` (out-degree=2)
- `backend/services/contabil/icms_st.py` (out-degree=1)
- `backend/services/contabil/retencoes.py` (out-degree=2)
- `backend/services/contabil/score_saude.py` (out-degree=3)
- `backend/services/contabil/tabelas/__init__.py` (out-degree=0)
- `backend/services/parsers/__init__.py` (out-degree=0)
- `backend/services/parsers/bradesco_empresas/__init__.py` (out-degree=0)
- `backend/services/parsers/itau_extrato_mensal.py` (out-degree=1)
- `backend/services/parsers/n2/__init__.py` (out-degree=0)
- `backend/services/parsers/parser_generico.py` (out-degree=0)
- `backend/services/parsers/parser_itau_mensal.py` (out-degree=0)
- `backend/services/parsers/parser_stone.py` (out-degree=0)
- `backend/services/parsers/santander_empresas/__init__.py` (out-degree=0)

### Entry-points reconhecidos (Recorte PRODUCAO)

- `backend/main.py` (in-degree=0, out-degree=29)
- `backend/scripts/seed_empresas_validacao_paralela.py` (in-degree=0, out-degree=3)
- `backend/scripts/validacao_paralela_dre.py` (in-degree=0, out-degree=5)

### Arquivos com In-Degree=1 (Recorte PRODUCAO)

- `backend/routers/alertas.py` <- `backend/main.py`
- `backend/routers/classificacao.py` <- `backend/main.py`
- `backend/routers/conciliacao.py` <- `backend/main.py`
- `backend/routers/empresas.py` <- `backend/main.py`
- `backend/routers/equipe.py` <- `backend/main.py`
- `backend/routers/financeiro.py` <- `backend/main.py`
- `backend/routers/importacao.py` <- `backend/main.py`
- `backend/routers/master.py` <- `backend/main.py`
- `backend/routers/orcamento.py` <- `backend/main.py`
- `backend/routers/relatorios.py` <- `backend/main.py`
- `backend/services/backup_service.py` <- `backend/main.py`
- `backend/services/categorizacao_extrato.py` <- `backend/main.py`
- `backend/services/cnpj_validator.py` <- `backend/main.py`
- `backend/services/conciliacao/__init__.py` <- `backend/routers/conciliacao.py`
- `backend/services/conciliacao/engine.py` <- `backend/services/conciliacao/__init__.py`
- `backend/services/conciliacao/excel_reader.py` <- `backend/services/conciliacao/__init__.py`
- `backend/services/conciliacao/matchers/__init__.py` <- `backend/services/conciliacao/engine.py`
- `backend/services/conciliacao/matchers/bb.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/bradesco.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/c6bank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/caixa.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/inter.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/itau.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/mercado_pago.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/nubank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/pagbank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/santander.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/sicredi.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/stone.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/universal.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/contabil/__init__.py` <- `backend/services/contabil/score_saude.py`
- `backend/services/contabil/balanco.py` <- `backend/services/contabil/dfc.py`
- `backend/services/contabil/cnae_presuncao.py` <- `backend/services/simulacao_tributaria_service.py`
- `backend/services/contabil/indicadores.py` <- `backend/services/contabil/score_saude.py`
- `backend/services/contabil/lucro_real.py` <- `backend/services/contabil/comparador.py`
- `backend/services/contabil/reforma.py` <- `backend/services/contabil/comparador.py`
- `backend/services/contabil/simples_nacional.py` <- `backend/services/contabil/comparador.py`
- `backend/services/contabil/tabelas/aliquotas_icms.py` <- `backend/services/contabil/difal.py`
- `backend/services/contabil/tabelas/reforma_tributaria.py` <- `backend/services/contabil/reforma.py`
- `backend/services/contabil/tabelas/servicos_retencao.py` <- `backend/services/contabil/retencoes.py`
- `backend/services/email_service.py` <- `backend/routers/alertas.py`
- `backend/services/gerador_excel.py` <- `backend/main.py`
- `backend/services/gerador_excel_contabil.py` <- `backend/main.py`
- `backend/services/gerador_excel_pipeline.py` <- `backend/services/pipeline_extracao.py`
- `backend/services/importacao_service.py` <- `backend/routers/importacao.py`
- `backend/services/insights_engine.py` <- `backend/services/financeiro_service.py`
- `backend/services/leitor_excel.py` <- `backend/main.py`
- `backend/services/parsers/bb.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/bradesco.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/bs2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/btg.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/c6bank.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/caixa.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/cora.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/itau.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/mercado_pago.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/inter_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/itau_empresas_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/itau_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/nubank.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/pagbank.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/safra.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander_empresas/santander_empresas_v2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander_ib_novo.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/sicredi.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/stone.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/stone_n2.py` <- `backend/services/parsers/stone.py`
- `backend/services/parsers/sumup.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/xp_extrato.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/xp_posicao.py` <- `backend/services/extrator_pdf.py`
- `backend/services/pipeline_extracao.py` <- `backend/main.py`
- `backend/services/simulacao_tributaria_service.py` <- `backend/routers/financeiro.py`
- `backend/services/storage.py` <- `backend/main.py`
- `backend/services/template_dashboard.py` <- `backend/main.py`
- `backend/services/tributario/__init__.py` <- `backend/services/simulacao_tributaria_service.py`
- `backend/services/tributario/lucro_presumido.py` <- `backend/services/tributario/__init__.py`
- `backend/services/tributario/lucro_real.py` <- `backend/services/tributario/__init__.py`
- `backend/services/tributario/reforma.py` <- `backend/services/tributario/__init__.py`
- `backend/services/tributario/simples_nacional.py` <- `backend/services/tributario/__init__.py`
- `backend/services/validacao/__init__.py` <- `backend/services/pipeline_extracao.py`
- `backend/services/validacao/classificador_confianca.py` <- `backend/services/validacao/__init__.py`
- `backend/services/validacao/validador_saldos.py` <- `backend/services/validacao/__init__.py`
- `backend/services/verification/__init__.py` <- `backend/main.py`
- `backend/services/verification/base.py` <- `backend/services/verification/verifiers.py`
- `backend/services/verification/orchestrator.py` <- `backend/services/verification/__init__.py`
- `backend/services/verification/verifiers.py` <- `backend/services/verification/orchestrator.py`

### Modulos Isolados (Recorte PRODUCAO)

- `backend/core/config.py`
- `backend/routers/__init__.py`
- `backend/services/categorias.py`
- `backend/services/contabil/tabelas/__init__.py`
- `backend/services/parsers/__init__.py`
- `backend/services/parsers/bradesco_empresas/__init__.py`
- `backend/services/parsers/n2/__init__.py`
- `backend/services/parsers/parser_generico.py`
- `backend/services/parsers/parser_itau_mensal.py`
- `backend/services/parsers/parser_stone.py`
- `backend/services/parsers/santander_empresas/__init__.py`

## Recorte COMPLETO

- Total de arquivos .py mapeados: **187**
- Total de arestas (imports internos): **367**
- Imports circulares detectados: **0**
- Arquivos sem in-degree (orfaos): **64**
  - dos quais entry-points (esperado): **2**
  - dos quais NAO entry-points (suspeitos): **62**
- Arquivos com in-degree=1: **70**
- Modulos isolados (in=0 E out=0): **14**

### Top 10 Mais Importados (Recorte COMPLETO)

| Arquivo | in-degree |
| --- | --- |
| `backend/services/contabil/core.py` | 30 |
| `backend/services/parsers/base.py` | 30 |
| `backend/data/database/models.py` | 26 |
| `backend/data/database/__init__.py` | 25 |
| `backend/data/database/config.py` | 17 |
| `backend/services/auth_utils.py` | 13 |
| `backend/services/conciliacao/matchers/base.py` | 13 |
| `backend/services/extrator_pdf.py` | 12 |
| `backend/tests/conftest.py` | 10 |
| `backend/services/contabil/dre.py` | 7 |

### Top 10 Que Mais Importam (Recorte COMPLETO)

| Arquivo | out-degree |
| --- | --- |
| `backend/services/extrator_pdf.py` | 30 |
| `backend/main.py` | 29 |
| `backend/services/conciliacao/matchers/__init__.py` | 13 |
| `backend/routers/financeiro.py` | 9 |
| `backend/routers/conciliacao.py` | 7 |
| `backend/routers/importacao.py` | 7 |
| `backend/routers/classificacao.py` | 6 |
| `backend/services/financeiro_service.py` | 6 |
| `backend/services/simulacao_tributaria_service.py` | 6 |
| `backend/tests/test_dre_integracao.py` | 6 |

### Imports Circulares (Recorte COMPLETO)

Nenhum ciclo detectado.

### Arquivos sem In-Degree NAO entry-point (Recorte COMPLETO)

Sao candidatos a dead code (validar em Fase 2/3).

- `backend/core/config.py` (out-degree=0)
- `backend/routers/__init__.py` (out-degree=0)
- `backend/services/contabil/tabelas/__init__.py` (out-degree=0)
- `backend/services/parsers/itau_extrato_mensal.py` (out-degree=1)
- `backend/services/parsers/n2/__init__.py` (out-degree=0)
- `backend/services/parsers/parser_generico.py` (out-degree=0)
- `backend/services/parsers/parser_itau_mensal.py` (out-degree=0)
- `backend/services/parsers/parser_stone.py` (out-degree=0)
- `backend/services/parsers/santander_empresas/__init__.py` (out-degree=0)
- `backend/services/verification/tests/__init__.py` (out-degree=0)
- `backend/services/verification/tests/test_verification.py` (out-degree=4)
- `backend/test_parsers.py` (out-degree=1)
- `backend/tests/__init__.py` (out-degree=0)
- `backend/tests/diagnostico_parsers.py` (out-degree=1)
- `backend/tests/expectativas_extratos.py` (out-degree=0)
- `backend/tests/test_all_parsers.py` (out-degree=1)
- `backend/tests/test_balanco.py` (out-degree=3)
- `backend/tests/test_categorias.py` (out-degree=1)
- `backend/tests/test_classificacao_motor.py` (out-degree=1)
- `backend/tests/test_comparador_indicadores_score.py` (out-degree=5)
- `backend/tests/test_contabil_core.py` (out-degree=1)
- `backend/tests/test_deteccao_banco.py` (out-degree=1)
- `backend/tests/test_dfc.py` (out-degree=4)
- `backend/tests/test_dre.py` (out-degree=2)
- `backend/tests/test_dre_integracao.py` (out-degree=6)
- `backend/tests/test_excel_contabil.py` (out-degree=1)
- `backend/tests/test_extrair_saldos_bradesco_net_empresas.py` (out-degree=0)
- `backend/tests/test_extrair_saldos_santander_s19.py` (out-degree=1)
- `backend/tests/test_gerador_excel_spec_allan.py` (out-degree=1)
- `backend/tests/test_integridade.py` (out-degree=1)
- `backend/tests/test_inter_ocr_fallback.py` (out-degree=3)
- `backend/tests/test_lp_adapter.py` (out-degree=2)
- `backend/tests/test_lp_dispatch.py` (out-degree=4)
- `backend/tests/test_lp_integracao.py` (out-degree=4)
- `backend/tests/test_lucro_presumido.py` (out-degree=2)
- `backend/tests/test_lucro_real.py` (out-degree=2)
- `backend/tests/test_pagbank.py` (out-degree=1)
- `backend/tests/test_pagbank_integracao.py` (out-degree=1)
- `backend/tests/test_parser_bradesco_net_empresas_lote_a.py` (out-degree=2)
- `backend/tests/test_parser_santander_ib_novo.py` (out-degree=2)
- `backend/tests/test_parsers_logic.py` (out-degree=1)
- `backend/tests/test_reforma.py` (out-degree=3)
- `backend/tests/test_resiliencia.py` (out-degree=1)
- `backend/tests/test_resiliencia_extra.py` (out-degree=1)
- `backend/tests/test_retencoes_difal_st.py` (out-degree=5)
- `backend/tests/test_safra.py` (out-degree=1)
- `backend/tests/test_santander_empresarial_sinal_separado.py` (out-degree=1)
- `backend/tests/test_santander_empresas_bugs_s21.py` (out-degree=4)
- `backend/tests/test_santander_ib_novo_saldos_intermediarios.py` (out-degree=1)
- `backend/tests/test_security_upload.py` (out-degree=3)
- `backend/tests/test_simples_nacional.py` (out-degree=2)
- `backend/tests/test_stone_saldos_s24.py` (out-degree=3)
- `backend/tests/test_tenant.py` (out-degree=3)
- `backend/tests/test_tenant_critico1.py` (out-degree=1)
- `backend/tests/test_tributario.py` (out-degree=4)
- `backend/tests/test_usuario_mestre_protecao.py` (out-degree=3)
- `backend/tests/test_validacao_senha.py` (out-degree=4)
- `backend/tests/test_validador_diagnostico_acionavel_s19.py` (out-degree=2)
- `backend/tests/test_validador_saldos.py` (out-degree=2)
- `backend/tests/validacao_lp_paralela.py` (out-degree=3)
- `backend/tests_fase2/conftest_setup.py` (out-degree=0)
- `backend/tests_fase2/validar_completo.py` (out-degree=0)

### Entry-points reconhecidos (Recorte COMPLETO)

- `backend/main.py` (in-degree=1, out-degree=29)
- `backend/scripts/seed_empresas_validacao_paralela.py` (in-degree=0, out-degree=3)
- `backend/scripts/validacao_paralela_dre.py` (in-degree=0, out-degree=5)

### Arquivos com In-Degree=1 (Recorte COMPLETO)

- `backend/main.py` <- `backend/tests/conftest.py`
- `backend/routers/alertas.py` <- `backend/main.py`
- `backend/routers/classificacao.py` <- `backend/main.py`
- `backend/routers/conciliacao.py` <- `backend/main.py`
- `backend/routers/empresas.py` <- `backend/main.py`
- `backend/routers/equipe.py` <- `backend/main.py`
- `backend/routers/financeiro.py` <- `backend/main.py`
- `backend/routers/importacao.py` <- `backend/main.py`
- `backend/routers/master.py` <- `backend/main.py`
- `backend/routers/orcamento.py` <- `backend/main.py`
- `backend/routers/relatorios.py` <- `backend/main.py`
- `backend/services/backup_service.py` <- `backend/main.py`
- `backend/services/categorias.py` <- `backend/tests/test_categorias.py`
- `backend/services/categorizacao_extrato.py` <- `backend/main.py`
- `backend/services/cnpj_validator.py` <- `backend/main.py`
- `backend/services/conciliacao/__init__.py` <- `backend/routers/conciliacao.py`
- `backend/services/conciliacao/engine.py` <- `backend/services/conciliacao/__init__.py`
- `backend/services/conciliacao/excel_reader.py` <- `backend/services/conciliacao/__init__.py`
- `backend/services/conciliacao/matchers/__init__.py` <- `backend/services/conciliacao/engine.py`
- `backend/services/conciliacao/matchers/bb.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/bradesco.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/c6bank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/caixa.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/inter.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/itau.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/mercado_pago.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/nubank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/pagbank.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/santander.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/sicredi.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/stone.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/conciliacao/matchers/universal.py` <- `backend/services/conciliacao/matchers/__init__.py`
- `backend/services/contabil/comparador.py` <- `backend/tests/test_comparador_indicadores_score.py`
- `backend/services/contabil/dfc.py` <- `backend/tests/test_dfc.py`
- `backend/services/contabil/difal.py` <- `backend/tests/test_retencoes_difal_st.py`
- `backend/services/contabil/icms_st.py` <- `backend/tests/test_retencoes_difal_st.py`
- `backend/services/contabil/retencoes.py` <- `backend/tests/test_retencoes_difal_st.py`
- `backend/services/contabil/score_saude.py` <- `backend/tests/test_comparador_indicadores_score.py`
- `backend/services/contabil/tabelas/aliquotas_icms.py` <- `backend/services/contabil/difal.py`
- `backend/services/email_service.py` <- `backend/routers/alertas.py`
- `backend/services/gerador_excel_pipeline.py` <- `backend/services/pipeline_extracao.py`
- `backend/services/importacao_service.py` <- `backend/routers/importacao.py`
- `backend/services/insights_engine.py` <- `backend/services/financeiro_service.py`
- `backend/services/leitor_excel.py` <- `backend/main.py`
- `backend/services/parsers/__init__.py` <- `backend/tests/test_santander_empresas_bugs_s21.py`
- `backend/services/parsers/bb.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/bradesco.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/bradesco_empresas/__init__.py` <- `backend/tests/test_parser_bradesco_net_empresas_lote_a.py`
- `backend/services/parsers/bs2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/btg.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/c6bank.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/caixa.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/cora.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/itau.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/mercado_pago.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/inter_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/itau_empresas_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/n2/itau_n2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/nubank.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/santander_empresas/santander_empresas_v2.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/sicredi.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/sumup.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/xp_extrato.py` <- `backend/services/extrator_pdf.py`
- `backend/services/parsers/xp_posicao.py` <- `backend/services/extrator_pdf.py`
- `backend/services/storage.py` <- `backend/main.py`
- `backend/services/template_dashboard.py` <- `backend/main.py`
- `backend/services/tributario/__init__.py` <- `backend/services/simulacao_tributaria_service.py`
- `backend/services/validacao/__init__.py` <- `backend/services/pipeline_extracao.py`
- `backend/services/verification/__init__.py` <- `backend/main.py`

### Modulos Isolados (Recorte COMPLETO)

- `backend/core/config.py`
- `backend/routers/__init__.py`
- `backend/services/contabil/tabelas/__init__.py`
- `backend/services/parsers/n2/__init__.py`
- `backend/services/parsers/parser_generico.py`
- `backend/services/parsers/parser_itau_mensal.py`
- `backend/services/parsers/parser_stone.py`
- `backend/services/parsers/santander_empresas/__init__.py`
- `backend/services/verification/tests/__init__.py`
- `backend/tests/__init__.py`
- `backend/tests/expectativas_extratos.py`
- `backend/tests/test_extrair_saldos_bradesco_net_empresas.py`
- `backend/tests_fase2/conftest_setup.py`
- `backend/tests_fase2/validar_completo.py`

## Comparativo Producao vs Completo

Diferenca de in-degree por arquivo do recorte PRODUCAO:
quanto o teste/script adiciona aos consumidores do modulo.

Apenas arquivos onde in-degree(completo) > in-degree(producao)
(ou seja, sao consumidos por testes/scripts alem da producao).

| Arquivo | in-degree producao | in-degree completo | delta |
| --- | --- | --- | --- |
| `backend/services/contabil/core.py` | 18 | 30 | +12 |
| `backend/data/database/__init__.py` | 17 | 25 | +8 |
| `backend/data/database/models.py` | 18 | 26 | +8 |
| `backend/services/extrator_pdf.py` | 4 | 12 | +8 |
| `backend/services/contabil/dre.py` | 3 | 7 | +4 |
| `backend/services/contabil/lucro_presumido.py` | 2 | 5 | +3 |
| `backend/services/contabil/balanco.py` | 1 | 3 | +2 |
| `backend/services/parsers/base.py` | 28 | 30 | +2 |
| `backend/services/parsers/santander_empresarial.py` | 2 | 4 | +2 |
| `backend/services/parsers/santander_ib_novo.py` | 1 | 3 | +2 |
| `backend/services/simulacao_tributaria_service.py` | 1 | 3 | +2 |
| `backend/services/tributario/lucro_presumido.py` | 1 | 3 | +2 |
| `backend/services/validacao/classificador_confianca.py` | 1 | 3 | +2 |
| `backend/services/validacao/validador_saldos.py` | 1 | 3 | +2 |
| `backend/data/database/config.py` | 16 | 17 | +1 |
| `backend/main.py` | 0 | 1 | +1 |
| `backend/services/auth_utils.py` | 12 | 13 | +1 |
| `backend/services/categorias.py` | 0 | 1 | +1 |
| `backend/services/contabil/__init__.py` | 1 | 2 | +1 |
| `backend/services/contabil/cnae_presuncao.py` | 1 | 2 | +1 |
| `backend/services/contabil/comparador.py` | 0 | 1 | +1 |
| `backend/services/contabil/dfc.py` | 0 | 1 | +1 |
| `backend/services/contabil/difal.py` | 0 | 1 | +1 |
| `backend/services/contabil/icms_st.py` | 0 | 1 | +1 |
| `backend/services/contabil/indicadores.py` | 1 | 2 | +1 |
| `backend/services/contabil/lucro_real.py` | 1 | 2 | +1 |
| `backend/services/contabil/reforma.py` | 1 | 2 | +1 |
| `backend/services/contabil/retencoes.py` | 0 | 1 | +1 |
| `backend/services/contabil/score_saude.py` | 0 | 1 | +1 |
| `backend/services/contabil/simples_nacional.py` | 1 | 2 | +1 |

Total de arquivos producao com in-degree elevado por testes: **55**

### Arquivos Producao Vivos APENAS via Testes/Scripts

Aparecem orfaos no recorte producao mas sao referenciados no completo.
Atencao em Fase 2: NAO sao dead code, sao integration points de teste.

- `backend/main.py` (in-degree completo = 1)
- `backend/services/categorias.py` (in-degree completo = 1)
- `backend/services/contabil/comparador.py` (in-degree completo = 1)
- `backend/services/contabil/dfc.py` (in-degree completo = 1)
- `backend/services/contabil/difal.py` (in-degree completo = 1)
- `backend/services/contabil/icms_st.py` (in-degree completo = 1)
- `backend/services/contabil/retencoes.py` (in-degree completo = 1)
- `backend/services/contabil/score_saude.py` (in-degree completo = 1)
- `backend/services/parsers/__init__.py` (in-degree completo = 1)
- `backend/services/parsers/bradesco_empresas/__init__.py` (in-degree completo = 1)
