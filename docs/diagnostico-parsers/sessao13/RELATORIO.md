# Relatório de Diagnóstico Multi-Banco — Sessão 13

| | |
|---|---|
| **Data** | 2026-04-30 |
| **Branch** | `diag/multibanco-2026-04-30` |
| **Commit base (origem main)** | `3f7c0dd33569043ccfcef5bf256dbb88de9fdf28` |
| **Executor** | Claude Code (modo read-only) |
| **Escopo** | Diagnóstico de Bradesco / Santander / BS2 com 9 PDFs reais |
| **Política respeitada** | Nenhum PDF binário commitado (`.gitignore`/`pdfs_reais/.gitignore`). Raw texts em `raw-texts/`. SHAs no inventário abaixo. |

---

## 1. Versões de libs

| Lib | requirements.txt | Local (sessão diag) | Produção (Lightsail) |
|---|---|---|---|
| Python | 3.11 / 3.12 (Dockerfile.prod) | 3.14.4 | **a preencher** |
| pikepdf | `==9.7.0` | **10.5.1** ⚠️ diverge | **a preencher** |
| pdfplumber | `==0.11.9` | 0.11.9 | **a preencher** |
| pdfminer.six | `==20251230` | 20251230 | **a preencher** |
| PyMuPDF | `==1.27.2` | 1.27.2 | **a preencher** |

⚠️ **Divergência local vs requirements:** o venv versionado em `backend/venv/` foi instalado/atualizado para `pikepdf 10.5.1`, mas o lockfile `requirements.txt` ainda fixa `9.7.0`. A imagem Docker de produção foi construída a partir de `requirements.txt` (logo, **provavelmente** roda 9.7.0). Se confirmado, isso é o candidato mais forte para a causa do erro `/Root dictionary`.

---

## 2. Stack trace real do erro `/Root dictionary`

### Status: **PENDENTE — Lightsail não foi consultado**

Os comandos SSH a serem executados em produção estão em [comandos-allan-lightsail.md](comandos-allan-lightsail.md). Quando executados, os outputs serão salvos em:
- [versoes-producao.txt](versoes-producao.txt) (placeholder)
- [stack-trace-root-dictionary.txt](stack-trace-root-dictionary.txt) (placeholder)

**Hipótese principal a confirmar:** o erro `/Root dictionary` é lançado por `pikepdf 9.7.0` (versão de produção) ao tentar abrir um PDF gerado por motor moderno (Skia/PDF m143 ou m145, presentes no `Santander_Internet_Banking_N1.pdf` e no `Bradesco_Net_Empresas__2_.pdf`). Localmente, com `pikepdf 10.5.1`, **nenhum dos 9 PDFs reproduziu o erro** — todos abriram normalmente em pikepdf e em pdfplumber.

---

## 3. Catálogo de PDFs (Inventário de fixtures)

| Filename | SHA-256 | Tamanho | Páginas | Producer |
|---|---|---|---|---|
| B2S.pdf | `cf781b936d6c1e827cbfe26cfed3a2ff1c03daa0cab8770bd58d8a69c0a6014b` | 72.067 B | 2 | (sem metadados) |
| Bradesco_net.pdf | `2a2f114e4034848841de7bc74d8b4ad1704b79f320ba272eda4647989abcfe9d` | 30.950 B | 3 | iText 2.0.8 (by lowagie.com) |
| Bradesco_net2.pdf | `d75820f5eb6d16e6857a91f3151b5a85e5f797756f1a57f92a1cebb3eb95e876` | 31.992 B | 3 | iText 2.0.8 (by lowagie.com) |
| Bradesco_Net_Empresas.PDF | `f1a29e33b65b91b38b8cf843dd6d4d71111c34b9e7b98dc3e4ca59dcf169514f` | 14.101 B | 1 | iText 2.0.8 (by lowagie.com) |
| Bradesco_Net_Empresas__2_.pdf | `26e6ada3d856f858337a2e15fcf5552a07bde2fc57491899144658077064525f` | 156.284 B | 1 | **Skia/PDF m143** |
| Santander_Internet_Banking_N1.pdf | `c0648182684ce8171f0a4b71ff18036084090efa412b22e0115a3c0ed89afd72` | 160.345 B | 2 | **Skia/PDF m145** |
| Santander_Internet_Banking_N3.pdf | `5b908f8416529f56f704b6654374175a0578be266f54867c06e7dc36dd221dcf` | 113.633 B | 4 | OpenPDF 1.3.30 |
| Santander_N1.pdf | `2e6d2aa1eea8da8fe3af9442024c07a1ef525f7171b57e805eab710cd1ae5419` | 218.182 B | 14 | Compart MFFPDF I/O Filter 2023-01-26 |
| Santander_N3.pdf | `2b5ee2dded038ccbc5a2914165dd4347271bc480a227c774fb72f8bf7b6304ae` | 236.629 B | 17 | Compart MFFPDF I/O Filter 2023-01-26 |

