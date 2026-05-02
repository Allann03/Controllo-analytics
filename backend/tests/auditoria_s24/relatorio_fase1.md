# S24 Fase 1 — Stone Parser: Relatório Diagnóstico

Data: 2026-05-01
Branch: `feat/stone-parser-saldos`
Tip antes desta fase: `79331d4` (commit S23)
Status: **read-only, nada commitado**

## Resumo executivo

- 10 PDFs Stone identificados em `auditoria_s23/resultado_pipeline.csv`,
  todos VERMELHO (SI=None em 10/10).
- Após dedup por MD5: **7 PDFs únicos** em **2 layouts distintos**.
- Causa raiz é dupla:
  1. O branch `stone` em `_extrair_saldos_pdf()` deliberadamente retorna
     `(None, fim)` — comentário inline reconhece que "SI não é extraível
     de forma confiável" pois o saldo da coluna é pós-transação. Mas o
     `fim` extraído é semanticamente o saldo após a transação mais ANTIGA
     (o extrato é cronologicamente reverso), não após a mais recente.
  2. O parser `stone.py` não implementa `_extrair_saldos_intermediarios()`,
     então o pipeline de inferência de SI por saldo intermediário (que já
     existe e funciona para outros bancos) nunca é acionado.

## Layouts identificados

### Layout A — clássico (4 PDFs únicos)
- Cabeçalho `Titular X Instituição Stone Instituição de … Período DD/MM/YYYY até DD/MM/YYYY Conta Z`
- Coluna `DATA TIPO LANÇAMENTO VALOR (R$) SALDO (R$) CONTRAPARTE`
- Datas DD/MM/YYYY, valores **sem** prefixo `R$`, tipos `Débito`/`Crédito`
- PDFs: Extrato Jan a Mar, Extrato Stone, extrato-D1A65663, Extrato

### Layout B — novo (3 PDFs únicos)
- Cabeçalho `Dados da conta … Stone Instituição de Pagamento S.A. … Período: de DD/MM/YYYY a DD/MM/YYYY`
- Coluna `DATA TIPO DESCRIÇÃO VALOR SALDO CONTRAPARTE`
- Datas DD/MM/YY, valores **com** prefixo `R$`, tipos `Entrada`/`Saída`,
  saídas prefixadas com `- R$`
- PDFs: extrato-26172B0E, extrato-BF509BF9 (= Stone.pdf), Outubro extrato-80EFCACA

Ambos os layouts compartilham:
- Ausência total de label textual SI/SF (`Saldo anterior`/`Saldo inicial`/
  `Saldo do dia`/etc) — verificado em todas as 18.010 linhas raw.
- Saldo na coluna SALDO é o saldo **após** cada transação.
- Transações em **ordem cronológica reversa** (mais recente primeiro).

## Hipótese de fix (estimativa: BAIXA-MÉDIA complexidade)

A infraestrutura para inferir SI a partir de saldos intermediários já
existe no orquestrador (`extrator_pdf.py` linhas 1377–1491) e funciona
para outros bancos (c6bank, cora, bb, inter, caixa, pagbank, nubank,
safra, santander_ib_novo). Apenas Stone fica de fora porque seu parser
não implementa o gancho.

### Fix proposto (Fase 2)

1. **Implementar `_extrair_saldos_intermediarios()` em
   `backend/services/parsers/stone.py`**, retornando lista
   `[{data: 'DD/MM/YYYY', saldo: Decimal}, …]` em ordem cronológica
   crescente, com 1 entrada por data (último saldo do dia, considerando
   que as transações vêm em ordem reversa).

   - Layout A: regex captura saldo após `valor` na linha-âncora
     `DD/MM/YYYY Tipo [desc] valor saldo …`.
   - Layout B: regex captura saldo após `R$ valor` na linha-âncora
     `DD/MM/YY Tipo [desc] -? R$ valor R$ saldo …`.
   - Ambos devem deduplicar por data, mantendo o saldo da última
     transação cronológica de cada dia (= primeira ocorrência ao ler
     o PDF de cima para baixo, dado o reverse).
   - Normalizar data para DD/MM/YYYY (corrigir layout B que usa YY).

