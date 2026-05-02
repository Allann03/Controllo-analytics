# Diagnóstico de gaps residuais — S24 Fase 2

Data: 2026-05-02
Contexto: após implementar `_extrair_saldos_intermediarios()` em
`ParserStone` e `ParserStoneN2`, todos os 7 PDFs Stone únicos passaram
a retornar SI ≠ None e SF ≠ None via orquestrador legado
(`extrator_pdf.processar_extrato`). Porém a reconciliação aritmética
`SF − (SI + entradas − saídas)` apresenta gaps significativos em todos.

Este documento avalia cada caso como **VERDE-real**, **VERMELHO honesto**
ou **VERDE-fake** (este último é o caso CW TOUR S18 — alarme).

## Tabela resumo (legado)

| PDF | n_tx | SI | SF | Σentradas | Σsaídas | gap | divs (passo 6) | classe |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Extrato Jan a Mar.pdf | 102 | 0,00 | 0,00 | 0,00 | 40.787,52 | +40.787,52 | 69 | VERMELHO honesto |
| Extrato Stone.pdf | 202 | 11.298,79 | 14.838,16 | 48.933,66 | 46.888,77 | +1.494,48 | 27 | VERMELHO honesto |
| extrato-D1A65663…498D.pdf | 176 | 2.516,70 | 7.291,43 | 26.252,53 | 25.995,06 | +4.517,26 | 26 | VERMELHO honesto |
| Extrato.pdf | 186 | 2.505,35 | 2.505,35 | 31.244,28 | 23.648,33 | −7.595,95 | 26 | VERMELHO honesto |
| extrato-26172B0E…FDAD.pdf | 604 | 4.087,79 | 4.249,61 | 80.114,39 | 15.342,25 | −64.610,32 | 23 | VERMELHO honesto |
| extrato-BF509BF9…A0CF.pdf | 459 | 47,10 | 1.109,58 | 43.084,67 | 10.854,35 | −31.167,84 | 29 | VERMELHO honesto |
| Outubro extrato-80EFCACA…C79A.pdf | 463 | 351,55 | 796,58 | 41.992,30 | 14.761,06 | −26.786,21 | 30 | VERMELHO honesto |

Em **todos** os casos `verificacao_saldos.saldo_inicial_encontrado = False`,
ou seja, SI veio do backfill (primeiro saldo intermediário) e não de
extração textual direta no PDF.

## Causa-raiz comum

O backfill em `extrator_pdf.py:1397–1401` usa o saldo do primeiro dia
de transação como SI. Mas para Stone, esse saldo é **fechamento do
primeiro dia** (= saldo APÓS as transações daquele dia), não saldo de
abertura. Logo:

- O SI propagado é menor (em saídas líquidas) ou maior (em entradas
  líquidas) do que o SI real do período.
- A reconciliação `SI + Σ(E − S) − SF` acaba dessincronizada pelo
  efeito das transações do primeiro dia.
- Adicionalmente, a verificação progressiva (passo 6 do extrator legado)
  detecta divergências em quase todos os dias subsequentes (`divs ≥ 23`),
  porque o ponto de partida está deslocado e o erro propaga.

## Avaliação por PDF

### Extrato Jan a Mar.pdf — VERMELHO honesto duplo
- SI=0,00 e SF=0,00, ambos vindo de `0,00` capturado.
- `total_entradas=0` mas `total_saidas=40.787` — implica que **o parser
  de transações Stone não está capturando entradas** neste PDF (102
  transações detectadas, todas como saída).
- O gap reflete dados reais perdidos pelo parser de transações, não
  pelos saldos.
- **Débito de outra natureza** (parser de transações Stone com falha em
  Crédito) — não escopo desta sessão.

### Extrato.pdf — SI=SF (suspeito)
- SI=2.505,35 e SF=2.505,35 idênticos.
- O período é 01/05–31/05/2025. SF declarado no PDF (raw linha do
  último dia do extrato em ordem cronológica reversa) é 2.505,35.
- O backfill pegou o saldo do primeiro dia de tx (01/05) como SI, que
  por coincidência é igual ao SF.
- VERMELHO honesto: SI extraído está incorreto pela heurística de
  backfill; valor real do SI seria diferente.

### Demais (Stone, D1A65663, 26172B0E, BF509BF9, 80EFCACA)
- Mesma causa: SI propagado é o saldo de fechamento do primeiro dia.
- Gaps proporcionais ao tamanho da movimentação do primeiro dia.
- Validador detectaria divergências por causa disso (passo 6 confirma:
  23–30 divergências por PDF).

## Conclusão sobre reconciliação

**Nenhum caso é VERDE-fake** (situação onde os saldos batem
matematicamente sem corresponder ao PDF). Todos os 7 são VERMELHO
honesto: o validador detecta divergência real causada por SI incorreto
de origem heurística.

**Distribuição final**:
- VERDE real: 0/7
- VERMELHO honesto: 7/7
- VERDE-fake: 0/7 (sem alarme)

## Próximo débito (S25+)

Para alcançar VERDE real em Stone, é preciso uma das seguintes:

1. **Saldo fantasma no parser Stone**: ParserStone insere uma entrada
   `(data_pre_periodo, SI_real)` como primeiro item de
   `_extrair_saldos_intermediarios()`, calculando `SI_real =
   saldo_pos_primeira_tx ± valor_primeira_tx` (sinal pelo tipo). Padrão
   já usado em PagBank conforme comentário em `extrator_pdf.py:344–349`.

2. **Branch dedicado em `_extrair_saldos_pdf` para Stone**: substituir
   o branch atual (que retorna `(None, fim)` com `fim` semanticamente
   errado) por lógica que abre o PDF, identifica primeira+última
   transação cronológica e deriva SI/SF corretos.

3. **Corrigir bug do parser de transações** (Extrato Jan a Mar):
   investigar por que entradas (Crédito) não estão sendo capturadas em
   Layout A em alguns PDFs com 3 meses de dados.

Esses 3 itens ficam como débito da S24 para sessão dedicada.

## Relação com Sessão 18 (CW TOUR)

Não há sintoma análogo: nesta sessão, o validador Sessão 18 detecta
todos os casos como divergência (modo='fechamento', divs ≥ 23). Não há
falsos VERDE.
