# Passo 6 — Bradesco CW TOUR: análise das descrições trocadas

## Metadados de execução

```json
{
  "executado_com": {
    "python": "3.14.4",
    "pikepdf": "10.5.1",
    "pdfplumber": "0.11.9",
    "pdfminer.six": "20251230",
    "pymupdf": "1.27.2"
  },
  "ambiente": "local-allan-windows",
  "obs": "ATENÇÃO: requirements.txt pina pikepdf==9.7.0; produção pode ter versão diferente. Output do Lightsail em versoes-producao.txt."
}
```

---

## Fixture

- **Arquivo:** `backend/tests/fixtures/pdfs_reais/diag-2026-04-30/Bradesco_Net_Empresas__2_.pdf`
- **SHA-256:** `26e6ada3d856f858337a2e15fcf5552a07bde2fc57491899144658077064525f`
- **Cliente:** CW TOUR EIRELI (CNPJ 004.699.574/0001-50)
- **Período:** 01/01/2026 a 31/01/2026 (+ "Últimos Lançamentos" de 05/02 a 10/02)
- **Layout:** Bradesco Net Empresas, formato multi-linha "Data | Lançamento | Dcto. | Crédito | Débito | Saldo"
- **Producer (pikepdf):** `Skia/PDF m143 Google Docs Renderer`
- **Detecção do pipeline:** `bradesco_net_empresas` (correto)
- **Tx extraídas:** 13

---

## Tabela linha-do-PDF-bruta vs linha-no-parser-output

Numeração L## = número da linha no raw extraído via pdfplumber (raw em [raw-texts/Bradesco_Net_Empresas__2_.txt](raw-texts/Bradesco_Net_Empresas__2_.txt)).

