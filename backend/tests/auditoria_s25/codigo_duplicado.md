# Codigo Duplicado — S25 Fase 4

Audit estrutural sobre `backend/` (exceto tests/, venv, auditorias antigas).

## Sumario

- Total arquivos producao analisados: **134**
- Funcoes com mesmo nome em arquivos diferentes: **26**
- Funcoes com corpo identico (hash MD5): **3**
- Constantes ALL-CAPS com mesmo valor: **34**
- Blocos >=10 linhas identicas: **184**
- Regex compartilhadas entre parsers: **6**

## 1. Funcoes com Mesmo Nome em Arquivos Diferentes

(Filtrando metodos comuns como `__init__`, `extrair`, `main`.)

Total relevante: **25**

- `_converter_data_abrev` (corpos diferentes)
  - `backend/services/parsers/itau.py:142-147`
  - `backend/services/parsers/itau_empresas.py:146-150`
- `_e_linha_skip` (corpos diferentes)
  - `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:65-73`
  - `backend/services/parsers/n2/itau_n2.py:49-56`
- `_get` (corpos diferentes)
  - `backend/services/contabil/balanco.py:99-103`
  - `backend/services/contabil/dre.py:70-75`
- `_get_admin` (corpos diferentes)
  - `backend/routers/auditoria.py:24-28`
  - `backend/routers/empresas.py:33-40`
- `_get_user` (corpos diferentes)
  - `backend/routers/empresas.py:495-499`
  - `backend/routers/equipe.py:28-41`
- `_limpar_descricao` (corpos diferentes)
  - `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:95-98`
  - `backend/services/parsers/n2/itau_n2.py:69-75`
- `_normalizar_float` (corpos diferentes)
  - `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:84-92`
  - `backend/services/parsers/n2/itau_n2.py:59-66`
- `_parse_data` (corpos diferentes)
  - `backend/services/gerador_excel.py:55-62`
  - `backend/services/parsers/santander_empresas/santander_empresas_v1.py:68-72`
  - `backend/services/validacao/validador_saldos.py:61-78`
- `_pct` (corpos diferentes)
  - `backend/services/financeiro_service.py:88-89`
  - `backend/services/insights_engine.py:33-34`
- `_safe` (corpos diferentes)
  - `backend/scripts/validacao_paralela_dre.py:58-59`
  - `backend/services/financeiro_service.py:59-61`
- `_to_dec` (corpos diferentes)
  - `backend/scripts/validacao_paralela_dre.py:62-65`
  - `backend/services/financeiro_service.py:72-78`
  - `backend/services/motor_narrativa.py:20-25`
  - `backend/services/score_saude.py:11-16`
- `_to_float` **[CORPO IDENTICO]**
  - `backend/services/gerador_excel.py:47-52`
  - `backend/services/gerador_excel_contabil.py:48-53`
- `_variacao` (corpos diferentes)
  - `backend/routers/orcamento.py:72-76`
  - `backend/services/financeiro_service.py:92-95`
- `aplicar_categorias` (corpos diferentes)
  - `backend/services/categorias.py:335-398`
  - `backend/services/extrator_pdf.py:1648-1747`
- `aprovar_usuario` (corpos diferentes)
  - `backend/main.py:1190-1213`
  - `backend/routers/master.py:443-457`
- `atualizar_empresa` (corpos diferentes)
  - `backend/main.py:2592-2627`
  - `backend/routers/empresas.py:292-372`
- `calcular` (corpos diferentes)
  - `backend/services/tributario/lucro_presumido.py:26-130`
  - `backend/services/tributario/lucro_real.py:30-139`
  - `backend/services/tributario/reforma.py:32-84`
  - `backend/services/tributario/simples_nacional.py:45-99`
- `categorizar` (corpos diferentes)
  - `backend/scripts/validacao_paralela_dre.py:118-136`
  - `backend/services/categorizacao_extrato.py:207-249`
- `comparar_regimes` (corpos diferentes)
  - `backend/routers/financeiro.py:253-289`
  - `backend/services/contabil/comparador.py:88-191`
- `criar_empresa` (corpos diferentes)
  - `backend/main.py:2525-2583`
  - `backend/routers/empresas.py:232-288`
- `deletar_template` (corpos diferentes)
  - `backend/routers/importacao.py:285-295`
  - `backend/services/importacao_service.py:413-419`
- `excluir_usuario` (corpos diferentes)
  - `backend/main.py:1296-1316`
  - `backend/routers/master.py:512-527`
- `get_current_user` (corpos diferentes)
  - `backend/main.py:818-834`
  - `backend/routers/equipe.py:44-48`
  - `backend/services/auth_utils.py:63-87`
