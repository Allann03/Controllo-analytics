# Correcao Lucro Presumido -- Analise de Impacto Financeiro

**Data:** 2026-04-11
**Versao:** 1.0 (rascunho para revisao)
**Motor:** services/contabil/lucro_presumido.py (BLOCO 3F)

---

## Resumo

O motor legado de Lucro Presumido aplicava base de presuncao de 32% (servicos)
para TODAS as atividades, incluindo comercio (deveria ser 8%) e industria.
Adicionalmente, a CSLL usava base 32% para todas as atividades, quando deveria
ser 12% para comercio/industria (Lei 9.249/95 art. 20).

## Magnitude do impacto

### IRPJ — base de presuncao errada (CRITICO-LP-2)

| Atividade | Base legada | Base correta | Fator de superestimativa |
|---|---|---|---|
| Revenda combustiveis | 32% | 1.6% | 20x |
| Comercio em geral | 32% | 8% | 4x |
| Transporte passageiros | 32% | 16% | 2x |
| Servicos em geral | 32% | 32% | 1x (correto) |

### CSLL — base de presuncao errada (CRITICO-LP-1)

| Atividade | Base legada | Base correta | Fator |
|---|---|---|---|
| Comercio/industria | 32% | 12% | 2.67x |
| Servicos em geral | 32% | 32% | 1x (correto) |

### Impacto monetario estimado (receita bruta mensal = R$ 500.000)

| Cenario | Tributo legado/mes | Tributo correto/mes | Diferenca/mes | Diferenca/ano |
|---|---|---|---|---|
| Comercio (IRPJ+CSLL) | ~R$ 52.400 | ~R$ 11.400 | ~R$ 27.000 | ~R$ 324.000 |
| Combustiveis (IRPJ+CSLL) | ~R$ 52.400 | ~R$ 6.600 | ~R$ 30.000+ | ~R$ 360.000+ |
| Transp. passageiros | ~R$ 52.400 | ~R$ 19.400 | ~R$ 22.000 | ~R$ 264.000 |
| Servicos (correto) | ~R$ 38.400 | ~R$ 38.400 | R$ 0 | R$ 0 |

*Nota: valores de IRPJ+CSLL apenas. PIS, COFINS e ISS nao sao afetados (incidem sobre receita bruta, nao sobre base presumida).*

### Empresas NAO afetadas

- Empresas no Simples Nacional (regime proprio)
- Empresas no Lucro Real (apuracao diferente)
- Empresas de servicos no Lucro Presumido com base 32% (calculo ja estava correto)

### Empresas afetadas

- Comercio em geral no Lucro Presumido
- Industrias no Lucro Presumido
- Hospitais e servicos medicos no Lucro Presumido (base 8%)
- Transportadoras no Lucro Presumido
- Postos de combustiveis no Lucro Presumido (base 1.6%)

## Fundamentacao normativa

- **Lei 9.249/95 art. 15:** bases de presuncao IRPJ por atividade
- **Lei 9.249/95 art. 15 par. 1:** bases especificas (1.6%, 16%)
- **Lei 9.249/95 art. 20:** base CSLL (12% comercio, 32% servicos)
- **RIR/2018 art. 591:** tabela consolidada de presuncoes

## Recomendacao

Comunicar proativamente a todos os clientes no Lucro Presumido com atividades
de comercio, industria ou transporte que os valores de IRPJ e CSLL estavam
superestimados. Orientar revisao com o contador CRC para verificar se decisoes
fiscais foram tomadas com base nos valores incorretos.

## Status

Motor corrigido em `services/contabil/lucro_presumido.py` (BLOCO 3F).
Aguarda integracao ao endpoint e cutover.

---

*Rascunho para revisao pelo mandato.*