**Pendente:** `santander_problema.pdf` (KKS PROMOCOES) — não está no repo, foi reportado pelo Allan apenas via screenshot. Ver §7.

**Reprodução:** os PDFs vivem somente no working tree local do Allan em `backend/tests/fixtures/pdfs_reais/diag-2026-04-30/` (gitignored). Para reproduzir esta sessão em outra máquina, replicar os 9 PDFs com os SHAs acima.

---

## 4. Comportamento do pipeline em main por PDF

| Filename | banco_detectado | parser_class | n_tx | silent? | exception? | Status |
|---|---|---|---:|---|---|---|
| B2S.pdf | **`santander`** ❌ | ParserSantander | 46 | não | não | **MIS-ROUTE** (deveria ser `bs2`) |
| Bradesco_net.pdf | `bradesco` | ParserBradesco | 75 | não | não | OK |
| Bradesco_net2.pdf | `bradesco` | ParserBradesco | 73 | não | não | OK |
| Bradesco_Net_Empresas.PDF | `bradesco` ⚠️ | ParserBradesco | 20 | não | não | **MIS-ROUTE** (deveria ser `bradesco_net_empresas`) |
| Bradesco_Net_Empresas__2_.pdf | `bradesco_net_empresas` | ParserBradescoNetEmpresas | 13 | não | não | **DEGRADADO** — 6/13 tx com descrição trocada (ver §5) |
| Santander_Internet_Banking_N1.pdf | `santander` ⚠️ | ParserSantander | 6 | não | não | **MIS-ROUTE** (deveria ser `santander_ib_novo`); saldo final divergente |
| Santander_Internet_Banking_N3.pdf | `santander_ib_novo` | ParserSantanderIBNovo | 116 | não | não | OK (mas SI/SF=None) |
| Santander_N1.pdf | **`mercado_pago`** ❌ | ParserMercadoPago | 0 | **SIM** | não | **MIS-ROUTE silent** (deveria ser `santander_consolidado`) |
| Santander_N3.pdf | `santander_consolidado` | ParserSantanderConsolidado | 193 | não | não | OK (saldo conferido) |

**Síntese estatística:**
- **9 PDFs testados localmente**
- **3 falhas silentes ou parciais que retornam dados confiáveis ao usuário** (B2S → Santander, BradescoNetEmpresas SEOLIN → bradesco legado, Santander_IB_N1 → santander legado)
- **1 falha silenciosa total** (Santander_N1 → mercado_pago, 0 tx)
- **1 degradado pelo parser** (Bradesco CW TOUR, descrições trocadas)
- **3 OK** (Bradesco_net jan/dez, Santander_IB_N3, Santander_N3)
- **0 exceções `/Root dictionary` reproduzidas localmente**

---

## 5. Análise por PDF

### 5.1 B2S.pdf (PROMOVE BRASIL, jan/2025) — **MIS-ROUTE**

- **Detecção esperada:** `bs2`. **Detecção atual:** `santander`.
- **Causa raiz:** assinatura `['santander']` solta vem 24 linhas antes da assinatura BS2 em `_ASSINATURAS`. A string `santander` aparece 1× no texto via descrição de uma TED enviada para um cliente Santander (`bco santander sa - karla pinto varasquim`). BS2 tem 2 assinaturas válidas que dariam match (`'empresas.bs2'`, `'bs2.com.br'` via substring de `'bancobs2.com.br'`), mas nunca são avaliadas porque santander vence primeiro.
- **Análise completa:** [passo7-bs2-analise.md](passo7-bs2-analise.md)
- **Categoria:** Detecção (assinatura fraca + ordem)
- **Severidade:** **CRÍTICA** — parser Santander retornou 46 tx aparentemente coerentes (saldo final bate por sorte), o que esconde o problema do usuário.