- `get_gestor_or_admin` (corpos diferentes)
  - `backend/routers/equipe.py:51-58`
  - `backend/services/auth_utils.py:101-110`
- `listar_templates` (corpos diferentes)
  - `backend/routers/importacao.py:263-269`
  - `backend/services/importacao_service.py:399-410`

## 2. Funcoes com Corpo Identico (hash MD5)

### Hash `a7976cd5` — 6 linhas
- `backend/services/gerador_excel.py:47-52` — funcao `_to_float`
- `backend/services/gerador_excel_contabil.py:48-53` — funcao `_to_float`

### Hash `e86f3254` — 6 linhas
- `backend/services/motor_narrativa.py:20-25` — funcao `_to_dec`
- `backend/services/score_saude.py:11-16` — funcao `_to_dec`

## 3. Constantes ALL-CAPS Duplicadas

### Valor: `re.compile(`
- `backend/services/motor_classificacao.py:20` — `FILTRO_SALDO`
- `backend/services/motor_classificacao.py:24` — `FILTRO_TOTAIS`
- `backend/services/parsers/bb.py:53` — `_RE_VALOR`
- `backend/services/parsers/bb.py:59` — `_RE_DATA_TRUNC_VALOR`
- `backend/services/parsers/bb.py:66` — `_RE_CONTINUACAO`
- `backend/services/parsers/bradesco.py:36` — `_RE_LINHA_DATA`
- `backend/services/parsers/bradesco.py:41` — `_RE_LINHA_DOC`
- `backend/services/parsers/bradesco.py:46` — `_RE_LINHA_INLINE`
- `backend/services/parsers/bradesco.py:51` — `_RE_LINHA_DATA_INLINE`
- `backend/services/parsers/c6bank.py:29` — `_RE_TRANSACAO`
- `backend/services/parsers/caixa.py:36` — `_RE_DOC_FULL`
- `backend/services/parsers/caixa.py:42` — `_RE_DOC_SPLIT`
- `backend/services/parsers/caixa.py:47` — `_RE_TIMESTAMP_VALOR`
- `backend/services/parsers/cora.py:26` — `_RE_TRANSACAO`
- `backend/services/parsers/inter.py:36` — `_RE_DATA_HEADER`
- `backend/services/parsers/inter.py:41` — `_RE_TRANSACAO`
- `backend/services/parsers/itau.py:41` — `_RE_DATA_ABREV`
- `backend/services/parsers/itau.py:50` — `_RE_LINHA`
- `backend/services/parsers/itau_empresas.py:30` — `_RE_LINHA`
- `backend/services/parsers/mercado_pago.py:25` — `_RE_LINHA_PRINCIPAL`
- `backend/services/parsers/mercado_pago.py:30` — `_RE_DATE_DESC`
- `backend/services/parsers/mercado_pago.py:35` — `_RE_DATE_ID_VALOR`
- `backend/services/parsers/nubank.py:39` — `_RE_DATA_DIA`
- `backend/services/parsers/nubank.py:44` — `_RE_DATA_DIA_PREFIX`
- `backend/services/parsers/nubank.py:50` — `_RE_VALOR_LINHA`
- `backend/services/parsers/nubank.py:56` — `_RE_VALOR_INLINE`
- `backend/services/parsers/nubank.py:61` — `_RE_TABELA`
- `backend/services/parsers/pagbank.py:34` — `_RE_DATA_VALOR_SOLO`
- `backend/services/parsers/pagbank.py:39` — `_RE_TX_INLINE`
- `backend/services/parsers/pagbank.py:44` — `_RE_PERIODO`
- `backend/services/parsers/safra.py:41` — `_RE_TX`
- `backend/services/parsers/safra.py:49` — `_RE_SALDO_DIA`
- `backend/services/parsers/safra.py:54` — `_RE_PERIODO`
- `backend/services/parsers/santander.py:26` — `_RE_TRANSACAO`
- `backend/services/parsers/santander_consolidado.py:33` — `_RE_VALOR_FIM`
- `backend/services/parsers/santander_empresarial.py:35` — `_RE_DATA_EXTENSO`
- `backend/services/parsers/santander_empresarial.py:41` — `_RE_TX_APP`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:27` — `_RE_DATA_HEADER`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:34` — `_RE_TRANSACAO`
- `backend/services/parsers/santander_ib_novo.py:58` — `_RE_TRANSACAO`
- `backend/services/parsers/stone.py:43` — `_RE_LINHA_TEXTO`
- `backend/services/parsers/stone.py:50` — `_RE_LINHA_SIMPLES`
- `backend/services/parsers/stone.py:56` — `_RE_SALDO_TAIL_N1`
- `backend/services/parsers/stone_n2.py:22` — `_RE_DATA_INICIO`
- `backend/services/parsers/stone_n2.py:28` — `_RE_LINHA_COMPLETA`
- `backend/services/parsers/stone_n2.py:36` — `_RE_DATA_SALDO_TAIL_N2`
- `backend/services/parsers/xp_extrato.py:24` — `_RE_LANCAMENTO`
- `backend/services/parsers/xp_extrato.py:29` — `_RE_LANCAMENTO_INLINE`

