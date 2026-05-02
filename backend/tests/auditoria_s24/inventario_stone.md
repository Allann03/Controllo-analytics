# Inventário Stone — S24 Fase 1 (read-only)

Fonte: 10 PDFs Stone listados em `auditoria_s23/resultado_pipeline.csv`,
todos classificados VERMELHO com diagnóstico "saldo inicial ou final ausente".

PDFs físicos: `backend/tests/fixtures/pdfs_reais/<nome>`
Texto raw: `backend/tests/fixtures/raw_stone/<stem>_raw.txt`

## Tabela completa (10 arquivos, antes da dedup)

| arquivo | md5 | layout | si_localização | si_label | sf_localização | sf_label | observações |
|---|---|---|---|---|---|---|---|
| Extrato Jan a Mar.pdf | 6a41e220 | A | derivado (não há label) | — | derivado (não há label) | — | layout clássico, "Débito"/"Crédito"; coluna SALDO sem prefixo R$ |
| Extrato Stone.pdf | 2153b395 | A | derivado | — | derivado | — | layout clássico; 30 páginas |
| extrato-26172B0E…FDAD.pdf | 659afb39 | B | derivado | — | derivado | — | layout novo (UUID), "Entrada"/"Saída"; valores com prefixo R$; 48 páginas |
| extrato-26172B0E…FDAD_1.pdf | 659afb39 | B | derivado | — | derivado | — | DUPLICATA exata (md5 idêntico) |
| extrato-BF509BF9…A0CF.pdf | 33134919 | B | derivado | — | derivado | — | layout novo |
| extrato-D1A65663…498D.pdf | 4cb999a2 | A | derivado | — | derivado | — | layout clássico apesar do nome UUID |
| extrato-D1A65663…498D_1.pdf | 4cb999a2 | A | derivado | — | derivado | — | DUPLICATA exata |
| Extrato.pdf | 97a80f33 | A | derivado | — | derivado | — | layout clássico |
| Outubro extrato-80EFCACA…C79A.pdf | 10d24c3e | B | derivado | — | derivado | — | layout novo; mês em português no nome |
| Stone.pdf | 33134919 | B | derivado | — | derivado | — | DUPLICATA exata de extrato-BF509BF9 |

## Deduplicação por MD5

3 pares duplicados → **7 PDFs únicos**:

| md5 | arquivos com este md5 |
|---|---|
| 659afb39f298d263481c9f6458bb3aeb | extrato-26172B0E…FDAD.pdf, extrato-26172B0E…FDAD_1.pdf |
| 33134919b1d89c1d4755390bb72f05cc | extrato-BF509BF9…A0CF.pdf, Stone.pdf |
| 4cb999a2d1130267ee7cfe2bebbdfd50 | extrato-D1A65663…498D.pdf, extrato-D1A65663…498D_1.pdf |

## Agrupamento por LAYOUT

### Layout A — "clássico" (4 PDFs únicos)

Cabeçalho:
```
Extrato de conta corrente
Emitido no dia DD de MES de YYYY às HH:MM:SS
Titular <NOME> Instituição Stone Instituição de
<NOME-cont> Pagamento S.A.
Documento <CNPJ> Agência 0001
Período DD/MM/YYYY até DD/MM/YYYY Conta <conta>
DATA TIPO LANÇAMENTO VALOR (R$) SALDO (R$) CONTRAPARTE
```

Padrões:
- Data: **DD/MM/YYYY** (4 dígitos no ano)
- Tipo: `Débito` / `Crédito`
- Valor: sem prefixo `R$`, formato BR (`1.252,83`)
- Saldo: sem prefixo `R$`, mesmo formato
- Linha de transação: `DD/MM/YYYY Tipo [desc] valor saldo [contraparte]` em uma única linha
  ou descrição multi-linha com data/tipo/valor/saldo na linha "âncora"
- Transações em **ordem cronológica reversa** (mais recente primeiro)

PDFs únicos no layout A:
- `6a41e220` Extrato Jan a Mar.pdf (15 páginas, período 01/01–31/03/2025)
- `2153b395` Extrato Stone.pdf (30 páginas, período 01/08–31/08/2025)
- `4cb999a2` extrato-D1A65663…498D.pdf (27 páginas, emitido 17/09/2025, período 01/06–30/06/2025)
- `97a80f33` Extrato.pdf (32 páginas, período 01/05–31/05/2025)

### Layout B — "novo" (3 PDFs únicos)

