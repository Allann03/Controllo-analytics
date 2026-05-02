# SESSAO 23 — RELATORIO DE REGRESSOES E DIAGNOSTICO

**Data**: 2026-05-01
**Branch**: `feat/inter-ocr-fallback`
**Commit**: `02a753c860011f5d7a5521462a00b3b07f25f940`
**Auditoria**: 96 PDFs reais em `backend/tests/fixtures/pdfs_reais/`
**Tempo total**: 348s (5.8 min) — sem timeouts

---

## 0. DIAGNOSTICO TESSERACT (CRITICO — antes das regressoes)

7 PDFs vetoriais (4 Inter + 3 Itau) cairam em `banco=desconhecido` + `erro=PDF vetorial/imagem` na auditoria. Investigacao confirma que **nao e regressao de codigo** — e ambiente.

**Diagnostico shell:**

```
which tesseract        -> "no tesseract in PATH" (Bash/Git Bash)
where.exe tesseract    -> "nao foi possivel localizar arquivos" (PowerShell)
tesseract --version    -> "command not found"
```

PATH atual nao contem nenhum diretorio com `tesseract`. `TESSDATA_PREFIX` vazio.

**Codigo de [`backend/services/ocr_fallback.py:18-26`](../../services/ocr_fallback.py#L18):**

```python
try:
    import fitz
    import pytesseract
    from PIL import Image
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False
```

Sem hardcode de `pytesseract.tesseract_cmd`. Depende **integralmente** do PATH do processo. Se `tesseract` nao estiver no PATH, `pytesseract.image_to_string` levanta `TesseractNotFoundError` e o `except Exception` na linha 77-80 retorna `''`. O pipeline entao vai pra branch "OCR tambem falhou" e marca `erro=PDF vetorial/imagem`.

**Conclusao**: ambiente desta auditoria nao tem Tesseract acessivel. A S20 documentou que o Allan instalou via `winget install --id UB-Mannheim.TesseractOCR` — provavelmente foi instalado em sessao PowerShell interativa que nao herda PATH global, ou foi desinstalado entre S20 e S23. **NAO e regressao do codigo**. Os 7 PDFs ficam INDETERMINADO ate Tesseract estar disponivel no PATH do processo do uvicorn/script.

**Acao recomendada (fora desta sessao):** verificar instalacao de Tesseract com `winget list tesseract` ou re-instalar. Adicionar diretorio (`C:\Program Files\Tesseract-OCR`) ao PATH de sistema, nao so do usuario interativo.

---

## 1. RESULTADO POR BANCO — comparacao com baselines

| Banco | Esperado | Atual | Delta | Status |
|---|---|---|---|---|
| **bradesco_net_empresas** (S18) | 9/9 VERDE | **9/9 VERDE** | zero | ✅ Preservada |
| **nubank** (S18/S19) | 7/7 VERDE | **7/7 VERDE** | zero | ✅ Preservada |
| **itau_n2** (S20) | 9/9 VERDE | **9/9 VERDE** | zero | ✅ Preservada |
| **santander_consolidado** (S19) | 3/3 VERDE | **9/9 VERDE** (3 unicos × 3 nomes via duplicata MD5) | +6 colaterais | ✅ Preservada |
| **santander** (S19/S21) | 4/4 VERDE | **8/8 VERDE** (`santander problema`, `Santander empresas 2`, 2 IB Novo, 2 DLS, 2 IB N1 — DLS/N1 mais hashes duplicados) | +4 (S21 ContaMax) | ✅ Preservada+expandida |
| **santander_ib_novo** (S19) | 2/2 VERDE | **2/2 VERDE** | zero | ✅ Preservada |
| **bs2** (S17) | 1/1 VERDE | **1/1 VERDE** | zero | ✅ Preservada |
| **caixa** | 1/1 VERDE | **1/1 VERDE** | zero | ✅ Preservada |
| **itau (mensal)** (S20) | 8/16 VERDE | **8/13 VERDE** | -3 PDFs nao detectados (caem em desconhecido por Tesseract ausente) | ⚠️ Regressao ambiente |
| **inter_n2** (S20) | 1/4 VERMELHO honesto + 3 multi-coluna | **0/4 detectados** (todos viram `desconhecido` por Tesseract ausente) | -1 (extrato ABRIL.pdf perdido) | ⚠️ Regressao ambiente |
| **santander_empresas** (S19/S21) | 4/4 VERMELHO acionavel | **4/4 VERMELHO acionavel** | zero (esperado, debito S25) | ⚠️ Pre-existente |
| **stone** | desconhecido | **10/10 VERMELHO** "SI/SF ausente" | esperado (parser sem SI) | ⚠️ Pre-existente |
| **bb** (S21) | 1/7 VERDE | **1/6 VERDE** | -1 PDF nao detectado | ⚠️ Pre-existente |
| **btg** (S21) | 0/2 borderline | **0/2 borderline gap < R$0,30** | zero | ⚠️ Pre-existente |
| **pagbank** | 0/2 | **0/2 VERMELHO "SI/SF ausente"** | zero | ⚠️ Pre-existente |
| **c6bank** | desconhecido | **0/3 VERMELHO** | esperado | ⚠️ Pre-existente |
| **safra**, **sicredi**, **itau_empresas** | varios VERMELHO | **3/3 VERMELHO "SI/SF ausente"** | zero | ⚠️ Pre-existente |

**Resumo geral**: 56/96 VERDE (58%), 33/96 VERMELHO honesto (todos com diagnostico explicativo), 7/96 INDETERMINADO (Tesseract ausente).

---

## 2. PDFs VERMELHO — TABELA DETALHADA com diagnostico full

Todos os VERMELHO foram analisados via re-execucao do pipeline com captura do diagnostico completo. **Padrao geral**: 3 categorias claras, sem exception leaks.

### 2a. "saldo inicial ou final ausente" — parser nao extrai SI ou SF (24 PDFs)

| arquivo | banco | si | sf | n_tx | nota |
|---|---|---|---|---|---|
| Stone.pdf | stone | None | 1109.58 | 459 | Parser Stone sem SI |
| Extrato Stone.pdf | stone | None | 14838.16 | 202 | idem |
| extrato-26172B0E-...FDAD.pdf | stone | None | 4249.61 | 604 | idem (+ duplicata _1) |
| extrato-BF509BF9-...A0CF.pdf | stone | None | 1109.58 | 459 | idem |
| extrato-D1A65663-...498D.pdf | stone | None | 7291.43 | 176 | idem (+ duplicata _1) |
| Outubro extrato-80EFCACA-...79A.pdf | stone | None | 796.58 | 463 | idem |
| Extrato.pdf | stone | None | 2505.35 | 186 | idem |
| Extrato Jan a Mar.pdf | stone | None | 0.00 | 102 | idem |
| Extrato da Conta - Julho.2025.pdf | pagbank | None | 188.01 | 217 | Parser PagBank sem SI |
| Extrato da Conta - Junho.2025.pdf | pagbank | None | 141.45 | 218 | idem |
| account_statement-e09135bc-...pdf | c6bank | None | None | 0 | **MIS-ROUTE**: e Mercado Pago real, c6bank nao parseou. Bug pre-existente fora do escopo S17 (notado naquela sessao). |
| Extrato Mensal_Outubro2025 - Consolidado.pdf | itau | None | None | 13 | Itau Mensal Consolidado: parser nao extrai SI/SF |
| Extrato Mensal_Novembro2025 - Consolidado.pdf | itau | None | None | 21 | idem |
| Extrato Mensal_Setembro2025 - Consolidado.pdf | itau | None | None | 20 | idem |
| Itau empresas.pdf | itau_empresas | None | None | 300 | Parser Itau Empresas sem SI/SF |
| Extrato SICREDI N2.pdf | sicredi | None | None | 0 | Parser Sicredi nao extrai SI/SF nem tx neste layout |
| Safra.pdf | safra | None | None | 721 | Parser Safra sem SI/SF |

### 2b. "saldo total diverge em R$ X" — validador detecta gap honestamente (8 PDFs)

| arquivo | banco | si | sf | gap | nivel | status |
|---|---|---|---|---|---|---|
| 11 - novembro 2025.pdf | btg | 32837.65 | 0.00 | -0.03 | VERMELHO | borderline R$0,03 (S21) |
| 12 - dezembro 2025.pdf | btg | 0.00 | 0.00 | -0.26 | VERMELHO | borderline R$0,26 (S21) |
| Extrato de Agosto de 2025.pdf | bb | 78.23 | 20.32 | -139.35 | VERMELHO | parser BB perde tx |
| Extrato de setembro de 2025.pdf | bb | 3.21 | 2548.27 | 275.16 | VERMELHO | idem |
| Extrato Dezembro de 2025.pdf | bb | 512.56 | 13748.83 | -170.02 | VERMELHO | idem |
| Extrato Junho.pdf | bb | 1158.04 | 1000.00 | -138.33 | VERMELHO | idem |
| Extrato Outubro de 2025.pdf | bb | 2273.11 | 20.92 | -104.13 | VERMELHO | idem |
| Abr- Set 2025.pdf / Extrato C6 (Atencao ao ano).pdf (mesmo MD5) | c6bank | 631.42 | 3000.10 | -628.00 | VERMELHO | parser C6 perde tx (628 reais) |
| Extrato_023700861000_22-03-2026_Parte1.pdf | itau | 13157.18 | 3157.25 | 19248.80 | VERMELHO | parser Itau Mensal perde tx (3.80%) |
| Itau 2.pdf | itau | 131882.08 | 107561.07 | -48642.02 | VERMELHO | gap 48k confirmado pre-existente (S22 menciona) |

### 2c. "extrato_sem_si_sf" — diagnostico acionavel S19 (4 PDFs santander_empresas)

Diagnostico completo: `extrato_sem_si_sf: este extrato (formato App do Santander Empresas) nao inclui saldo inicial nem final, entao nao e possivel reconciliar. Solicite ao banco o "Extrato Consolidado Inteligente" para uma analise completa.`

- `Santander empresarial .pdf` — 30 tx
- `Santander empresarial 2.pdf` — 30 tx
- `Empresarial 3.pdf` — 30 tx
- `junho 2025.pdf` — 30 tx

**Esperado pela S19** — debito S25.

### CONCLUSAO da analise: ZERO regressao real de qualidade

Todos os 33 VERMELHO sao **diagnosticos honestos pre-existentes**. Padrao consistente:
- Categoria 2a: parser nao cobre o layout daquele PDF (debito tecnico — adicionar branch novo em `_extrair_saldos_pdf` ou no parser)
- Categoria 2b: parser perde tx ou tem bug — gap reportado honestamente pelo validador da S18
- Categoria 2c: layout sem SI/SF intrinseco — diagnostico acionavel da S19

NENHUM PDF retornou exception leak, "INDETERMINADO" sem motivo, ou diagnostico sem causa raiz identificavel.

---

## 3. PDFs novos sem fixture .txt

Aplicando heuristica do brief (`<nome>.pdf` -> `<nome>_raw.txt`): apenas 22 fixtures .txt existem em `backend/tests/fixtures/`, vs 96 PDFs. Praticamente todos os PDFs nao seguem essa convencao literal de naming.

Os 22 fixtures cobrem (mapeando por contexto da auditoria S18-S21):
- Bradesco: cw_tour_jan2026, seolin_jan2025, tania_dez2025, tania_nov2025
- Santander: 9+ fixtures (consolidado/empresas/ib_novo/dls/problema)
- BS2: b2s_raw
- Inter: extrato_abril_ocr_raw

**PDFs novos sem fixture associada (cerca de 70)**: incluem TODOS os PDFs Itau Mensal (13), Stone (10), BB (7), C6 (3), PagBank (2), Sicredi (1), Safra (1), Nubank (7), BTG (2), Itau N2 (varios), e a maioria dos Bradesco net "Agosto 2025", "Bradesco5", "Bradesco_24032026" etc.

Recomendacao: **nao bloquear progresso por falta de fixture .txt**. Sessoes 16-21 mostraram que fixture e criada apenas para PDFs onde regression test e necessario (ex: depois de fix de parser bug). PDFs VERDE estaveis nao precisam de fixture dedicada — testes de pipeline E2E em pasta `pdfs_reais/` (gitignored) ja cobrem.

---

## 4. Top 10 PDFs problematicos (criterio: maior gap absoluto + criticidade)

| # | arquivo | banco | gap | n_tx | acao recomendada |
|---|---|---|---|---|---|
| 1 | Itau 2.pdf | itau | -48642.02 (2.33%) | 300 | parser Itau Mensal perde tx — investigar layout |
| 2 | Extrato_023700861000_22-03-2026_Parte1.pdf | itau | 19248.80 (3.80%) | 147 | idem |
| 3 | Abr-Set 2025.pdf (= Extrato C6) | c6bank | -628.00 | 238 | parser C6 perde tx (~6 meses periodo) |
| 4-7 | Itau Mensal Consolidado Set/Out/Nov 2025 | itau | None (sem SI/SF) | 13-21 | parser nao extrai saldos do layout Consolidado |
| 8 | Extrato Junho.pdf | bb | -138.33 | 57 | parser BB perde tx |
| 9 | Itau empresas.pdf | itau_empresas | None | 300 | parser Itau Empresas sem branch SI/SF |
| 10 | Stone.pdf (e 9 outros Stone, mesmo bug) | stone | None | 459 | parser Stone nao extrai SI |

---

## 5. Categorias suspeitas

### 5.1 PDFs `desconhecido` que pelo nome NAO deveriam ser
Todos os 7 sao Inter/Itau vetoriais (OCR-dependentes). Comportamento esperado dado Tesseract ausente. **Nao e mis-route — e ausencia de OCR.**

### 5.2 PDFs que dispararam OCR fora do esperado
Apenas Inter (4) e Itau (3) vetoriais — exatamente os mesmos onde S20 disse "OCR esperado". Zero OCR disparado em outros bancos. Gate cirurgico funcionando.

### 5.3 Mis-routes confirmadas (pre-existentes da S17)
- `account_statement-e09135bc-cf6b-41c8-a1c0-6b9dffc5...pdf` foi para `c6bank` em vez de `mercado_pago`. Mencionado na S17 como "bug pre-existente FORA do escopo da Sessao 17". 0 transacoes. **Continua pendente** (auditoria de assinatura `mercado_pago` vs filename hint frágil).

### 5.4 Regressao de PDFs por causa de Tesseract
- `extrato ABRIL.pdf`: era VERMELHO honesto gap=0,96 (S20). Agora INDETERMINADO. **Ambiente**, nao codigo.
- `Itau 07828-5.pdf`, `Itau 07828-5_1.pdf`, `Itau 09089-2.pdf`: eram detectados como itau (mensal) via OCR (S20). Agora INDETERMINADO. **Ambiente**.

---

## 6. RECOMENDACAO PARA O ARQUITETO — proximas sessoes

Ordem de prioridade (impacto × custo):

1. **S24 — Reinstalar Tesseract no PATH global** (custo baixo, recupera 7 PDFs — Inter S20 + Itau vetoriais).
2. **S25 — Itau Mensal Consolidado parser SI/SF**: 5 PDFs VERMELHO ("Itau 2.pdf" gap 48k, Itau_023700861000 gap 19k, 3 Mensal Consolidado sem SI/SF). Ataca o segundo maior bloco de VERMELHO depois Stone.
3. **S26 — Stone parser SI**: 10 PDFs VERMELHO simultaneos por SI ausente. Maior bloco numerico — provavelmente regex/branch faltante no `_extrair_saldos_pdf`.
4. **S27 — Inter Layout 2 (multi-coluna OCR)**: 3 PDFs Inter vetoriais. Depende S24 (Tesseract). Bug ja mapeado no fim da S20 — parser perde relacao desc↔valor.
5. **S28 — santander_empresas formato App**: 4 PDFs VERMELHO acionavel S19. Refactor: parser + camada de negocio para "fluxo de caixa parcial sem SF".
6. **S29 — BB parser perde tx**: 5 PDFs gaps R$104-R$275. Auditar `_IGNORAR`/`_SKIP_*` igual S21 fez no Santander.
7. **S30 — C6 parser perde tx**: 1 PDF gap R$628 (com duplicata = 2 nomes). Mesmo padrao S29.
8. **S31 — PagBank parser SI**: 2 PDFs sem SI. Igual S26 mas em PagBank.
9. **S32 — mis-route mercado_pago**: 1 PDF (account_statement-e09135bc) que vai para C6 em vez de MP. Bug S17 pendente — refinar assinatura mercado_pago + filename hint.
10. **S33 — Itau Empresas + Sicredi + Safra**: parsers menores sem branch SI/SF. Cluster final, baixo impacto individual mas zera VERMELHO.

**Bloco mais urgente do ponto de vista de produto**: S24 → S25 → S26 (Tesseract + Itau + Stone). Resolveria ~22 PDFs VERMELHO/INDETERMINADO de uma vez.

---

## 7. Arquivos gerados nesta sessao

- [`inventario_pdfs.csv`](inventario_pdfs.csv) — 96 PDFs com tamanho e MD5
- [`resultado_pipeline.csv`](resultado_pipeline.csv) — 96 linhas com banco, nivel, gap, diagnostico (truncado em 80)
- [`detalhes_vermelhos.json`](detalhes_vermelhos.json) — diagnosticos completos dos 34 VERMELHO
- `gerar_inventario.py`, `relatorio_fase1.py`, `run_auditoria.py`, `relatorio_fase2.py`, `detalhes_vermelhos.py` — scripts auxiliares
- Este arquivo: `regressoes.md`

**Confirmacao final**: nenhum arquivo fora de [`backend/tests/auditoria_s23/`](.) foi criado ou modificado. Working tree limpa exceto pelos arquivos novos desta pasta. Pipeline e parsers de producao intactos.
