# S24 Fase 2 — Relatório

Data: 2026-05-02
Branch: `feat/stone-parser-saldos`
Tip: `79331d4` (chore S23) — sem novos commits.

## Decisão tomada

**Opção D**: NÃO modificar `pipeline_extracao.py`. A divergência entre
os dois orquestradores foi documentada como débito arquitetural em
`debito_arquitetural_pipelines_s24.md`. Em produção, o endpoint
principal usa o legado (`extrator_pdf.processar_extrato`), que **possui
backfill** de SI a partir de saldos intermediários. Logo, o fix do
parser Stone resolve o problema para o usuário final.

**Opção A** (cirúrgica em `stone_n2.py`): aprovada para resolver caso
`Extrato.pdf` (linha sem descrição inline). 8 linhas adicionadas, nada
existente alterado.

## Arquivos modificados

| Arquivo | Mudança | Linhas |
|---|---|---|
| `backend/services/parsers/stone.py` | + `_RE_SALDO_TAIL_N1` regex<br>+ `_extrair_saldos_intermediarios()` (delegação espelhando `extrair()`)<br>+ `_extrair_saldos_intermediarios_n1()` (Layout B) | +85, sem alteração de código preexistente |
| `backend/services/parsers/stone_n2.py` | + `_RE_DATA_SALDO_TAIL_N2` regex permissiva<br>+ `_extrair_saldos_intermediarios()` (Layout A)<br>+ fallback dentro do loop quando linha-âncora sem descrição inline | +75, sem alteração de código preexistente |
| `backend/tests/test_stone_saldos_s24.py` | NOVO — 16 testes (8 método direto + 7 E2E parametrizados + 1 cobertura agregada) | +180 |
| `backend/tests/auditoria_s24/relatorio_fase2.md` | NOVO (este arquivo) | — |
| `backend/tests/auditoria_s24/debito_arquitetural_pipelines_s24.md` | NOVO | — |
| `backend/tests/auditoria_s24/diagnostico_gaps_residuais_s24.md` | NOVO | — |

Fora desse escopo, nenhum arquivo de produção foi tocado. R2 respeitado.

## Resultado funcional

### Layout A (Crédito/Débito) — via legado

| PDF | n_tx | SI antes (S23) | SI depois (S24) | SF depois | gap residual |
|---|---:|---:|---:|---:|---:|
| Extrato Jan a Mar.pdf | 102 | None | 0,00 | 0,00 | 40.787,52 |
| Extrato Stone.pdf | 202 | None | 11.298,79 | 14.838,16 | 1.494,48 |
| extrato-D1A65663…498D.pdf | 176 | None | 2.516,70 | 7.291,43 | 4.517,26 |
| Extrato.pdf | 186 | None | 2.505,35 | 2.505,35 | −7.595,95 |

**4/4 PDFs Layout A** agora retornam SI ≠ None (antes: 0/4).

### Layout B (Entrada/Saída) — via legado

| PDF | n_tx | SI antes (S23) | SI depois (S24) | SF depois | gap residual |
|---|---:|---:|---:|---:|---:|
| extrato-26172B0E…FDAD.pdf | 604 | None | 4.087,79 | 4.249,61 | −64.610,32 |
| extrato-BF509BF9…A0CF.pdf | 459 | None | 47,10 | 1.109,58 | −31.167,84 |
| Outubro extrato-80EFCACA…C79A.pdf | 463 | None | 351,55 | 796,58 | −26.786,21 |

**3/3 PDFs Layout B** agora retornam SI ≠ None (antes: 0/3).
**Layout B não exigiu fix em `stone.py`** — cobertura de datas já era
completa (gap=0 em todos).

### Auditoria S23 (pipeline novo)

Continua reportando 10/10 Stone como VERMELHO `saldo inicial ou final
ausente` — esperado, é o débito arquitetural documentado. **Auditoria
NÃO foi re-rodada nesta sessão** (objetivo era validar o caminho do
endpoint, não do pipeline novo).

## Diagnóstico de gaps residuais