### Valor: `Decimal("0")`
- `backend/services/contabil/balanco.py:31` — `_ZERO`
- `backend/services/contabil/comparador.py:21` — `_ZERO`
- `backend/services/contabil/core.py:63` — `_ZERO`
- `backend/services/contabil/dfc.py:36` — `_ZERO`
- `backend/services/contabil/difal.py:25` — `_ZERO`
- `backend/services/contabil/dre.py:29` — `_ZERO`
- `backend/services/contabil/icms_st.py:21` — `_ZERO`
- `backend/services/contabil/indicadores.py:16` — `_ZERO`
- `backend/services/contabil/lucro_presumido.py:38` — `_ZERO`
- `backend/services/contabil/lucro_real.py:38` — `_ZERO`
- `backend/services/contabil/reforma.py:42` — `_ZERO`
- `backend/services/contabil/retencoes.py:25` — `_ZERO`
- `backend/services/contabil/score_saude.py:24` — `_ZERO`
- `backend/services/contabil/simples_nacional.py:35` — `_ZERO`

### Valor: `BankVerifier._SALDO_KEYWORDS + [`
- `backend/services/verification/verifiers.py:60` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:98` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:131` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:171` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:201` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:222` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:252` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:277` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:322` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:352` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:372` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:433` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:453` — `_SALDO_KEYWORDS`
- `backend/services/verification/verifiers.py:485` — `_SALDO_KEYWORDS`

### Valor: `Decimal('0.02')`
- `backend/services/conciliacao/matchers/bb.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/bradesco.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/c6bank.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/caixa.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/inter.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/itau.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/mercado_pago.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/nubank.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/pagbank.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/santander.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/stone.py:6` — `TOLERANCIA_VALOR`

### Valor: `money_fiscal("0.01")`
- `backend/services/contabil/difal.py:26` — `_TOL`
- `backend/services/contabil/icms_st.py:22` — `_TOL`
- `backend/services/contabil/lucro_presumido.py:39` — `_TOL`
- `backend/services/contabil/lucro_real.py:39` — `_TOL`
- `backend/services/contabil/reforma.py:43` — `_TOL`
- `backend/services/contabil/retencoes.py:26` — `_TOL`
- `backend/services/contabil/simples_nacional.py:40` — `_TOL_MONEY`

### Valor: `re.compile(r'\b(20\d{2})\b')`
- `backend/services/parsers/bb.py:43` — `_RE_ANO`
- `backend/services/parsers/bradesco.py:33` — `_RE_ANO`
- `backend/services/parsers/c6bank.py:25` — `_RE_ANO`
- `backend/services/parsers/itau.py:55` — `_RE_ANO`
- `backend/services/parsers/itau_empresas.py:34` — `_RE_ANO`
- `backend/services/parsers/nubank.py:65` — `_RE_ANO`
- `backend/services/parsers/stone.py:40` — `_RE_ANO`

### Valor: `frozenset({`
- `backend/services/contabil/comparador.py:24` — `ATIVIDADES_VALIDAS`
- `backend/services/contabil/tabelas/aliquotas_icms.py:15` — `UFS_VALIDAS`
- `backend/services/contabil/tabelas/servicos_retencao.py:25` — `SERVICOS_IRRF_15`
- `backend/services/contabil/tabelas/servicos_retencao.py:42` — `SERVICOS_CSRF_465`
- `backend/services/contabil/tabelas/servicos_retencao.py:56` — `TIPOS_SERVICO_VALIDOS`

### Valor: `"legado"`
- `backend/services/financeiro_service.py:33` — `_DRE_ENGINE_RAW`
- `backend/services/financeiro_service.py:39` — `_DRE_ENGINE_RAW`
- `backend/services/simulacao_tributaria_service.py:46` — `_LP_ENGINE_RAW`
- `backend/services/simulacao_tributaria_service.py:52` — `_LP_ENGINE_RAW`

### Valor: `'Santander'`
- `backend/services/parsers/santander.py:23` — `BANCO`
- `backend/services/parsers/santander_consolidado.py:21` — `BANCO`
- `backend/services/parsers/santander_empresarial.py:22` — `BANCO`
- `backend/services/parsers/santander_ib_novo.py:42` — `BANCO`