### 5.2 Bradesco_net.pdf (TANIA LALLO, dez/2025)

- **Detecção:** `bradesco` (correto)
- **Tx:** 75. SI = 78.019,32. SF informado = 43.612,02. SF calculado = N/A (parser bradesco não tem `_extrair_saldos_intermediarios`).
- **Status:** OK
- Layout iText 2.0.8 — não dispara `/Root dictionary` em pikepdf 10.5.1 nem deve em 9.7.0.

### 5.3 Bradesco_net2.pdf (TANIA LALLO, nov/2025)

- **Detecção:** `bradesco` (correto)
- **Tx:** 73. SI = 96.735,73. SF informado = 78.019,32 (consistente com SI do mês seguinte).
- **Status:** OK

### 5.4 Bradesco_Net_Empresas.PDF (SEOLIN, jan/2025) — **MIS-ROUTE**

- **Detecção esperada:** `bradesco_net_empresas`. **Detecção atual:** `bradesco` (legado).
- **Causa raiz:** o tuple `bradesco_net_empresas` em `_ASSINATURAS` exige `['bradesco', 'total disponível (r$)']` (ou variantes encoding-safe). O texto do PDF não inclui literalmente "Total Disponível (R$)" como cabeçalho — usa um layout antigo do Net Empresas. O fallback `'total dispon'` também não bate. Cai no tuple seguinte: `('bradesco', [['bradesco'], ['dcto.'], ...])`, que é menos restritivo.
- **Tx extraídas pelo parser legado:** 20 (vs ~13 esperadas pela contagem visual do raw — pode ter falsos positivos).
- **Severidade:** **ALTA** — usuário recebe parser errado sem aviso. O parser legado pode não cobrir todas as tx do formato Net Empresas multi-linha.

### 5.5 Bradesco_Net_Empresas__2_.pdf (CW TOUR, jan/2026) — **DEGRADADO**