| Tx# | Linhas raw envolvidas | Descrição esperada | Descrição obtida pelo parser | Diagnóstico |
|---|---|---|---|---|
| 1 | L17 `ENCARGOS LIMITE DE CRED` <br> L18 `05/01/2026 7868963 -45,20 -963,58` <br> L19 `ENCARGO - 16,49%` | `ENCARGOS LIMITE DE CRED 7868963 ENCARGO - 16,49%` | `ENCARGOS LIMITE DE CRED 7868963 ENCARGO - 16,49%` | **OK** (multi-linha resolvido corretamente) |
| 2 | L20 `IOF S/ UTILIZACAO LIMITE 7868963 -4,12 -967,70` <br> L21 `TRANSFERENCIA PIX` (← desc da tx 3) | `IOF S/ UTILIZACAO LIMITE 7868963` | `IOF S/ UTILIZACAO LIMITE 7868963 TRANSFERENCIA PIX` | **BUG**: lookahead engoliu a desc da tx seguinte |
| 3 | L21 `TRANSFERENCIA PIX` <br> L22 `07/01/2026 951320 1.000,00 32,30` <br> L23 `REM: CW TOUR LTDA 07/01` | `TRANSFERENCIA PIX 951320 REM: CW TOUR LTDA 07/01` | `951320 REM: CW TOUR LTDA 07/01` | **BUG**: perdeu o rótulo `TRANSFERENCIA PIX` (já consumido pela tx 2) |
| 4 | L24 `PAGTO ELETRON COBRANCA` <br> L25 `12/01/2026 105 -595,43 -563,13` <br> L26 `070548543401100503BRADESCO ADMIN` | `PAGTO ELETRON COBRANCA 105 070548543401100503BRADESCO ADMIN` | `PAGTO ELETRON COBRANCA 105 070548543401100503BRADESCO ADMIN` | **OK** |
| 5 | L27 `CARTAO CREDITO ANUIDADE 4740012 -38,00 -601,13` <br> L28 `TARIFA BANCARIA` (← desc da tx 6) | `CARTAO CREDITO ANUIDADE 4740012` | `CARTAO CREDITO ANUIDADE 4740012 TARIFA BANCARIA` | **BUG**: idêntico à tx 2 — lookahead engoliu desc da próxima |
| 6 | L28 `TARIFA BANCARIA` <br> L29 `15/01/2026 20126 -168,50 -769,63` <br> L30 `CESTA PJ FACIL 1` | `TARIFA BANCARIA 20126 CESTA PJ FACIL 1` | `20126 CESTA PJ FACIL` | **BUG**: perdeu rótulo `TARIFA BANCARIA` (consumido pela tx 5). `CESTA PJ FACIL 1` virou `CESTA PJ FACIL` por conta de `_RE_TRAILING_INTS` em `_limpar_descricao` |
| 7 | L31 `TRANSFERENCIA PIX` <br> L32 `30/01/2026 1709091 1.500,00 730,37` <br> L33 `REM: CW TOUR LTDA 30/01` | `TRANSFERENCIA PIX 1709091 REM: CW TOUR LTDA 30/01` | `TRANSFERENCIA PIX 1709091 REM: CW TOUR LTDA 30/01` | **OK** |
| 8 | L34 `TITULO DE CAPITALIZACAO` <br> L35 `3000093 -500,00 230,37` <br> L36 `CAPITALIZACAO 1235 0050170217-0` | `TITULO DE CAPITALIZACAO 3000093 CAPITALIZACAO 1235 0050170217-0` | `TITULO DE CAPITALIZACAO 3000093 CAPITALIZACAO 1235 0050170217-0` | **OK** |
| 9 | L37 `APLIC.INVEST FACIL 4751785 -229,37 1,00` | `APLIC.INVEST FACIL 4751785` ou `APLIC.INVEST FACIL` | `APLIC.INVEST FACIL` | **OK** (não há lookahead viável: próxima linha real é "Total ...") |
| 10 | L43 `10/02/2026 RESG.AUTOM.INVEST FACIL* 100226 124,02 125,02` <br> L44 `PAGTO ELETRON COBRANCA` (← desc da tx 11) | `RESG.AUTOM.INVEST FACIL* 100226` | `RESG.AUTOM.INVEST FACIL* 100226 PAGTO ELETRON COBRANCA` | **BUG**: idêntico à tx 2/5 |
| 11 | L44 `PAGTO ELETRON COBRANCA` <br> L45 `106 -588,22 -463,20` <br> L46 `070548543401100503BRADESCO ADMIN` | `PAGTO ELETRON COBRANCA 106 070548543401100503BRADESCO ADMIN` | `106 070548543401100503BRADESCO ADMIN` | **BUG**: idêntico à tx 3/6 |
| 12 | L47 `PAGTO ELETRON COBRANCA` <br> L48 `107 -746,69 -1.209,89` <br> L49 `070553661201069205BRADESCO ADMIN` | `PAGTO ELETRON COBRANCA 107 070553661201069205BRADESCO ADMIN` | `PAGTO ELETRON COBRANCA 107 070553661201069205BRADESCO ADMIN` | **OK** (porque a tx 11 não conseguiu engolir o "PAGTO ELETRON COBRANCA" da L47 — já estava no desc_buffer para uma tx que não veio?) |
| 13 | L50 `CARTAO CREDITO ANUIDADE 4740041 -38,00 -1.247,89` | `CARTAO CREDITO ANUIDADE 4740041` ou `CARTAO CREDITO ANUIDADE` | `CARTAO CREDITO ANUIDADE` | **OK** |

**Total:** 5 transações com bug confirmado (tx 2, 3, 5, 6, 10, 11) — bug afeta **~46% das transações** deste fixture (6/13).

---

## Local exato do bug no código

Arquivo: [backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py](backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py)

### Bloco 1 — branch "linha completa com data inline" ([linhas 177-186](backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py#L177-L186))

```python
# Olhar proxima linha: se e descricao pura, e continuacao
desc_depois = ''
if i < len(linhas_raw):
    prox = linhas_raw[i].strip()
    if prox and not _e_linha_skip(prox) and not _RE_DATA_LINHA.match(prox) and len(_extrair_valores(prox)) < 2:
        desc_depois = prox
        i += 1

if desc_depois:
    desc_parts.append(desc_depois)
```

### Bloco 2 — branch "linha de valor sem data" ([linhas 204-213](backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py#L204-L213))

```python
# Olhar proxima linha: se e descricao pura, e continuacao desta tx
desc_depois = ''
if i < len(linhas_raw):
    prox = linhas_raw[i].strip()
    if prox and not _e_linha_skip(prox) and not _RE_DATA_LINHA.match(prox) and len(_extrair_valores(prox)) < 2:
        desc_depois = prox
        i += 1

if desc_depois:
    desc_parts.append(desc_depois)
```

