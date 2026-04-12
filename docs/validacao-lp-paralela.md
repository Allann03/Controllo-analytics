# Validacao Paralela -- Motor de Lucro Presumido (BLOCO 3F.2)

**Data:** 2026-04-12
**Total de comparacoes:** 36
**Invariantes:** 252/252 OK

---

## Criterios de Aprovacao

| Caso | Tipo | Criterio |
|---|---|---|
| A | Servicos puros (32%/32%) | novo == legado (diff = 0) |
| B | Comercial (8%/12%) | novo < legado, bate na casa do centavo |
| C | Combustiveis (1.6%/12%) | novo << legado, bate na casa do centavo |

---

## Caso A -- Servicos TI (CNAE 6201-5/01)

| Mes | Receita | Total Legado | Total Novo | Base IRPJ Leg. | Base IRPJ Novo | Status | Nota |
|---|---|---|---|---|---|---|---|
| 01 | R$ 50,000 | R$ 8,165.00 | R$ 8,165.00 | R$ 16,000.00 | R$ 16,000.00 | PASS | OK: diff=0.0000 |
| 02 | R$ 200,000 | R$ 37,060.00 | R$ 37,060.00 | R$ 64,000.00 | R$ 64,000.00 | PASS | OK: diff=0.0000 |
| 03 | R$ 500,000 | R$ 95,650.00 | R$ 95,650.00 | R$ 160,000.00 | R$ 160,000.00 | PASS | OK: diff=0.0000 |
| 04 | R$ 50,000 | R$ 8,165.00 | R$ 8,165.00 | R$ 16,000.00 | R$ 16,000.00 | PASS | OK: diff=0.0000 |
| 05 | R$ 200,000 | R$ 37,060.00 | R$ 37,060.00 | R$ 64,000.00 | R$ 64,000.00 | PASS | OK: diff=0.0000 |
| 06 | R$ 500,000 | R$ 95,650.00 | R$ 95,650.00 | R$ 160,000.00 | R$ 160,000.00 | PASS | OK: diff=0.0000 |
| 07 | R$ 50,000 | R$ 8,165.00 | R$ 8,165.00 | R$ 16,000.00 | R$ 16,000.00 | PASS | OK: diff=0.0000 |
| 08 | R$ 200,000 | R$ 37,060.00 | R$ 37,060.00 | R$ 64,000.00 | R$ 64,000.00 | PASS | OK: diff=0.0000 |
| 09 | R$ 500,000 | R$ 95,650.00 | R$ 95,650.00 | R$ 160,000.00 | R$ 160,000.00 | PASS | OK: diff=0.0000 |
| 10 | R$ 50,000 | R$ 8,165.00 | R$ 8,165.00 | R$ 16,000.00 | R$ 16,000.00 | PASS | OK: diff=0.0000 |
| 11 | R$ 200,000 | R$ 37,060.00 | R$ 37,060.00 | R$ 64,000.00 | R$ 64,000.00 | PASS | OK: diff=0.0000 |
| 12 | R$ 500,000 | R$ 95,650.00 | R$ 95,650.00 | R$ 160,000.00 | R$ 160,000.00 | PASS | OK: diff=0.0000 |

## Caso B -- Comercio Varejista (CNAE 4711-3/02)

| Mes | Receita | Total Legado | Total Novo | Base IRPJ Leg. | Base IRPJ Novo | Status | Nota |
|---|---|---|---|---|---|---|---|
| 01 | R$ 50,000 | R$ 8,165.00 | R$ 5,465.00 | R$ 16,000.00 | R$ 4,000.00 | PASS | OK: novo=5465.00 legado=8165.00 economia=2700.00 |
| 02 | R$ 200,000 | R$ 37,060.00 | R$ 21,860.00 | R$ 64,000.00 | R$ 16,000.00 | PASS | OK: novo=21860.00 legado=37060.00 economia=15200.00 |
| 03 | R$ 500,000 | R$ 95,650.00 | R$ 56,650.00 | R$ 160,000.00 | R$ 40,000.00 | PASS | OK: novo=56650.00 legado=95650.00 economia=39000.00 |
| 04 | R$ 50,000 | R$ 8,165.00 | R$ 5,465.00 | R$ 16,000.00 | R$ 4,000.00 | PASS | OK: novo=5465.00 legado=8165.00 economia=2700.00 |
| 05 | R$ 200,000 | R$ 37,060.00 | R$ 21,860.00 | R$ 64,000.00 | R$ 16,000.00 | PASS | OK: novo=21860.00 legado=37060.00 economia=15200.00 |
| 06 | R$ 500,000 | R$ 95,650.00 | R$ 56,650.00 | R$ 160,000.00 | R$ 40,000.00 | PASS | OK: novo=56650.00 legado=95650.00 economia=39000.00 |
| 07 | R$ 50,000 | R$ 8,165.00 | R$ 5,465.00 | R$ 16,000.00 | R$ 4,000.00 | PASS | OK: novo=5465.00 legado=8165.00 economia=2700.00 |
| 08 | R$ 200,000 | R$ 37,060.00 | R$ 21,860.00 | R$ 64,000.00 | R$ 16,000.00 | PASS | OK: novo=21860.00 legado=37060.00 economia=15200.00 |
| 09 | R$ 500,000 | R$ 95,650.00 | R$ 56,650.00 | R$ 160,000.00 | R$ 40,000.00 | PASS | OK: novo=56650.00 legado=95650.00 economia=39000.00 |
| 10 | R$ 50,000 | R$ 8,165.00 | R$ 5,465.00 | R$ 16,000.00 | R$ 4,000.00 | PASS | OK: novo=5465.00 legado=8165.00 economia=2700.00 |
| 11 | R$ 200,000 | R$ 37,060.00 | R$ 21,860.00 | R$ 64,000.00 | R$ 16,000.00 | PASS | OK: novo=21860.00 legado=37060.00 economia=15200.00 |
| 12 | R$ 500,000 | R$ 95,650.00 | R$ 56,650.00 | R$ 160,000.00 | R$ 40,000.00 | PASS | OK: novo=56650.00 legado=95650.00 economia=39000.00 |