### Valor: `True`
- `backend/main.py:396` — `_USE_REDIS`
- `backend/services/auth_utils.py:26` — `_ZXCVBN_DISPONIVEL`
- `backend/services/ocr_fallback.py:24` — `_DEPS_OK`

### Valor: `False`
- `backend/main.py:400` — `_USE_REDIS`
- `backend/services/auth_utils.py:23` — `_ZXCVBN_DISPONIVEL`
- `backend/services/ocr_fallback.py:26` — `_DEPS_OK`

### Valor: `re.compile(r'^\d{2}/\d{2}/\d{4}$')`
- `backend/main.py:728` — `_DATE_BR_RE`
- `backend/services/parsers/base.py:36` — `_RE_DATA_VALIDA`
- `backend/services/parsers/sicredi.py:75` — `_RE_DATA`

### Valor: `money("0.01")`
- `backend/services/contabil/balanco.py:32` — `_TOL`
- `backend/services/contabil/dfc.py:37` — `_TOL`
- `backend/services/contabil/dre.py:30` — `_TOL`

### Valor: `dict[str, dict] = {`
- `backend/services/contabil/cnae_presuncao.py:39` — `CNAE_PARA_PRESUNCAO`
- `backend/services/contabil/tabelas/reforma_tributaria.py:94` — `REGIMES_ESPECIFICOS`
- `backend/services/importacao_service.py:430` — `_MODELOS`

### Valor: `dict[str, str] = {`
- `backend/services/contabil/comparador.py:42` — `_MAPA_ANEXO`
- `backend/services/extrator_pdf.py:919` — `FALLBACK_PARSERS`
- `backend/services/extrator_pdf.py:1561` — `_NOME_BANCO_EXIBICAO`

### Valor: `Decimal('0')`
- `backend/services/financeiro_service.py:69` — `_ZERO`
- `backend/services/motor_narrativa.py:9` — `_ZERO`
- `backend/services/score_saude.py:8` — `_ZERO`

### Valor: `re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')`
- `backend/services/parsers/bb.py:49` — `_RE_DATA_DESC`
- `backend/services/parsers/bs2.py:26` — `_RE_DATA_INICIO`
- `backend/services/parsers/santander_empresarial.py:25` — `_RE_DATA_INICIO`

