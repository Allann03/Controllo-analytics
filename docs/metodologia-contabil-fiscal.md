# Metodologia Contabil-Fiscal -- Controllo BPO Analytics

## Versao do Calculo
Versao atual: 3.0.0 (constante `VERSAO_CALCULO` em `services/contabil/core.py`)

## Principios

1. **Todo valor monetario e Decimal.** Float e proibido em caminhos contabeis e fiscais.
2. **Contabilidade usa ROUND_HALF_EVEN** (`money()`). Tributacao usa **ROUND_HALF_UP** (`money_fiscal()`).
3. **Toda funcao top-level retorna `ResultadoCalculo`** com memoria auditavel (`MemoriaCalculo`).
4. **Invariantes contabeis sao verificadas em runtime** e violacoes sao logadas antes do raise.
5. **Regra de ouro:** se o valor vai para uma guia de recolhimento (DARF, DAS, GPS, GNRE), use `money_fiscal()`. Caso contrario, `money()`.

## Normas Adotadas

| Norma | Escopo | Sub-bloco |
|---|---|---|
| CPC 26 (R2) | DRE, BP | 3B, 3C |
| CPC 03 (R2) | DFC | 3D |
| RIR/2018 | IRPJ, CSLL, Lucro Real, Presumido | 3F, 3G |
| IN RFB 1.700/2017 | Arredondamento fiscal (ROUND_HALF_UP) | 3A (core) |
| LC 123/2006 | Simples Nacional | 3E |
| LC 214/2025 | Reforma Tributaria (CBS/IBS) | 3H |
| Lei 9.718/1998 | PIS/COFINS cumulativo | 3F |
| Lei 10.637/2002 | PIS nao-cumulativo | 3G |
| Lei 10.833/2003 | COFINS nao-cumulativo | 3G |

*(Tabela sera expandida nos sub-blocos 3B--3K)*

## Decisoes de Design

### A. ROUND_HALF_EVEN vs ROUND_HALF_UP
- `money()` usa ROUND_HALF_EVEN (padrao internacional, IEEE 754, IFRS).
- `money_fiscal()` usa ROUND_HALF_UP (padrao RFB, IN 1.700/2017 Art. 7, par. 2).
- Diferenca aparece somente em `.005`: `money("100.445") = 100.44` vs `money_fiscal("100.445") = 100.45`.
- Divergir da RFB em guias fiscais gera centavos de diferenca que causam malha fina.

### B. ResultadoCalculo -- apenas top-level
- Funcoes de apuracao tributaria e relatorios (calcular_simples, get_dre, etc.) retornam `ResultadoCalculo`.
- Funcoes auxiliares internas retornam `Decimal` puro para evitar overhead.

### C. Norma -- Union[NormaContabil, str]
- `NormaContabil` e um `str Enum` com normas catalogadas.
- Strings livres aceitas para normas nao catalogadas (novas INs, ADEs).

### D. Unicode/Acentos em nomes de campo
- Docstrings e comentarios usam ASCII puro para compatibilidade maxima com encoding.
- Nomes de funcao e variavel sao ASCII puro (snake_case).

## DRE -- Versao 3.0.0

### Estrutura (17 linhas implementadas)

| # | Codigo | Descricao | Formula |
|---|---|---|---|
| 1 | 1 | Receita Bruta de Vendas/Servicos | campo direto |
| 2 | 2 | (-) Deducoes da Receita | campo direto |
| 3 | 3 | = Receita Liquida | [1] - [2] |
| 4 | 4 | (-) Custo dos Produtos/Servicos (CMV/CSV) | campo direto |
| 5 | 5 | = Lucro Bruto | [3] - [4] |
| 6 | 6a | (-) Despesas Administrativas | campo direto |
| 7 | 6b | (-) Despesas Comerciais | campo direto |
| 8 | 6c | (-) Outras Despesas Operacionais | campo direto |
| 9 | 6d | (-) Depreciacao e Amortizacao | campo direto |
| 10 | 7 | = EBIT (Resultado Operacional) | [5] - [6a] - [6b] - [6c] - [6d] |
| 11 | 8 | = EBITDA | [7] + [6d] |
| 12 | 9a | (-) Despesas Financeiras | campo direto |
| 13 | 9b | (+) Receitas Financeiras | campo direto (0 se ausente) |
| 14 | 10 | = LAIR (Lucro Antes IR/CSLL) | [7] - [9a] + [9b] |
| 15 | 11a | (-) IRPJ | campo direto (ou consolidado legado) |
| 16 | 11b | (-) CSLL | campo direto (0 se consolidado) |
| 17 | 12 | = Resultado Liquido do Exercicio | [10] - [11a] - [11b] |