2. **Ajustar branch `stone` em `_extrair_saldos_pdf()`** (extrator_pdf.py
   linhas 293–313) para extrair o SF correto: pegar o **primeiro** match
   da regex (não o último), pois é o saldo após a transação mais recente.
   Manter `ini = None` aqui — o backfill via verificação progressiva
   resolve.

   Alternativa mais conservadora: deixar o branch como está e confiar
   apenas no backfill via `_extrair_saldos_intermediarios()`. O backfill
   recalcula `saldo_final = saldo_inicial + (entradas − saídas)`, que é
   matematicamente correto se SI estiver correto e as transações cobrirem
   todo o período.

### Verificação cruzada esperada após fix
- SI inferido (primeiro saldo intermediário) ± valor da transação inicial
  (modo abertura vs fechamento — o orquestrador testa ambos).
- SF calculado deve casar com o saldo após a transação cronologicamente
  mais recente.
- `verificacao_saldos.divergencias` deve ficar vazio para os 7 PDFs
  únicos (ou conter apenas dias com tarifa silenciosa).

## Riscos identificados

1. **Multi-linha**: descrições de transação em Stone podem ocupar várias
   linhas. A linha-âncora (com data) já é detectada pelo parser atual via
   `_RE_LINHA_TEXTO`/`_RE_LINHA_SIMPLES`. Reaproveitar essas regex para o
   `_extrair_saldos_intermediarios()` minimiza divergência.
2. **Layout A vs Layout B**: as regex precisam ser duas; o método
   `_detectar_formato()` já existe e retorna `n1`/`n2`/`auto`. O método
   intermediário pode usar essa detecção ou tentar ambas.
3. **Stone N2 (Crédito/Débito)**: existe um parser separado
   `stone_n2.py`. Precisa receber o mesmo tratamento ou compartilhar
   helper. Vale checar na Fase 2.
4. **Tarifas embutidas no Layout B**: linhas tipo `Saída Tarifa - R$ 0,07
   R$ 62,85` mostram que a tarifa pode estar como linha separada com
   descrição "Tarifa" embutida no campo CONTRAPARTE — já tratado pelo
   parser atual.
5. **Ajuste de Saldo** (apenas em PDF `659afb39`): aparece como tipo de
   transação. Tratar como entrada/saída normal — não confundir com label
   de saldo.
6. **Duplicatas**: 3 pares duplicados (md5 idêntico) entre os 10
   originais. Não é problema de parsing, é input duplicado do usuário.
7. **stone_n2.py paralelo**: parser N2 pode ter divergência sutil com N1
   na detecção de saldo. Inspecionar antes de implementar.

## Recomendação

**Avançar direto para Fase 2** sem Fase 1.5. Os achados são suficientes
para escrever o fix. Estimativa: 1 turno para implementar
`_extrair_saldos_intermediarios()` em Stone (N1 e N2), 1 turno para
testes de regressão sobre os 7 PDFs únicos e os outros bancos.

Roteiro sugerido para Fase 2:
1. Inspecionar `stone_n2.py` (read-only).
2. Implementar `_extrair_saldos_intermediarios()` no `ParserStone`,
   reutilizando regex existentes ou variantes que captem o saldo final
   da linha. Layout A e Layout B em métodos separados se necessário.
3. Decidir se precisa também em `ParserStoneN2`.
4. Ajustar branch stone de `_extrair_saldos_pdf()` se necessário (talvez
   só ajustar para retornar primeiro match em vez de último, ou remover
   a extração de fim e deixar tudo via backfill).
5. Rodar `auditoria_s23` (já implementada) e confirmar 10/10 → VERDE
   ou pelo menos AMARELO com SI presente.
6. Commit dedicado por escopo.