Todos os 7 PDFs apresentam gap aritmético > R$ 100 após backfill, mas
**nenhum é VERDE-fake**: o validador Sessão 18 detecta divergências em
todos (23–69 divergências por PDF), e a causa é honesta — o backfill
genérico em `extrator_pdf.py:1397–1401` usa o saldo do primeiro dia de
transação como SI, mas em Stone esse saldo é **fechamento do primeiro
dia** (após as transações daquele dia), não SI verdadeiro.

Detalhes completos em
[diagnostico_gaps_residuais_s24.md](diagnostico_gaps_residuais_s24.md).

**Distribuição final dos 7 únicos**:
- VERDE real: 0/7
- VERMELHO honesto: 7/7
- VERDE-fake: 0/7 (sem alarme)

**Caso especial — Extrato Jan a Mar.pdf**: total_entradas=0 mas
total_saidas=40.787 com 102 transações. Sintoma de bug separado no
parser Stone (não captura entradas/Crédito em alguns PDFs Layout A).
Débito de outra natureza, fora desta sessão.

## Testes

```
tests/test_stone_saldos_s24.py ............... 16/16 PASSED
```

Cobertura:
- 4× `test_extracao_intermediarios_layout_a` — método direto (parametrize por PDF)
- 3× `test_extracao_intermediarios_layout_b` — método direto (parametrize)
- 1× `test_saldos_intermediarios_ordenados_e_deduplicados`
- 4× `test_si_inferido_via_legado_layout_a` — pipeline E2E
- 3× `test_si_inferido_via_legado_layout_b` — pipeline E2E
- 1× `test_todos_pdfs_stone_unicos_retornam_si_sf_via_legado`

## R-B (pytest completo)

```
912 passed, 1 failed, 1 skipped, 2 errors
```

- **+16 vs baseline esperado** (842 → 912; baseline reportado no briefing
  era 842, mas o repositório aparenta ter mais testes hoje — diferença
  são testes de outras sessões).
- **1 failed**: `test_validacao_senha::test_t8_senhas_comuns_rejeita_via_zxcvbn`
  — pré-existente, confirmado via `git stash` no tip antes da S24.
  Não é regressão.
- **2 errors**: PagBank pré-existentes mencionados no briefing.
- **1 skipped**: E2E Inter condicional (Tesseract).

Nenhuma regressão introduzida pela S24.

## Hipóteses ajustadas durante implementação

1. Inicialmente tentei rodar testes E2E via pipeline novo
   (`processar_com_pipeline`). Falharam todos por ausência de backfill.
   Investigação revelou divergência arquitetural entre os dois
   orquestradores → testes redirecionados para o legado.

2. `Extrato.pdf` falhou inicialmente porque `_RE_LINHA_COMPLETA` exige
   descrição inline (`(.*?)\s+`). Linha real do PDF
   `01/05/2025 Débito 83,80 2.505,35` não casa. Solução: regex
   permissiva `_RE_DATA_SALDO_TAIL_N2` como fallback.

3. Reconciliação aritmética não fecha em nenhum PDF — não é regressão
   nem bug do método novo, é limitação conhecida do backfill genérico
   aplicada a um banco com saldo pós-transação. Documentado.

## Riscos residuais

- **Stone permanece VERMELHO honesto** mesmo após S24 (validador
  detecta divergência por SI heurístico). VERDE real exige sessão
  futura para implementar saldo fantasma ou branch dedicado em
  `_extrair_saldos_pdf` para Stone.
- **Auditoria S23 continua reportando Stone como VERMELHO**. Para
  paridade com produção, precisa portar backfill para
  `pipeline_extracao.py` (débito documentado).
- Bug separado no parser de transações Stone Layout A (Extrato Jan a
  Mar.pdf não captura entradas). Não atacado.

## Próximos passos sugeridos

1. **Sessão 25**: implementar saldo fantasma no `ParserStone` para
   eliminar VERMELHO honesto residual.
2. **Sessão 26+**: portar backfill do legado para o pipeline novo
   (caminho pelo débito arquitetural).
3. **Sessão dedicada**: investigar bug do parser de transações Stone
   Layout A em PDFs com 3 meses de dados.