### Invariantes verificadas em runtime

| ID | Invariante | Tolerancia |
|---|---|---|
| INV-1 | receita_liquida == receita_bruta - deducoes_receita | 0.01 |
| INV-2 | lucro_bruto == receita_liquida - custo_servicos | 0.01 |
| INV-3 | ebit == lucro_bruto - desp_adm - desp_com - outras_desp - d&a | 0.01 |
| INV-4 | ebitda == ebit + depreciacao_amortizacao | 0.01 |
| INV-5 | lair == ebit - despesas_financeiras + receitas_financeiras | 0.01 |
| INV-6 | resultado_liquido == lair - irpj - csll (ou ir_csll consolidado) | 0.01 |

### Correcoes Aplicadas

| ID | Bug | Norma violada | Efeito | Data |
|---|---|---|---|---|
| ALTO-1 | `ebit` incluia `despesas_financeiras` — era LAIR rotulado como EBIT | CPC 26 (R2) par. 82 | Reclassificacao entre linhas; Resultado Liquido inalterado (quando D&A=0) | 2026-04-11 |
| ALTO-1b (CRITICO-NEW-2) | `depreciacao_amortizacao` nunca subtraida na DRE | CPC 26 (R2) par. 102; Lei 6.404/76 art. 187 IV | Resultado Liquido superestimado por D&A/mes em toda empresa com D&A>0 | 2026-04-11 |

**ALTO-1:** EBIT = Lucro Bruto - Despesas Operacionais (sem financeiras, com D&A).
LAIR = EBIT - DFin + RFin. Campos separados no retorno.

**ALTO-1b:** Causa raiz: `financeiro_service.py:73` somava apenas `adm+com+fin+out`, omitindo
`depreciacao_amortizacao`. Descoberto durante validacao paralela (BLOCO 3B.2 Fase B).
Motor novo inclui D&A em despesas operacionais conforme CPC 26.

### Limitacoes transitorias

1. **IRPJ/CSLL consolidados:** modelo legado armazena em coluna unica `ir_csll`. Motor aceita
   separacao (campos `irpj`, `csll`) quando disponivel, com fallback para consolidado + aviso.
   Separacao contabil pendente -- BLOCO 3K.
2. **Receitas financeiras ausentes:** coluna nao existe no model `LancamentoMensal`. Motor aceita
   como parametro opcional (default 0) e emite aviso quando ausente. Coluna -- BLOCO 3K.
3. **Participacoes estatutarias:** nao tratadas (linhas 18-20 do Adendo A.1). Relevante apenas
   para S/A com estatuto. Implementacao -- BLOCO 3K se necessario.

## Historico de Versoes

