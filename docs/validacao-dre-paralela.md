# Validacao Paralela DRE -- BLOCO 3B.2 Fase B (recalibrada)

Gerado em: 2026-04-11T15:09:46.559129+00:00

## Incidente ALTO-1b

Durante a primeira execucao da Fase B, descobriu-se que a engine legada
nunca subtraia `depreciacao_amortizacao` da DRE (CRITICO-NEW-2).
Criterios recalibrados pelo mandato para refletir dois bugs simultaneos:
ALTO-1 (DFin no EBIT) e ALTO-1b (D&A omitida).
Ref: `docs/debitos-descobertos.md` entry CRITICO-NEW-2.

## 1. Metodologia

### Criterios de categorizacao (recalibrados)
| Categoria | Regra |
|---|---|
| IGUAL | Diferenca <= 0.02 |
| CORRECAO COMBINADA (EBITDA) | EBITDA: diff == +DFin - D&A (D&A nao cancela no legado) |
| CORRECAO ALTO-1b (D&A) | LAIR/LL: diff == -depreciacao_amortizacao |
| CORRECAO COMBINADA | EBIT: diff == +DFin - D&A |
| DIVERGENCIA INVESTIGAR | Qualquer outra coisa |

### Invariantes matematicas (6 novas)
| ID | Formula |
|---|---|
| INV-P1' | RB ate LB: IGUAL em 5 linhas |
| INV-P2' | EBIT_novo - EBIT_leg == DFin - D&A |
| INV-P3' | EBITDA_novo - EBITDA_leg == DFin - D&A |
| INV-P4' | LAIR_novo - LAIR_leg == -D&A |
| INV-P5' | LL_novo - LL_leg == -D&A |
| INV-P6' | Se D&A=0: LAIR e LL iguais |

## 2. Datasets sinteticos

### Empresa Alpha S/A (id=1)
- **Perfil:** Servicos PME — RB crescente, D&A=1500, DFin=2000

### Empresa Comercio Teste (id=3)
- **Perfil:** Comercio — CMV~60%, sazonalidade, D&A=500, DFin=5000

### Empresa Industria Teste (id=4)
- **Perfil:** Industria — crescimento linear, D&A=20000, DFin=12000

## 3. Resultados por empresa

### Empresa Alpha S/A

| Mes | Linha | Legado | Novo | Diferenca | Categoria |
|---|---|---|---|---|---|
| 2025-01 | ebit | 47000.00 | 47500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-01 | ebitda | 48500.00 | 49000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-01 | lair | 47000.00 | 45500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-01 | lucro_liquido | 44000.00 | 42500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | ebit | 52000.00 | 52500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-02 | ebitda | 53500.00 | 54000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-02 | lair | 52000.00 | 50500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | lucro_liquido | 49000.00 | 47500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | ebit | 57000.00 | 57500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-03 | ebitda | 58500.00 | 59000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-03 | lair | 57000.00 | 55500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | lucro_liquido | 54000.00 | 52500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | ebit | 62000.00 | 62500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-04 | ebitda | 63500.00 | 64000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-04 | lair | 62000.00 | 60500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | lucro_liquido | 59000.00 | 57500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | ebit | 67000.00 | 67500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-05 | ebitda | 68500.00 | 69000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-05 | lair | 67000.00 | 65500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | lucro_liquido | 64000.00 | 62500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | ebit | 72000.00 | 72500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-06 | ebitda | 73500.00 | 74000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-06 | lair | 72000.00 | 70500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | lucro_liquido | 69000.00 | 67500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | ebit | 77000.00 | 77500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-07 | ebitda | 78500.00 | 79000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-07 | lair | 77000.00 | 75500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | lucro_liquido | 74000.00 | 72500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | ebit | 82000.00 | 82500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-08 | ebitda | 83500.00 | 84000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-08 | lair | 82000.00 | 80500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | lucro_liquido | 79000.00 | 77500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | ebit | 87000.00 | 87500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-09 | ebitda | 88500.00 | 89000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-09 | lair | 87000.00 | 85500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | lucro_liquido | 84000.00 | 82500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | ebit | 92000.00 | 92500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-10 | ebitda | 93500.00 | 94000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-10 | lair | 92000.00 | 90500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | lucro_liquido | 89000.00 | 87500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | ebit | 97000.00 | 97500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-11 | ebitda | 98500.00 | 99000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-11 | lair | 97000.00 | 95500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | lucro_liquido | 94000.00 | 92500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | ebit | 102000.00 | 102500.00 | +500.00 | CORRECAO COMBINADA |
| 2025-12 | ebitda | 103500.00 | 104000.00 | +500.00 | CORRECAO COMBINADA |
| 2025-12 | lair | 102000.00 | 100500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | lucro_liquido | 99000.00 | 97500.00 | -1500.00 | CORRECAO ALTO-1b (D&A) |

Linhas identicas: 120/168

### Empresa Comercio Teste