### Valor: `re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')`
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:26` — `_RE_VALOR`
- `backend/services/parsers/btg.py:33` — `_RE_VALOR`
- `backend/services/parsers/n2/itau_n2.py:28` — `_RE_VALOR`

### Valor: `os.environ.get("CONTROLLO_MASTER_SLUG", "controllobpo")`
- `backend/main.py:446` — `ESCRITORIO_MASTER_SLUG`
- `backend/routers/master.py:27` — `_MASTER_SLUG`

### Valor: `50 * 1024 * 1024`
- `backend/main.py:1722` — `MAX_FILE_SIZE`
- `backend/main.py:1876` — `MAX_FILE_SIZE`

### Valor: `dict[str, list[dict]] = {`
- `backend/routers/importacao.py:64` — `_EXEMPLOS`
- `backend/services/importacao_service.py:24` — `CAMPOS_DESTINO`

### Valor: `os.path.join(os.path.dirname(os.path.abspath(__file__)),`
- `backend/scripts/seed_empresas_validacao_paralela.py:24` — `DB_PATH`
- `backend/scripts/validacao_paralela_dre.py:28` — `DB_PATH`

### Valor: `Decimal('0.05')`
- `backend/services/conciliacao/matchers/sicredi.py:6` — `TOLERANCIA_VALOR`
- `backend/services/conciliacao/matchers/universal.py:6` — `TOLERANCIA_VALOR`

### Valor: `Decimal("0.32")`
- `backend/services/contabil/cnae_presuncao.py:25` — `_FALLBACK_IRPJ`
- `backend/services/contabil/cnae_presuncao.py:26` — `_FALLBACK_CSLL`

### Valor: `Decimal("4800000")`
- `backend/services/contabil/comparador.py:22` — `_TETO_SIMPLES`
- `backend/services/contabil/simples_nacional.py:36` — `_TETO_SIMPLES`

### Valor: `Decimal("0.000001")`
- `backend/services/contabil/core.py:61` — `_Q_RATE`
- `backend/services/contabil/core.py:62` — `_Q_PCT`

### Valor: `rate("0.15")       # Lei 9.249/95 art. 3`
- `backend/services/contabil/lucro_presumido.py:44` — `ALIQUOTA_IRPJ`
- `backend/services/contabil/lucro_real.py:43` — `ALIQUOTA_IRPJ`

### Valor: `rate("0.10")       # Lei 9.249/95 art. 3 par. 1`
- `backend/services/contabil/lucro_presumido.py:45` — `ALIQUOTA_IRPJ_ADIC`
- `backend/services/contabil/lucro_real.py:44` — `ALIQUOTA_IRPJ_ADIC`

### Valor: `frozenset([`
- `backend/services/contabil/lucro_presumido.py:52` — `BASES_IRPJ_VALIDAS`
- `backend/services/contabil/lucro_presumido.py:60` — `BASES_CSLL_VALIDAS`

### Valor: `dict[str, Decimal] = {`
- `backend/services/contabil/tabelas/aliquotas_icms.py:47` — `ALIQUOTA_INTERNA_PADRAO`
- `backend/services/contabil/tabelas/aliquotas_icms.py:59` — `FCP_POR_UF`

## 4. Blocos >=10 Linhas Identicas Entre Arquivos

### Bloco `c9cd8b59` — 4 arquivos
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:118-128`
- `backend/services/parsers/btg.py:82-92`
- `backend/services/parsers/n2/itau_n2.py:92-102`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:88-98`

### Bloco `3bb5cee3` — 4 arquivos
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:120-130`
- `backend/services/parsers/btg.py:84-94`
- `backend/services/parsers/n2/itau_n2.py:94-104`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:90-100`

### Bloco `fb95e541` — 3 arquivos
- `backend/services/contabil/balanco.py:14-25`
- `backend/services/contabil/dfc.py:17-28`
- `backend/services/contabil/dre.py:12-23`

### Bloco `515edac4` — 3 arquivos
- `backend/services/contabil/balanco.py:16-26`
- `backend/services/contabil/dfc.py:19-29`
- `backend/services/contabil/dre.py:14-24`

### Bloco `82a475ac` — 3 arquivos
- `backend/services/contabil/balanco.py:17-27`
- `backend/services/contabil/dfc.py:20-30`
- `backend/services/contabil/dre.py:15-25`

### Bloco `ed4a66f3` — 3 arquivos
- `backend/services/contabil/balanco.py:18-28`
- `backend/services/contabil/dfc.py:21-31`
- `backend/services/contabil/dre.py:16-26`

### Bloco `7f6becf4` — 3 arquivos
- `backend/services/contabil/balanco.py:20-29`
- `backend/services/contabil/dfc.py:23-32`
- `backend/services/contabil/dre.py:18-27`

### Bloco `d3539d3b` — 3 arquivos
- `backend/services/parsers/bb.py:159-170`
- `backend/services/parsers/itau.py:164-175`
- `backend/services/parsers/itau_empresas.py:170-181`

### Bloco `7eebb1ab` — 3 arquivos
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:115-125`
- `backend/services/parsers/n2/itau_n2.py:89-99`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:85-95`

### Bloco `88fc8b2b` — 3 arquivos
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:116-126`
- `backend/services/parsers/n2/itau_n2.py:90-100`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:86-96`

### Bloco `3097c2a5` — 3 arquivos
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:117-127`
- `backend/services/parsers/n2/itau_n2.py:91-101`
- `backend/services/parsers/santander_empresas/santander_empresas_v1.py:87-97`

### Bloco `a9860114` — 2 arquivos
- `backend/main.py:2425-2435`
- `backend/routers/empresas.py:201-211`

### Bloco `55f95e8c` — 2 arquivos
- `backend/main.py:2427-2436`
- `backend/routers/empresas.py:203-212`

### Bloco `8afa700e` — 2 arquivos
- `backend/routers/financeiro.py:48-57`
- `backend/routers/orcamento.py:33-42`

### Bloco `d2c7ca73` — 2 arquivos
- `backend/services/contabil/balanco.py:21-31`
- `backend/services/contabil/dre.py:19-29`

### Bloco `d32e7d6b` — 2 arquivos
- `backend/services/contabil/balanco.py:22-32`
- `backend/services/contabil/dre.py:20-30`

### Bloco `ec830482` — 2 arquivos
- `backend/services/contabil/balanco.py:23-37`
- `backend/services/contabil/dre.py:21-35`

### Bloco `e74338a6` — 2 arquivos
- `backend/services/contabil/lucro_presumido.py:20-31`
- `backend/services/contabil/simples_nacional.py:13-24`

### Bloco `ce84d83d` — 2 arquivos
- `backend/services/contabil/lucro_presumido.py:22-32`
- `backend/services/contabil/simples_nacional.py:15-25`

### Bloco `83d00d0c` — 2 arquivos
- `backend/services/contabil/lucro_presumido.py:23-33`
- `backend/services/contabil/simples_nacional.py:16-26`

## 5. Regex Compartilhadas Entre Parsers

### Padrao: `r'\b(20\d{2})\b'`
- `backend/services/parsers/bb.py:43` — `_RE_ANO`
- `backend/services/parsers/bradesco.py:33` — `_RE_ANO`
- `backend/services/parsers/c6bank.py:25` — `_RE_ANO`
- `backend/services/parsers/itau.py:55` — `_RE_ANO`
- `backend/services/parsers/itau_empresas.py:34` — `_RE_ANO`
- `backend/services/parsers/nubank.py:65` — `_RE_ANO`
- `backend/services/parsers/stone.py:40` — `_RE_ANO`

### Padrao: `r'^(\d{2}/\d{2}/\d{4})\s+(.+)$'`
- `backend/services/parsers/bb.py:49` — `_RE_DATA_DESC`
- `backend/services/parsers/bs2.py:26` — `_RE_DATA_INICIO`
- `backend/services/parsers/santander_empresarial.py:25` — `_RE_DATA_INICIO`

### Padrao: `r'-?\d{1,3}(?:\.\d{3})*,\d{2}'`
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:26` — `_RE_VALOR`
- `backend/services/parsers/btg.py:33` — `_RE_VALOR`
- `backend/services/parsers/n2/itau_n2.py:28` — `_RE_VALOR`

### Padrao: `r'^\d{2}/\d{2}/\d{4}$'`
- `backend/services/parsers/base.py:36` — `_RE_DATA_VALIDA`
- `backend/services/parsers/sicredi.py:75` — `_RE_DATA`

### Padrao: `r'^(\d{2}/\d{2}/\d{4})\s+(.*)'`
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:29` — `_RE_DATA_LINHA`
- `backend/services/parsers/btg.py:30` — `_RE_DATA`

### Padrao: `r'(\s+\d+)+\s*$'`
- `backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py:62` — `_RE_TRAILING_INTS`
- `backend/services/parsers/n2/itau_n2.py:36` — `_RE_TRAILING_NUMS`

## 6. Recomendacoes preliminares por caso

### 6.1 Helpers Decimal/numericos (alta prioridade — ganho rapido)

| Caso | Arquivos | Recomendacao |
| --- | --- | --- |
| `_to_dec` (4 arquivos: `financeiro_service.py`, `motor_narrativa.py`, `score_saude.py`, `scripts/validacao_paralela_dre.py`) — 2 deles com **CORPO IDENTICO** | 4 | **EXTRAIR** para `services/_decimal_utils.py` ou `services/contabil/core.py` |
| `_to_float` **CORPO IDENTICO** em `gerador_excel.py` + `gerador_excel_contabil.py` | 2 | **EXTRAIR** para utilitario comum (parte da `services/exportacao/` na S5) |
| `_pct`, `_pct_safe`, `_safe`, `_variacao`, `_div_safe` em `financeiro_service`, `insights_engine`, `routers/orcamento` | 3+ | **EXTRAIR** para `services/contabil/_aritmetica_segura.py` |
| `_ZERO = Decimal("0")` em **14 arquivos** de `services/contabil/` | 14 | **EXTRAIR** — mover para `services/contabil/core.py` (ja exporta `to_decimal`); demais arquivos importam |
| `Decimal('0')` como `_ZERO` em `financeiro_service.py`, `motor_narrativa.py`, `score_saude.py` | 3 | **EXTRAIR** — usar mesmo helper acima (uniformizar `Decimal("0")` vs `Decimal('0')`) |

### 6.2 Tolerancias e constantes contabeis (alta prioridade)

| Caso | Arquivos | Recomendacao |
| --- | --- | --- |
| `_TOL = money_fiscal("0.01")` em 7 arquivos de `contabil/` (difal, icms_st, lucro_presumido, lucro_real, reforma, retencoes, simples_nacional) | 7 | **EXTRAIR** — mover para `contabil/core.py` ou `contabil/_constantes.py` |
| `_TOL = money("0.01")` em 3 arquivos de `contabil/` (balanco, dfc, dre) | 3 | **EXTRAIR** — mesma extracao acima (notar que sao 2 funcoes diferentes: `money` vs `money_fiscal` — uniformizar antes ou manter como 2 constantes distintas) |
| `TOLERANCIA_VALOR = Decimal('0.02')` em **11 matchers** de `conciliacao/` (bb, bradesco, c6bank, caixa, inter, itau, mercado_pago, nubank, pagbank, santander, stone) | 11 | **EXTRAIR** — `services/conciliacao/matchers/base.py` ja existe (in-degree 13); mover constante pra la |
| `TOLERANCIA_VALOR = Decimal('0.05')` em `matchers/sicredi.py` + `matchers/universal.py` | 2 | **MANTER** — sicredi e universal usam tolerancia maior (regra de negocio explicita); deixar comentado por que diverge |
| `_TETO_SIMPLES = Decimal("4800000")` em `contabil/comparador.py` + `contabil/simples_nacional.py` | 2 | **EXTRAIR** — `contabil/_constantes.py` ou `contabil/tabelas/limites.py` |
| `ALIQUOTA_IRPJ`, `ALIQUOTA_IRPJ_ADIC` em `lucro_presumido.py` + `lucro_real.py` | 2 | **EXTRAIR** — `contabil/tabelas/aliquotas_federais.py` |

### 6.3 Regex de parsers (alta prioridade — clusterizacao por familia)

| Regex | Arquivos | Recomendacao |
| --- | --- | --- |
| `re.compile(r'\b(20\d{2})\b')` como `_RE_ANO` em **7 parsers** (bb, bradesco, c6bank, itau, itau_empresas, nubank, stone) | 7 | **EXTRAIR** — `services/parsers/base.py` ja e in-degree 28; adicionar `_RE_ANO` la |
| `re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')` como `_RE_VALOR` em 3 parsers de empresa (bradesco_net_empresas, btg, n2/itau_n2) | 3 | **EXTRAIR** — para `parsers/base.py` ou `parsers/_n2_base.py` (ver §6.4) |
| `re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')` como `_RE_DATA_DESC` em bb + bs2 + santander_empresarial | 3 | **EXTRAIR** — `parsers/base.py` |
| `re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)')` em bradesco_net_empresas + btg | 2 | **EXTRAIR** — `parsers/base.py` (variacao com `*` vs `+` — quase identica) |
| `re.compile(r'^\d{2}/\d{2}/\d{4}$')` em main.py + parsers/base.py + parsers/sicredi.py | 3 | **EXTRAIR** — ja em `parsers/base.py:36`; sicredi e main devem importar de la |
| `re.compile(r'(\s+\d+)+\s*$')` (trailing ints) em bradesco_net_empresas + n2/itau_n2 | 2 | **EXTRAIR** — `parsers/base.py` ou subbase n2 |

### 6.4 Cluster de parsers "empresa" — duplicacao em massa

**Achado mais critico da Fase 4**: 4 parsers de empresas (`bradesco_net_empresas`, `btg`, `n2/itau_n2`, `santander_empresas_v1`) compartilham:
- 4 blocos identicos de 11 linhas (hash `c9cd8b59`, `3bb5cee3`, etc)
- Helpers privados duplicados (`_e_linha_skip`, `_limpar_descricao`, `_normalizar_float`) em pelo menos 2 arquivos
- Constante `_RE_VALOR` (regex BR) em 3 deles
- Constante `_RE_TRAILING_INTS` em 2 deles

**Recomendacao**: criar **`services/parsers/_empresa_base.py`** (ou `_n2_base.py`) que encapsula:
- Regex `_RE_VALOR`, `_RE_DATA_LINHA`, `_RE_TRAILING_INTS`
- Helpers `_e_linha_skip`, `_limpar_descricao`, `_normalizar_float`
- O bloco de loop principal duplicado (parecem ser pre-processamento de linhas).

Cada parser de empresa herda dessa base e sobrescreve apenas o que e especifico.

**Estimativa de reducao**: 4 arquivos × ~30 linhas duplicadas = ~120 linhas removiveis sem perda de funcionalidade.

### 6.5 Cluster contabil — boilerplate de imports/constantes

3 arquivos de `contabil/` (`balanco.py`, `dfc.py`, `dre.py`) compartilham 5 blocos identicos de 12 linhas (hashes `fb95e541`, `515edac4`, `82a475ac`, `ed4a66f3`, `7f6becf4`). Sao prologos identicos: imports + `_ZERO`/`_TOL` + setup.

**Recomendacao**: a maior parte deveria estar em `contabil/core.py` (ja in-degree 18). Migrar imports comuns para la.

Tambem `lucro_presumido.py` + `simples_nacional.py` tem 3 blocos duplicados (hashes `e74338a6`, `ce84d83d`, `83d00d0c`) — mesmo padrao.

### 6.6 Auth helpers (routers vs services/auth_utils.py)

`get_current_user`, `get_gestor_or_admin`, `_get_user`, `_get_admin` aparecem em:
- `services/auth_utils.py` (versao "oficial", in-degree=12)
- `main.py:818` (`get_current_user`)
- `routers/equipe.py:28-58` (varias copias)
- `routers/auditoria.py:24`, `routers/empresas.py:33,495`

**Recomendacao**: **EXTRAIR** todos para `services/auth_utils.py`, eliminar copias. Ja ha precedente forte (12 importadores). Provavel resquicio de duplicacao do tempo em que `main.py` continha tudo. Endereçado naturalmente por **decomposicao do main.py (S30+)**.

### 6.7 Endpoints duplicados main.py vs routers/

| Endpoint | main.py | router |
| --- | --- | --- |
| `aprovar_usuario` | `main.py:1190` | `routers/master.py:443` |
| `excluir_usuario` | `main.py:1296` | `routers/master.py:512` |
| `criar_empresa` | `main.py:2525` | `routers/empresas.py:232` |
| `atualizar_empresa` | `main.py:2592` | `routers/empresas.py:292` |

**Recomendacao**: **INVESTIGAR** — pode ser:
- Duplicacao real (main.py ainda nao foi limpo apos extracao para router)
- Versoes em URL paths diferentes (`/api/v1` vs `/api/admin`)

A acao depende do achado, mas tudo aponta para "main.py virou monolito legado precisando de remocao". Endereçar na S30+ (decomposicao main.py).

Bloco identico `main.py:2425-2435` vs `routers/empresas.py:201-211` reforca.

### 6.8 Casos a MANTER (especializacao real)

| Caso | Arquivos | Motivo |
| --- | --- | --- |
| `BANCO = 'Santander'` em 4 parsers Santander (santander, santander_consolidado, santander_empresarial, santander_ib_novo) | 4 | Especializacao por variante de extrato Santander; nao da pra unificar sem perder polimorfismo. |
| `def calcular(...)` em 4 arquivos de `tributario/` (lucro_presumido, lucro_real, reforma, simples_nacional) | 4 | Cada regime tributario tem assinatura propria; **MANTER** com base abstrata em `tributario/__init__.py` se nao houver. |
| `'legado' / 'novo'` strings em `financeiro_service.py` + `simulacao_tributaria_service.py` | 2 | Cada engine tem flag propria (`CONTROLLO_DRE_ENGINE` vs `CONTROLLO_LP_ENGINE`); strings sao comuns mas sao chaves separadas. **MANTER**. |

### 6.9 Casos a INVESTIGAR

| Caso | Motivo |
| --- | --- |
| `_parse_data` em `gerador_excel.py`, `santander_empresas_v1.py`, `validador_saldos.py` | 3 implementacoes em contextos diferentes — formato de entrada e validacao podem divergir; investigar antes de unificar |
| `categorizar` em `scripts/validacao_paralela_dre.py` + `services/categorizacao_extrato.py` | Provavel script de validacao usando logica diferente da producao — investigar |
| `aplicar_categorias` em `categorias.py` (GRUPO B sub-A) + `extrator_pdf.py:1648` | Ja confirmado: producao usa extrator_pdf; categorias.py e duplicata morta — REMOVER (S26) |
| `comparar_regimes` em `routers/financeiro.py` (endpoint) + `contabil/comparador.py` (GRUPO B sub-A) | Endpoint nao usa o servico — duplicacao funcional — REMOVER `comparador.py` (S26 sub-A) |
| `deletar_template`, `listar_templates` em `routers/importacao.py` + `services/importacao_service.py` | Padrao `from services import importacao_service as svc`; router chama servico, definicoes paralelas. **INVESTIGAR** se sao mesmo deletar/listar diferentes (template tem 2 escopos? user vs empresa?) |

## 7. Estimativa quantitativa de remocao por refator

Cifras conservadoras (sem contar testes adicionados/movidos):

| Categoria | Linhas removiveis estimadas |
| --- | --- |
| Helpers Decimal/numericos extraidos (§6.1) | ~50-80 (4 funcoes × ~10-20 linhas) |
| Constantes contabeis duplicadas removidas (§6.2) | ~40-60 (24 declaracoes redundantes × ~2 linhas) |
| Regex de parsers extraidas (§6.3) | ~30-40 (12 declaracoes × ~3 linhas) |
| Parsers empresa unificados (§6.4) | ~120 (cluster bradesco_net + btg + itau_n2 + santander_v1) |
| Boilerplate contabil migrado (§6.5) | ~60 (5 blocos × 12 linhas em 3 arquivos) |
| Auth helpers consolidados em auth_utils (§6.6) | ~40-60 |
| Endpoints duplicados main.py removidos (§6.7) | ~150-200 (6+ endpoints × ~25-30 linhas) |
| **TOTAL ESTIMADO** | **~490-720 linhas** |

Atencao: refators §6.4-§6.7 envolvem mudanca de comportamento parcial e merecem PRs proprias com cobertura de teste. Apenas §6.1-§6.3 sao quase-mecanicos.