- **3.0.0** (2026-04-11): Reestruturacao integral sob R3 do mandato de remediacao.
  - BLOCO 3A: `services/contabil/core.py` -- money, money_fiscal, rate, pct, to_decimal,
    MemoriaCalculo, ResultadoCalculo, IntegridadeContabilError, assertir_invariante.
  - BLOCO 3B.1: `services/contabil/dre.py` -- motor DRE isolado, 17 linhas, 6 invariantes,
    correcao ALTO-1 (EBIT vs LAIR), comparativo CPC 26, avisos transitorios.
  - BLOCO 3B.2: Integracao DRE ao endpoint com feature flag `CONTROLLO_DRE_ENGINE`,
    refactor de 3 paginas frontend, validacao paralela (36 comparacoes, 216 invariantes).
    Descoberta ALTO-1b (D&A omitida) durante validacao. Ref: `docs/debitos-descobertos.md`,
    `docs/validacao-dre-paralela.md`, `docs/comunicacao-clientes-correcao-dre.md`.
  - BLOCO 3C.1: `services/contabil/balanco.py` -- motor BP gerencial, invariante
    Ativo==Passivo+PL verificada em runtime (gap reportado sem corrigir),
    D&A acumulada observada, validacao cruzada DRE->LA, metodo assertir_fechamento.
    Ref: `docs/modelo-balanco-patrimonial-futuro.md`.
  - BLOCO 3D: `services/contabil/dfc.py` -- motor DFC metodo indireto conforme CPC 03 (R2),
    17 linhas (Oper/Invest/Financ), 6 invariantes, acoplamento explicito DRE+BP via
    parametros ResultadoCalculo, gap de reconciliacao com fluxos observados,
    investimento ajustado por D&A (ANC bucket unico), verificacao de versao cruzada.
  - BLOCO 3E: `services/contabil/simples_nacional.py` -- motor Simples Nacional reescrito
    com Decimal + money_fiscal (ROUND_HALF_UP), Fator R automatico (LC 123/2006 par. 5-J,
    threshold >= 0.28), sublimite estadual/municipal (ISS/ICMS excluidos > R$3.6M),
    5 anexos × 6 faixas, tabelas versionadas em Decimal, 5 invariantes.
  - BLOCO 3F: `services/contabil/lucro_presumido.py` -- motor Lucro Presumido reescrito
    com 4 bases IRPJ (1.6/8/16/32%), 2 bases CSLL (12/32%), multi-atividade,
    adicional IRPJ trimestral, validacao de bases no construtor, money_fiscal.
    Corrige CRITICO-LP-1 (CSLL 32% para comercio), CRITICO-LP-2 (IRPJ apenas 32%),
    ALTO-LP-3 (float). Ref: `docs/correcao-lucro-presumido-impacto.md`.
  - BLOCO 3G: `services/contabil/lucro_real.py` -- motor Lucro Real com LALUR
    simplificado (adicoes/exclusoes com norma obrigatoria), compensacao de prejuizo
    fiscal 30% (Lei 9.065/95), PIS/COFINS nao-cumulativo com creditos detalhados,
    CSLL com base propria, 11 invariantes.
    Corrige CRITICO-LR-1 (LALUR ausente), CRITICO-LR-2 (compensacao ausente),
    ALTO-LR-3 (float), MEDIO-LR-4/5. Ref: `docs/correcao-lucro-real-impacto.md`.
  - BLOCO 3H: `services/contabil/reforma.py` + `services/contabil/tabelas/reforma_tributaria.py`
    -- motor Reforma Tributaria com cronograma 2026-2033 (EC 132/2023), CBS + IBS + IS,
    6 regimes especificos (saude/educacao/transporte/agropecuaria/combustiveis/geral),
    nao-cumulatividade com creditos, split payment informativo, 6 invariantes.
    Corrige ALTO-RT-1 (cronograma ausente), ALTO-RT-2 (float), MEDIO-RT-3/4.
  - BLOCO 3I: 3 modulos — `retencoes.py` (IRRF 1,5%, CSRF 4,65%, INSS 11%, ISS retido,
    dispensa CSRF <= R$215,05), `difal.py` (EC 87/2015, LC 190/2022, FCP por UF),
    `icms_st.py` (base ST com MVA, ICMS proprio vs ST).
    2 tabelas: `tabelas/servicos_retencao.py`, `tabelas/aliquotas_icms.py` (27 UFs).
    8 invariantes. Funcionalidade nova (NOVO-3I-1).
  - BLOCO 3J: 3 modulos — `comparador.py` (comparativo 4 regimes com PerfilEmpresa,
    regime otimo, economia, alertas), `indicadores.py` (22 indicadores FP&A canonicos:
    liquidez, rentabilidade, atividade/ciclo, estrutura, Fleuriet — funcoes puras Decimal
    com referencia bibliografica), `score_saude.py` (9 componentes, pesos Adendo A.5.3,
    total 0-100, 4 classificacoes). Corrige MEDIO-1 (branch inalcancavel),
    ALTO-SCORE-1 (float), MEDIO-SCORE-2/3 (pesos+cobertura juros), MEDIO-IND-1 (12 ausentes).

## Lucro Real -- Versao 3.0.0

### Estrutura LALUR simplificado

Motor aceita listas de AjusteLALUR (adicoes/exclusoes) com norma obrigatoria.
Categorias tipicas documentadas. LALUR completo com 30+ categorias fica para BLOCO 3K.

### Compensacao de prejuizo fiscal (Lei 9.065/95 art. 15)

- Compensacao limitada a 30% do lucro real antes da compensacao
- Motor recebe prejuizo_fiscal_acumulado como parametro
- Caller gerencia saldo entre periodos
- Prejuizo no periodo: acumula sem compensar