## Caso C -- Posto Combustiveis (CNAE 4731-8/00)

| Mes | Receita | Total Legado | Total Novo | Base IRPJ Leg. | Base IRPJ Novo | Status | Nota |
|---|---|---|---|---|---|---|---|
| 01 | R$ 50,000 | R$ 8,165.00 | R$ 4,985.00 | R$ 16,000.00 | R$ 800.00 | PASS | OK: novo=4985.00 legado=8165.00 economia=3180.00 |
| 02 | R$ 200,000 | R$ 37,060.00 | R$ 19,940.00 | R$ 64,000.00 | R$ 3,200.00 | PASS | OK: novo=19940.00 legado=37060.00 economia=17120.00 |
| 03 | R$ 500,000 | R$ 95,650.00 | R$ 49,850.00 | R$ 160,000.00 | R$ 8,000.00 | PASS | OK: novo=49850.00 legado=95650.00 economia=45800.00 |
| 04 | R$ 50,000 | R$ 8,165.00 | R$ 4,985.00 | R$ 16,000.00 | R$ 800.00 | PASS | OK: novo=4985.00 legado=8165.00 economia=3180.00 |
| 05 | R$ 200,000 | R$ 37,060.00 | R$ 19,940.00 | R$ 64,000.00 | R$ 3,200.00 | PASS | OK: novo=19940.00 legado=37060.00 economia=17120.00 |
| 06 | R$ 500,000 | R$ 95,650.00 | R$ 49,850.00 | R$ 160,000.00 | R$ 8,000.00 | PASS | OK: novo=49850.00 legado=95650.00 economia=45800.00 |
| 07 | R$ 50,000 | R$ 8,165.00 | R$ 4,985.00 | R$ 16,000.00 | R$ 800.00 | PASS | OK: novo=4985.00 legado=8165.00 economia=3180.00 |
| 08 | R$ 200,000 | R$ 37,060.00 | R$ 19,940.00 | R$ 64,000.00 | R$ 3,200.00 | PASS | OK: novo=19940.00 legado=37060.00 economia=17120.00 |
| 09 | R$ 500,000 | R$ 95,650.00 | R$ 49,850.00 | R$ 160,000.00 | R$ 8,000.00 | PASS | OK: novo=49850.00 legado=95650.00 economia=45800.00 |
| 10 | R$ 50,000 | R$ 8,165.00 | R$ 4,985.00 | R$ 16,000.00 | R$ 800.00 | PASS | OK: novo=4985.00 legado=8165.00 economia=3180.00 |
| 11 | R$ 200,000 | R$ 37,060.00 | R$ 19,940.00 | R$ 64,000.00 | R$ 3,200.00 | PASS | OK: novo=19940.00 legado=37060.00 economia=17120.00 |
| 12 | R$ 500,000 | R$ 95,650.00 | R$ 49,850.00 | R$ 160,000.00 | R$ 8,000.00 | PASS | OK: novo=49850.00 legado=95650.00 economia=45800.00 |

## Invariantes

Total: 252/252 invariantes OK

| Invariante | Descricao |
|---|---|
| INV-LP-1 | base_calculo_irpj == sum(receita_i x base_presuncao_irpj_i) |
| INV-LP-2 | irpj_15 == base_irpj x 0.15 |
| INV-LP-3 | base_trim <= 60k -> adicional == 0 |
| INV-LP-4 | csll_9 == base_csll x 0.09 |
| INV-LP-5 | pis_065 == receita x 0.0065 |
| INV-LP-6 | cofins_3 == receita x 0.03 |
| INV-LP-7 | total == irpj + csll + pis + cofins + iss |

---

## Veredito: **APROVADO**

- 36 comparacoes executadas
- 252/252 invariantes validadas
- 0 falhas encontradas

### Assinaturas

| Persona | Papel | Aprovacao |
|---|---|---|
| Engenheiro Fiscal | Correcao das bases de presuncao | SIM |
| Arquiteto | Integracao via feature flag + adapter | SIM |
| QA | 36 comparacoes + invariantes | SIM |
| Mandato | Revisao final e autorizacao de cutover | PENDENTE |

---

*Gerado automaticamente pelo script de validacao paralela (BLOCO 3F.2).*
