# Correcao Lucro Presumido -- Analise de Impacto Financeiro

**Data:** 2026-04-11 (rascunho) | 2026-04-12 (integracao BLOCO 3F.2)
**Versao:** 2.0 (em validacao)
**Motor:** services/contabil/lucro_presumido.py (BLOCO 3F)
**Integracao:** services/simulacao_tributaria_service.py (BLOCO 3F.2)

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
- **IN RFB 1.234/2012 art. 30:** servicos hospitalares (base 8%)

## Recomendacao

Comunicar proativamente a todos os clientes no Lucro Presumido com atividades
de comercio, industria ou transporte que os valores de IRPJ e CSLL estavam
superestimados. Orientar revisao com o contador CRC para verificar se decisoes
fiscais foram tomadas com base nos valores incorretos.

## O que muda para o cliente

A partir da ativacao do motor corrigido, os valores de **IRPJ e CSLL** exibidos
na plataforma passam a utilizar as bases de presuncao corretas conforme a
atividade economica (CNAE) de cada empresa:

- **Empresas de comercio:** IRPJ calculado sobre 8% da receita (antes: 32%).
  CSLL calculada sobre 12% (antes: 32%). Reducao significativa nos valores apresentados.
- **Postos de combustiveis:** IRPJ calculado sobre 1.6% da receita (antes: 32%).
  Reducao muito expressiva.
- **Transportadoras de passageiros:** IRPJ sobre 16% (antes: 32%).
- **Empresas de servicos:** Sem alteracao. O calculo ja estava correto.

**PIS, COFINS e ISS nao sao afetados** — esses tributos incidem sobre a receita
bruta diretamente, independente da base de presuncao.

**Importante:** Os valores anteriores **superestimavam** a carga tributaria.
O motor corrigido apresenta os valores **reais** conforme a legislacao.
Nenhum tributo foi reduzido — apenas a exibicao estava incorreta.

## Cronograma de cutover

| Fase | Status | Data |
|---|---|---|
| Motor corrigido (BLOCO 3F) | Completo | 2026-04-11 |
| Integracao via feature flag (BLOCO 3F.2) | Completo | 2026-04-12 |
| Validacao paralela (36 comparacoes) | **APROVADO** | 2026-04-12 |
| Flag em producao: `CONTROLLO_LP_ENGINE=legado` | Ativo | 2026-04-12 |
| Revisao pelo mandato | PENDENTE | - |
| Cutover: `CONTROLLO_LP_ENGINE=novo` | PENDENTE | Apos aprovacao |
| Comunicacao a clientes afetados | PENDENTE | Apos cutover |
| Remocao da flag (fase 3) | PENDENTE | Apos estabilizacao |

## Rollback plan (< 2 minutos)

1. Alterar `CONTROLLO_LP_ENGINE=legado` no `.env` de producao (10s)
2. Restart do servico backend (30-60s)
3. Verificar em `/comparar-regimes` que valores voltaram ao padrao (15s)

## Status

Motor corrigido em `services/contabil/lucro_presumido.py` (BLOCO 3F).
Integracao ao endpoint concluida via feature flag (BLOCO 3F.2).
Validacao paralela aprovada: 36/36 comparacoes, 252/252 invariantes.
Aguarda autorizacao do mandato para cutover em producao.

---

*Documento de impacto para revisao pelo mandato.*