### PIS/COFINS nao-cumulativo

- PIS 1,65% (Lei 10.637/02), COFINS 7,6% (Lei 10.833/03)
- Creditos detalhados por tipo: insumos, energia, aluguel, depreciacao, frete, outros
- Devido = max(0, debito - credito) — creditos nao geram valor negativo

### Correcoes aplicadas

| Bug | Descricao |
|---|---|
| CRITICO-LR-1 | LALUR ausente (lucro real = lucro bruto simplificado) |
| CRITICO-LR-2 | Compensacao de prejuizo ausente (Lei 9.065/95 nao implementada) |
| ALTO-LR-3 | float em toda aritmetica |
| MEDIO-LR-4 | Creditos PIS/COFINS sem detalhamento |
| MEDIO-LR-5 | CSLL sem base propria |

### Limitacoes transitorias

- Apuracao apenas trimestral (anual com estimativas fica para BLOCO 3K)
- LALUR simplificado (categorias limitadas, extensivel)
- Motor nao persiste saldo de prejuizo (caller gerencia)

### Propriedade matematica INV-SN-3 -- Tolerancia proporcional

Quando o DAS e distribuido entre N tributos com money_fiscal()
(ROUND_HALF_UP) aplicado individualmente, a soma dos componentes
pode divergir do total em ate N × 0.005 = N × meio centavo.

Tolerancia adotada: N × 0.01 (margem de seguranca 2x).

Justificativa: cada tributo e uma rubrica fiscal autonoma que vai
para guia/relatorio proprio. Calcular individualmente preserva
fidelidade a expectativa da RFB. A divergencia consolidada e tratada
como diferenca de arredondamento contabil, pratica comum.

Referencia: IN RFB 1.700/2017 Art. 7, par. 2.

## Lucro Presumido -- Versao 3.0.0

### Bases de presuncao implementadas (Lei 9.249/95 art. 15)

| Base IRPJ | Atividade | Base CSLL | Norma |
|---|---|---|---|
| 1.6% | Revenda combustiveis | 12% | art. 15 par. 1 I + art. 20 |
| 8% | Comercio, industria, transp. cargas, hospitais | 12% | art. 15 caput + art. 20 |
| 16% | Transporte de passageiros | 12% | art. 15 par. 1 II + art. 20 |
| 32% | Servicos em geral, intermediacao, locacao | 32% | art. 15 par. 1 III + art. 20 |

### Correcoes aplicadas

| Bug | Descricao | Impacto por cliente comercial (RB 500k/mes) |
|---|---|---|
| CRITICO-LP-1 | CSLL base 32% para todas atividades (correto: 12% para comercio) | +R$ 9.000/mes |
| CRITICO-LP-2 | IRPJ apenas base 32% (faltavam 1.6%, 8%, 16%) | +R$ 18.000/mes |
| ALTO-LP-3 | float em toda aritmetica | arredondamento impreciso |

### Adicional IRPJ

Conforme Lei 9.249/95 art. 3 par. 1: 10% sobre base trimestral > R$ 60.000.
Motor aceita modo trimestral (calculo direto) ou mensal (estimativa base*3 com aviso).

### Validacao de bases no construtor

ReceitaPorAtividade valida:
- IRPJ: apenas 1.6%, 8%, 16%, 32%
- CSLL: apenas 12%, 32%
- Coerencia IRPJ x CSLL (32% IRPJ exige 32% CSLL; 1.6% IRPJ exige 12% CSLL)
- Valor >= 0

## Ajuste de Escopo (2026-04-11, BLOCO 3C diagnostico)

O criterio original "BP fechado" foi recalibrado para "BP gerencial com invariante
verificada em runtime e gap reportado transparentemente". BP derivado de escrituracao
com partida dobrada requer migracao de modelo (BLOCO 3K).

Motivacao: o modelo de dados atual (LancamentoMensal) armazena saldos informados pelo
usuario sem disciplina de partida dobrada. A invariante Ativo == Passivo + PL e violada
em 100% dos dados existentes. O motor de calculo pode validar e reportar, mas nao pode
fabricar dados que nao existem.

Consenso das tres personas contabil-fiscais em 2026-04-11. Nao e falha do mandato — e
adaptacao honesta ao terreno real encontrado.