### Causa raiz

Ambos os blocos consomem a próxima linha como continuação **sem checar se a linha-depois-da-próxima começa com data** (DD/MM/YYYY). No formato CW TOUR, frequentemente a sequência é:

```
<linha completa com data inline>      <- tx N
<descrição-só-texto>                  <- na verdade é desc da tx N+1
<linha com data DD/MM/YYYY ...>       <- tx N+1
```

A heurística atual deveria checar **2 linhas à frente** e abortar o consumo se a linha seguinte-da-seguinte começa com data ou contém `len(valores) >= 2` (linha de valor sem data).

### Por que tx 1, 4, 7, 8 funcionam?

- **Tx 1, 4, 7, 8** são casos onde a linha-anterior (descrição sem data) foi corretamente acumulada em `desc_buffer` antes do parser ver a linha-com-data. O bug não afeta o caso "desc_anterior-com-data-na-linha-seguinte"; afeta o caso "linha-completa-inline + desc-pura-na-próxima".

- **Tx 12** funciona "por sorte" — a tx 11 (que tem o bug) já consumiu seu `i++`, e o parser cai num estado onde `desc_buffer` está vazio, mas a próxima linha real (`PAGTO ELETRON COBRANCA` na L47) é puro texto e vira `desc_buffer` antes do parser ver a linha de valor da tx 12. Coincidência semântica.

---

## Sintoma observado pelo usuário (corroborado)

O Allan reportou: "Bradesco_Net_Empresas (2).pdf extrai 13 transações no frontend, mas com descrições concatenadas erradamente entre transações vizinhas". **Confirmado**: 6 das 13 transações têm descrições deslocadas (a desc de N foi parar em N-1, a desc de N+1 foi engolida pela linha-de-valor-inline de N).

## Sugestão de fix (NÃO IMPLEMENTAR NESTA SESSÃO)

Estender a condição do lookahead para abortar quando há sinal claro de "isto pertence à próxima tx":

```python
# pseudocódigo — só engole "prox" como continuação se a linha DEPOIS de prox
# NÃO for início de outra transação
prox = linhas_raw[i].strip() if i < len(linhas_raw) else ''
prox_prox = linhas_raw[i+1].strip() if i+1 < len(linhas_raw) else ''
prox_e_continuacao = (
    prox
    and not _e_linha_skip(prox)
    and not _RE_DATA_LINHA.match(prox)
    and len(_extrair_valores(prox)) < 2
    and not _RE_DATA_LINHA.match(prox_prox)        # NOVO
    and not (len(_extrair_valores(prox_prox)) >= 2 and not _RE_DATA_LINHA.match(prox_prox))  # NOVO
)
```

Validar fix re-rodando este fixture + os 15 testes determinísticos da [Sessão 10 Turno 1](docs/diagnostico-parsers.md) (Bradesco Net A/B) — risco de regressão alto sem cobertura.

---

## Bradesco_Net_Empresas.PDF (SEOLIN, jan/2025) — caso adjacente

Este PDF foi mis-detectado pelo pipeline como `bradesco` (parser legado), não `bradesco_net_empresas`, e ainda assim retornou 20 transações. Não está coberto pelo Passo 6 stricto-sensu (que era especificamente sobre o CW TOUR), mas merece nota:

- **SHA-256:** `<ver passo4-catalogo.json>`
- **Producer:** iText 2.0.8 (by lowagie.com)
- **Detecção atual:** `bradesco` (legado)
- **Detecção desejável:** `bradesco_net_empresas` (mesmo título "Extrato Consolidado / Por Período" e mesma estrutura multi-linha do CW TOUR)
- **Implicação:** mesmo se o bug do lookahead for corrigido, este PDF não se beneficiará do fix porque cai no parser errado. Próxima sprint deve revisar `_ASSINATURAS` para forçar `bradesco_net_empresas` quando o título "Extrato Consolidado / Por Período" + colunas "Crédito (R$) Débito (R$) Saldo (R$)" aparecerem juntos.
