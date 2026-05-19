# Correcao Lucro Real -- Analise de Impacto

**Data:** 2026-04-11
**Versao:** 1.0 (rascunho)
**Motor:** services/contabil/lucro_real.py (BLOCO 3G)

---

## Resumo

O motor legado de Lucro Real tinha 5 bugs simultaneos. Diferente do Lucro Presumido
(superpagamento unidirecional), o Lucro Real tem impacto **bidirecional** — bugs podem
causar tanto sub quanto superpagamento dependendo do perfil da empresa.

## Bugs corrigidos

### CRITICO-LR-1 — LALUR ausente

O motor legado calculava "lucro real" como `max(0, receita_bruta - custo_servicos)`.
Isto e lucro bruto simplificado, nao lucro real. O LALUR (Livro de Apuracao do Lucro
Real) exige adicoes (despesas indedutiveis) e exclusoes (receitas nao tributaveis).

**Impacto bidirecional:**
- Empresa com muitas despesas indedutiveis: IRPJ SUBESTIMADO (adicoes faltantes)
- Empresa com receitas nao tributaveis relevantes: IRPJ SUPERESTIMADO (exclusoes faltantes)
- Direcao depende do perfil — nao e possivel estimar magnitude generica

### CRITICO-LR-2 — Compensacao de prejuizo ausente

Lei 9.065/95 art. 15 permite compensar prejuizos de exercicios anteriores ate 30%
do lucro real. O motor legado simplesmente zerava prejuizos via `max(0, ...)`.

**Impacto:** empresa com historico de prejuizo paga IRPJ/CSLL sobre a totalidade
do lucro quando deveria compensar ate 30%. Exemplo: prejuizo acumulado 1M, lucro
trimestral 200k → motor legado tributa 200k; motor novo tributa 140k (compensa 60k).
Diferenca IRPJ: (200k-140k)*15% = 9k/trimestre = 36k/ano.

### ALTO-LR-3 — Float em aritmetica

Toda aritmetica em float. Arredondamento impreciso em calculos fiscais que vao
para DARF. Corrigido via Decimal + money_fiscal (ROUND_HALF_UP).

### MEDIO-LR-4 — Creditos PIS/COFINS simplificados

Motor legado: credito = custo_servicos * aliquota (unica base).
Motor novo: creditos detalhados por tipo (insumos, energia, aluguel, depreciacao,
frete, outros). Permite calculo mais preciso do PIS/COFINS devido.

### MEDIO-LR-5 — CSLL sem base propria

Motor legado: CSLL usa mesma base do IRPJ. Lei 9.249/95 art. 57 permite ajustes
diferentes na base da CSLL. Motor novo aceita base_csll como parametro separado.

## Empresas afetadas

Todas que utilizam regime de Lucro Real. Em geral:
- Empresas de maior porte (receita > R$ 4.8M/ano excluidas do Simples)
- Empresas com margem de lucro baixa ou variavel
- Empresas com historico de prejuizo fiscal
- Empresas com receitas de equivalencia patrimonial ou dividendos relevantes

## Recomendacao

Diferente do Lucro Presumido (onde o impacto e unidirecional e mensuravel),
o Lucro Real exige analise caso a caso para determinar se houve sub ou
superpagamento. Recomendamos que o contador CRC de cada cliente revise:

1. Se a empresa tinha despesas indedutiveis nao adicionadas ao LALUR
2. Se havia exclusoes legitimas nao aplicadas
3. Se existe saldo de prejuizo fiscal nao compensado
4. Se os creditos PIS/COFINS foram aproveitados integralmente

## Status

Motor corrigido em `services/contabil/lucro_real.py` (BLOCO 3G).
Aguarda integracao ao endpoint e cutover.

---

*Rascunho para revisao pelo mandato.*