| Mes | Linha | Legado | Novo | Diferenca | Categoria |
|---|---|---|---|---|---|
| 2025-01 | ebit | 43000.00 | 47500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-01 | ebitda | 43500.00 | 48000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-01 | lair | 43000.00 | 42500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-01 | lucro_liquido | 32200.00 | 31700.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | ebit | 43000.00 | 47500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-02 | ebitda | 43500.00 | 48000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-02 | lair | 43000.00 | 42500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | lucro_liquido | 32200.00 | 31700.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-03 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-03 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-04 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-04 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-05 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-05 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-06 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-06 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-07 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-07 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-08 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-08 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-09 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-09 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | ebit | 52000.00 | 56500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-10 | ebitda | 52500.00 | 57000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-10 | lair | 52000.00 | 51500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | lucro_liquido | 40000.00 | 39500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | ebit | 79000.00 | 83500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-11 | ebitda | 79500.00 | 84000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-11 | lair | 79000.00 | 78500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | lucro_liquido | 63400.00 | 62900.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | ebit | 79000.00 | 83500.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-12 | ebitda | 79500.00 | 84000.00 | +4500.00 | CORRECAO COMBINADA |
| 2025-12 | lair | 79000.00 | 78500.00 | -500.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | lucro_liquido | 63400.00 | 62900.00 | -500.00 | CORRECAO ALTO-1b (D&A) |

Linhas identicas: 120/168

### Empresa Industria Teste

| Mes | Linha | Legado | Novo | Diferenca | Categoria |
|---|---|---|---|---|---|
| 2025-01 | ebit | 224700.00 | 216700.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-01 | ebitda | 244700.00 | 236700.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-01 | lair | 224700.00 | 204700.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-01 | lucro_liquido | 183950.00 | 163950.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | ebit | 230400.00 | 222400.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-02 | ebitda | 250400.00 | 242400.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-02 | lair | 230400.00 | 210400.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-02 | lucro_liquido | 188900.00 | 168900.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | ebit | 236100.00 | 228100.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-03 | ebitda | 256100.00 | 248100.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-03 | lair | 236100.00 | 216100.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-03 | lucro_liquido | 193850.00 | 173850.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | ebit | 241800.00 | 233800.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-04 | ebitda | 261800.00 | 253800.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-04 | lair | 241800.00 | 221800.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-04 | lucro_liquido | 198800.00 | 178800.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | ebit | 247500.00 | 239500.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-05 | ebitda | 267500.00 | 259500.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-05 | lair | 247500.00 | 227500.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-05 | lucro_liquido | 203750.00 | 183750.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | ebit | 253200.00 | 245200.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-06 | ebitda | 273200.00 | 265200.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-06 | lair | 253200.00 | 233200.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-06 | lucro_liquido | 208700.00 | 188700.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | ebit | 258900.00 | 250900.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-07 | ebitda | 278900.00 | 270900.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-07 | lair | 258900.00 | 238900.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-07 | lucro_liquido | 213650.00 | 193650.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | ebit | 264600.00 | 256600.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-08 | ebitda | 284600.00 | 276600.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-08 | lair | 264600.00 | 244600.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-08 | lucro_liquido | 218600.00 | 198600.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | ebit | 270300.00 | 262300.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-09 | ebitda | 290300.00 | 282300.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-09 | lair | 270300.00 | 250300.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-09 | lucro_liquido | 223550.00 | 203550.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | ebit | 276000.00 | 268000.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-10 | ebitda | 296000.00 | 288000.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-10 | lair | 276000.00 | 256000.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-10 | lucro_liquido | 228500.00 | 208500.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | ebit | 281700.00 | 273700.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-11 | ebitda | 301700.00 | 293700.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-11 | lair | 281700.00 | 261700.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-11 | lucro_liquido | 233450.00 | 213450.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | ebit | 287400.00 | 279400.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-12 | ebitda | 307400.00 | 299400.00 | -8000.00 | CORRECAO COMBINADA |
| 2025-12 | lair | 287400.00 | 267400.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |
| 2025-12 | lucro_liquido | 238400.00 | 218400.00 | -20000.00 | CORRECAO ALTO-1b (D&A) |

Linhas identicas: 120/168

## 4. Verificacao das 6 invariantes

| Empresa | Mes | P1' | P2' | P3' | P4' | P5' | P6' |
|---|---|---|---|---|---|---|---|
| Empresa Alpha S | 2025-01 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-02 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-03 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-04 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-05 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-06 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-07 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-08 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-09 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-10 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-11 | OK | OK | OK | OK | OK | OK |
| Empresa Alpha S | 2025-12 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-01 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-02 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-03 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-04 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-05 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-06 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-07 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-08 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-09 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-10 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-11 | OK | OK | OK | OK | OK | OK |
| Empresa Comerci | 2025-12 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-01 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-02 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-03 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-04 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-05 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-06 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-07 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-08 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-09 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-10 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-11 | OK | OK | OK | OK | OK | OK |
| Empresa Industr | 2025-12 | OK | OK | OK | OK | OK | OK |

**Total: 216/216 invariantes atendidas.**

## 5. Incidentes encontrados

Nenhum incidente encontrado.

## 6. Veredito final

- [OK] 100% das linhas Receita Bruta ate Lucro Bruto: IGUAL
- [OK] 100% das linhas EBIT: CORRECAO COMBINADA (ou IGUAL)
- [OK] 100% das linhas EBITDA: CORRECAO COMBINADA (ou IGUAL)
- [OK] 100% das linhas LAIR: CORRECAO ALTO-1b (ou IGUAL)
- [OK] 100% das linhas Resultado Liquido: CORRECAO ALTO-1b (ou IGUAL)
- [OK] 216/216 invariantes atendidas
- [OK] Zero DIVERGENCIA INVESTIGAR

**VEREDITO: APROVADO**

### Distribuicao de categorias
- CORRECAO ALTO-1b (D&A): 72
- CORRECAO COMBINADA: 72
- IGUAL: 360