- **Detecção:** `bradesco_net_empresas` (correto)
- **Tx:** 13 (contagem correta)
- **Bug confirmado:** 6 das 13 transações têm descrição trocada (rótulo da tx N+1 vai parar no fim da tx N; tx N+1 perde o rótulo). Ver tabela completa em [passo6-bradesco-cwtour-analise.md](passo6-bradesco-cwtour-analise.md).
- **Causa raiz:** lookahead em [bradesco_net_empresas.py:177-186](backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py#L177-L186) e [:204-213](backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py#L204-L213) consome a próxima linha como continuação sem checar se a linha-depois-da-próxima começa com data (sinal de "isto pertence à próxima tx").
- **Sensibilidade a versão de lib:** MÉDIA (Skia/PDF m143).

### 5.6 Santander_Internet_Banking_N1.pdf (CW TOUR IB, fev/2026) — **MIS-ROUTE**

- **Detecção esperada:** `santander_ib_novo`. **Detecção atual:** `santander` (legado).
- **Causa raiz:** o tuple `santander_ib_novo` exige `['internet banking empresarial', 'saldo do dia r$']`. O texto deste PDF (CW TOUR IB) **não tem** "saldo do dia r$" — é uma versão do IB que não imprime saldos diários. Cai em `santander` legado, que retorna apenas 6 tx + saldo final divergente (R$ 271.580,33 vs SI=R$ 50,84 — quebra grande, indica que parser não cobre o formato).
- **Sensibilidade a versão de lib:** MÉDIA (Skia/PDF m145, mesmo motor que o KKS).
- **Severidade:** **ALTA** — esta é a família próxima do KKS (santander_problema). Mesmo se `/Root dictionary` for resolvido em prod, o pipeline continuará entregando dados incompletos.

### 5.7 Santander_Internet_Banking_N3.pdf (VILA PET, fev/2025)

- **Detecção:** `santander_ib_novo` (correto)
- **Tx:** 116. SI/SF None (parser não extrai saldos).
- **Status:** OK
- **Sensibilidade a versão de lib:** **ALTA** — proxy do santander_problema.pdf (KKS) que reproduziu `/Root dictionary` em prod. Local processou normalmente com pikepdf 10.5.1. Comparar com prod no Lightsail.

### 5.8 Santander_N1.pdf (LEKE Consolidado, jan/2025) — **FALHA SILENT TOTAL**

- **Detecção esperada:** `santander_consolidado`. **Detecção atual:** `mercado_pago`.
- **Causa raiz:** confirmar com Sessão 12 (este caso já estava listado em PENDENCIAS_SPRINT.md). A assinatura `mercado_pago` exige `['mercado pago', 'extrato de conta']` ou similar. Se o texto do Santander_N1 contém ambos como substrings (provável: descrição de uma TED para Mercado Pago + cabeçalho "Extrato de Conta"), a detecção colapsa.
- **Resultado:** 0 transações + aviso "Extrato com saldo zero — nenhuma transação encontrada".
- **Severidade:** **CRÍTICA** — usuário não recebe nada. Falha silenciosa total.

### 5.9 Santander_N3.pdf (LEKE Consolidado, mar/2025)

- **Detecção:** `santander_consolidado` (correto)
- **Tx:** 193. SI = SF = R$ 78.206,39 (mês com fluxo equilibrado).
- **Status:** OK

---

## 6. Mapeamento problema → categoria

| PDF | Sintoma | Categoria | Ação proposta (sessão futura) |
|---|---|---|---|
| `santander_problema.pdf` (KKS, prod) | `/Root dictionary` Exception | **Infra (versão de lib)** | Atualizar `pikepdf==9.7.0` → `==10.5.1` no `requirements.txt` + rebuild Docker. Validar no Lightsail. |
| `Santander_Internet_Banking_N3.pdf` (proxy KKS) | (local) processa OK; (prod) provavelmente `/Root dictionary` | **Infra** | Mesmo fix acima. |
| `B2S.pdf` | mis-routed para `santander` | **Detecção (assinatura fraca + ordem)** | Mover tuple `bs2` para antes de `santander` em `_ASSINATURAS`, ou refinar `'santander'` solto |
| `Santander_N1.pdf` | mis-routed para `mercado_pago`, 0 tx | **Detecção (assinatura colide)** | Refinar assinatura `mercado_pago` ou subir `santander_consolidado` na ordem (já listado em PENDENCIAS_SPRINT.md) |
| `Santander_Internet_Banking_N1.pdf` | mis-routed para `santander` legado | **Detecção (assinatura `santander_ib_novo` exige termo opcional `saldo do dia r$`)** | Adicionar fallback de assinatura `santander_ib_novo` que não exija "saldo do dia" |
| `Bradesco_Net_Empresas.PDF` (SEOLIN) | mis-routed para `bradesco` legado | **Detecção (assinatura `bradesco_net_empresas` exige cabeçalho específico)** | Adicionar fallback de assinatura `bradesco_net_empresas` baseado no título "Extrato Consolidado / Por Período" + colunas Crédito/Débito/Saldo |
| `Bradesco_Net_Empresas__2_.pdf` (CW TOUR) | descrições trocadas em 6/13 tx | **Parser (lookahead frágil)** | Estender lookahead em `bradesco_net_empresas.py` para checar 2 linhas à frente antes de engolir continuação |

---

## 7. Pendência: santander_problema.pdf (KKS PROMOCOES)

Este PDF foi reportado pelo Allan via screenshot mostrando `/Root dictionary` em produção, mas **não está no repositório** — não foi colocado na pasta `diag-2026-04-30/` nesta sessão.

**Contexto inferido:**
- Layout idêntico ao `Santander_Internet_Banking_N3.pdf` (VILA PET) — formato "Data | Histórico | Valor" do Santander Internet Banking
- Producer provavelmente Skia/PDF (mesma família que `Santander_Internet_Banking_N1.pdf` CW TOUR IB)

**Status do diagnóstico nesta sessão:**
- O `Santander_Internet_Banking_N3.pdf` testado nesta sessão **serve como proxy** para entender o formato. Localmente extrai 116 tx sem erro com pikepdf 10.5.1. Em produção, espera-se reproduzir `/Root dictionary` se a hipótese da versão pikepdf for correta.
- A validação específica do PDF do KKS exigirá adicionar o PDF ao repo (em `diag-2026-04-30/`, mantendo gitignored) numa sessão futura.

**Não bloqueia decisões sobre:**
- Fix de pikepdf (infra) — pode ser feito agora baseado nos 3 fixtures Skia/PDF + Compart já presentes
- Fix do parser do formato IB layout 2 — pode ser feito com Santander_IB_N1/N3 como fixtures

---

## 8. Sugestão de ordem para próximas sessões

1. **Sessão 13.5 (READ-ONLY):** rodar comandos de [comandos-allan-lightsail.md](comandos-allan-lightsail.md) no servidor; preencher [versoes-producao.txt](versoes-producao.txt) e [stack-trace-root-dictionary.txt](stack-trace-root-dictionary.txt); atualizar §1 e §2 deste relatório com os achados; **só depois** decidir o fix de infra.

2. **Sessão 14 (FIX INFRA):** se confirmado que `/Root dictionary` é causado por pikepdf 9.7.0, atualizar `requirements.txt` para `pikepdf==10.5.1` (ou versão equivalente compatível com Python 3.12), rebuild Docker, validar em prod com PDF KKS. Cuidado com regressão em outros PDFs.

3. **Sessão 15 (FIX DETECÇÃO):** corrigir os 4 mis-routes em `_ASSINATURAS` (BS2, Santander_N1 → mercado_pago, Santander_IB_N1 → legacy, Bradesco_Net_Empresas SEOLIN → legacy). Sprint cirúrgica, mover tuples + adicionar fallbacks. Validar contra os 9 fixtures + suite atual.

4. **Sessão 16 (FIX PARSER):** Bradesco CW TOUR — bug do lookahead. Validar contra fixture CW TOUR + os 15 testes determinísticos da Sessão 10 Turno 1.

5. **Sessão 17 (PROXY KKS):** adicionar `santander_problema.pdf` ao working tree do Allan, rodar pipeline, confirmar que após fixes de Sessão 14+15 o PDF é processado corretamente.

---

## 9. Comparação Local vs Produção — PENDENTE

Outputs do Lightsail não foram fornecidos antes do fim desta sessão.
Comandos a serem executados: ver [comandos-allan-lightsail.md](comandos-allan-lightsail.md).

Quando os outputs forem coletados, salvar em:
- `docs/diagnostico-parsers/sessao13/versoes-producao.txt`
- `docs/diagnostico-parsers/sessao13/stack-trace-root-dictionary.txt`

E reabrir esta sessão (ou abrir Sessão 13.5) para incorporar achados antes de prosseguir para qualquer fix.

---

## 10. Artefatos desta sessão

| Arquivo | Conteúdo |
|---|---|
| [RELATORIO.md](RELATORIO.md) | Este documento |
| [versoes-locais.txt](versoes-locais.txt) | Versões de Python e libs no venv local + comparação com requirements.txt |
| [comandos-allan-lightsail.md](comandos-allan-lightsail.md) | Comandos SSH a executar em produção |
| `versoes-producao.txt` | (pendente — preencher do Lightsail) |
| `stack-trace-root-dictionary.txt` | (pendente — preencher do Lightsail) |
| [passo4-catalogo.json](passo4-catalogo.json) | Catálogo metadados de cada PDF (pikepdf, pdfplumber, assinaturas, SHA) |
| [passo5-pipeline.json](passo5-pipeline.json) | Resultado do pipeline `processar_extrato()` em cada PDF |
| [passo6-bradesco-cwtour-analise.md](passo6-bradesco-cwtour-analise.md) | Análise detalhada do bug de descrições trocadas no CW TOUR |
| [passo7-bs2-analise.md](passo7-bs2-analise.md) | Análise da detecção BS2 → Santander |
| [raw-texts/](raw-texts/) | 9 arquivos `.txt` com texto cru de cada PDF (header + SHA + páginas) |