Cabeçalho:
```
Extrato de conta corrente
Emitido em DD MES YYYY às HHMMSS
Página X de Y
Dados da conta
Nome Documento
<NOME> <CNPJ-sem-formatação>
Instituição Agência Conta
Stone Instituição de Pagamento S.A. <ag> <conta>
Período: de DD/MM/YYYY a DD/MM/YYYY
DATA TIPO DESCRIÇÃO VALOR SALDO CONTRAPARTE
```

Padrões:
- Data: **DD/MM/YY** (2 dígitos no ano)
- Tipo: `Entrada` / `Saída`
- Valor: **com prefixo `R$`**, formato BR (`R$ 1.589,35`)
- Saldo: **com prefixo `R$`**
- Sinal de saída prefixado por `- R$` (ex: `- R$ 0,07`)
- Cabeçalho `DATA TIPO DESCRIÇÃO VALOR SALDO CONTRAPARTE` repetido a cada página
- Transações em **ordem cronológica reversa** (mais recente primeiro)

PDFs únicos no layout B:
- `659afb39` extrato-26172B0E…FDAD.pdf (48 páginas, emitido 04/03/2026)
- `33134919` extrato-BF509BF9…A0CF.pdf / Stone.pdf (31 páginas, emitido 12/02/2026)
- `10d24c3e` Outubro extrato-80EFCACA…C79A.pdf (34 páginas, emitido 10/11/2025)

## Achados sobre SI / SF

**Nenhum** dos 10 PDFs contém os labels textuais procurados:
`saldo anterior`, `saldo inicial`, `saldo final`, `saldo do dia`,
`saldo em DD/MM`, `saldo bloqueado`, `saldo do periodo anterior`.

A única ocorrência da palavra "Saldo" fora do header `SALDO (R$)` é a entrada
descritiva `Ajuste de Saldo` (transação) no PDF `659afb39`.

Ambos os layouts colocam o saldo **APÓS cada transação** na coluna SALDO.
Portanto:
- **SF correto** = saldo da PRIMEIRA linha de transação cronologicamente (mais recente),
  o que, dada a ordem reversa do extrato, é a primeira linha após o header da
  primeira página.
- **SI correto** = saldo da ÚLTIMA linha de transação cronologicamente (mais antiga),
  ajustado pelo valor desta transação:
    - se `Saída`/`Débito`: SI = saldo_pos_ult + valor
    - se `Entrada`/`Crédito`: SI = saldo_pos_ult − valor

## Estado atual do código (read-only)

### `backend/services/extrator_pdf.py::_extrair_saldos_pdf()` (linhas 293–313)
Branch dedicado para `banco == 'stone'` JÁ EXISTE, mas:
- Itera por todas as linhas e atribui `fim = v` ao último match — em ordem
  reversa, esse "último match" é o saldo após a transação **mais antiga**,
  que é incorreto como SF (deveria ser o saldo após a transação mais recente).
- `ini` nunca é atribuído. Comentário inline diz "SI não é extraível de
  forma confiável (saldo na coluna é pós-transação)".
- Retorna `(None, fim)` para todos os 10 PDFs Stone.

Diagnóstico: o sistema reporta SI=None (correto) e SF tecnicamente extraído
mas semanticamente errado em alguns casos (vide CSV onde SF de "Extrato Jan
a Mar.pdf" é 0.00 — saldo após a primeira tx cronológica, não após a última).

### `backend/services/parsers/stone.py`
Parser extrai apenas TRANSAÇÕES; não toca em saldos.
Sem método `_extrair_saldos_intermediarios()` (10 outros parsers o
implementam: c6bank, cora, bb, inter, caixa, pagbank, nubank, safra,
santander_ib_novo, e o stub em base.py).

### Pipeline de saldos no orquestrador (linhas 1377–1491 de extrator_pdf.py)
Caso o parser implemente `_extrair_saldos_intermediarios()` retornando
`[{data, saldo}, …]`, o orquestrador automaticamente:
- infere SI a partir do primeiro saldo intermediário (linha 1397–1401);
- testa modo "abertura" e "fechamento" e escolhe o melhor (linhas 1456–1462);
- backfill propaga SI/SF para o resultado principal (linhas 1483–1491).

Stone hoje não fornece saldos intermediários, então esse pipeline não é
acionado. **Esta é a brecha exata que a Fase 2 deve fechar.**

## Arquivos auxiliares gerados nesta fase

- `backend/tests/auditoria_s24/inspecao_stone.py` — script de extração de raw + MD5 + busca por labels (read-only)
- `backend/tests/auditoria_s24/inspecao_resultado.json` — saída do script (JSON com headers, MD5, hits)
- `backend/tests/fixtures/raw_stone/*_raw.txt` — 10 textos raw extraídos via pdfplumber
