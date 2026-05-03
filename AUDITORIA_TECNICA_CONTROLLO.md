# AUDITORIA TÉCNICA — CONTROLLO BPO ANALYTICS v2.0

Última atualização: 02/05/2026
Versão: 2.0 (substitui v1.0 da S23)
Branch ativa: refactor/arquitetura-estrutural

## 1. Visão geral do sistema

Controllo BPO Analytics é um SaaS multi-tenant FastAPI + Next.js 16 para escritórios de BPO contábil. Recebe upload de extratos bancários PDF, processa via pipeline de extração com OCR fallback, valida saldos via mecanismo de checks da Sessão 18, e gera arquivos Excel formatados conforme padrão Contmatic para conciliação contábil.

**Estado de uso:** sistema interno, monousuário. Único cliente é o próprio dono do escritório (Allan). Não há SaaS terceirizado, SLA público, ou clientes pagantes externos. Esse status define apetite a risco da refatoração.

**Stack técnica backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL em produção / SQLite em dev, pdfplumber para extração estruturada, pikepdf 10.5.1 para sanitização, pytesseract + Tesseract OCR como fallback de PDFs vetoriais, openpyxl para Excel.

**Stack frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4. Frontend não está no escopo da refatoração estrutural atual.

**Infraestrutura:** AWS Lightsail single-instance `54.196.112.39`. Docker Compose orquestra serviços. Caddy como reverse proxy. Deploy manual via SSH executando `atualizar.sh` na instância.

**Dimensões atuais (pós-S27.5):**
- Backend: ~18.811 linhas em ~129 arquivos `.py`
- Frontend: ~28.000 linhas em arquivos `.tsx/.ts/.css`
- Total: ~46.800 linhas
- Redução acumulada na refatoração: -2.776 linhas (-13% do backend)

## 2. Arquitetura atual

### 2.1 Topologia de dependências (validada na S25)

**Imports circulares:** zero, verificado em ambos os recortes (produção e completo). Considerado saudável para refatoração.

**Pontos cegos:** zero. Os 2 imports dinâmicos do projeto (`__import__("sqlalchemy")` em `main.py:892` e `import importlib` em `test_lp_dispatch.py:92`) são para libs externas/sem efeito. O grafo estático de imports cobre 100% do código interno.

**Top 5 in-degree (mais importados, candidatos a "intocáveis"):**
1. `services/parsers/base.py` (28) — herdada por quase todo parser
2. `services/contabil/core.py` (18)
3. `data/database/models.py` (18)
4. `data/database/__init__.py` (17)
5. `data/database/config.py` (16)

**Top 5 out-degree (que mais importam, candidatos a decomposição):**
1. `services/extrator_pdf.py` (30) — monolito alvo da S30
2. `main.py` (28) — monolito alvo da S32
3. `services/conciliacao/matchers/__init__.py` (13)
4. `routers/conciliacao.py` (6)
5. `routers/financeiro.py` (6)

### 2.2 Pipeline de extração

**Endpoint principal:** `POST /api/processar-extrato`

Fluxo atual (a ser unificado na S31):

```
Upload PDF
    ↓
detectar_banco() em extrator_pdf.py
    ↓
[2 orquestradores em paralelo — débito da S31]
    ↓
extrator_pdf.processar_extrato() (LEGADO, com backfill)
    + pipeline_extracao.processar_com_pipeline() (NOVO, sem backfill)
    ↓
ParserBancoX.extrair() (subclasse de ParserBase)
    ↓
validador_saldos.validar() (Sessão 18, 4 checks)
    ↓
gerador_excel_contabil.gerar() (formato Contmatic)
    ↓
Response JSON com: transacoes, saldos, validacao, excel_url
```

**Bug arquitetural conhecido:** quando pipeline novo recebe SI=None, valida `gap = float('inf')`, FastAPI tenta serializar JSON e quebra com `ValueError: Out of range float values are not JSON compliant: inf`. Endpoint retorna HTTP 500. Afeta Stone, alguns Santander Empresas, possivelmente Inter Layout 2. Resolução prevista na S31 ao unificar orquestradores.

## 3. Bancos suportados e cobertura de validação

### 3.1 Bancos VERDE (validados S18-S20)

- **Bradesco PF + Net Empresas** — 9/9 PDFs VERDE (S18). Crítico de uso diário.
- **Itaú PF + Empresas + N2** — 9/9 PDFs VERDE (S20). Crítico de uso diário.
- **Santander PF + variantes IB Novo, App Empresas, legacy** — 7 VERDE real + 5 VERMELHO honesto (S19).
- **Nubank PF** — VERDE.

### 3.2 Bancos VERMELHO (não-bloqueantes para uso interno)

- **Stone** — parser implementado na S24, afetado pelo bug `inf` em produção. Funciona em pytest mas crasha via endpoint.
- **Inter Layout 2** — multi-coluna com OCR, não-resolvido. `extrato_ABRIL.pdf` retorna 422 mesmo com Tesseract OK.
- **BB, BTG, PagBank** — parcial ou VERMELHO honesto. PagBank tem 2 errors pré-existentes em pytest desde commit `d7f4689`.
- **C6 Bank, Cora, Sicredi** — implementados, cobertura parcial.
- **Itaú Mensal SEM_SALDO** — 3 PDFs VERMELHO honesto.

### 3.3 Política de "honesto > VERDE"

Validador da Sessão 18 não inventa SI/SF se PDF não tem. Classifica VERMELHO com mensagem honesta em vez de retornar zero ou interpolar. Filosofia herdada após o caso CW TOUR (matemática batia mas semanticamente fake).

## 4. Refatoração estrutural em curso

### 4.1 Histórico de sessões

| Sessão | Descrição | Commit | Status |
|---|---|---|---|
| S14 | Bradesco saldoanterior log422 | (último em prod 30/04) | Deployada |
| S15 | pikepdf 9.7.0→10.5.1 | — | Acumulada |
| S16 | Bradesco Net Empresas saldo negativo | — | Acumulada |
| S17 | Mis-routes detector banco endurecido | — | Acumulada |
| S18 | Validador saldos 4 checks + filosofia VERDE/VERMELHO | — | Acumulada |
| S19 | Santander 100% honesto (4 iterações) | — | Acumulada |
| S20 | Inter OCR Tesseract fallback | 02a753c | Acumulada |
| S21 | Remove hardcodes cliente | 472d3f0 | Acumulada |
| S22 | Excel reformat spec Contmatic | 7f960da | Acumulada |
| S23 | Auditoria 96 PDFs read-only | 79331d4 | Acumulada |
| S24 | Stone parser + descoberta bug `inf` | 528c5cb | Acumulada |
| S25 | Inventário arquitetural read-only | 6dd8e00 | Acumulada |
| S26 | Limpeza dead code (-2.751 linhas) | 87f6120 | Acumulada |
| S27 | Extrair _RE_ANO | 0da8679 | Acumulada |
| S27.5 | ParserEmpresaBase para 3 parsers | 92d84f7 | Acumulada |

**Acumulado não-deployado:** 9 sessões. Deploy só após S35.5 (refator concluído).

### 4.2 Plano mestre de refatoração (13 sessões)

| # | Sessão | Foco | Linhas | Risco |
|---|---|---|---|---|
| 1 | S26 | Dead code Grupo A + sub-A + tests_fase2 | -2.751 (real) | baixo ✅ |
| 2 | S27 | _RE_ANO em parsers/base.py (7 parsers) | -11 (real) | médio ✅ |
| 3 | S27.5 | parsers/_empresa_base.py (3 parsers) | -14 (real) | médio-alto ✅ |
| 4 | S28 | Reorganizar parsers/ por banco em subpastas | 0 (mecânico) | alto |
| 5 | S29 | TOLERANCIA_VALOR em conciliacao/matchers/base.py | -25 estimado | baixo |
| 6 | S30 | Decompor extrator_pdf.py (1.747 linhas) | 0 (split) | alto |
| 7 | S31 | Unificar 2 orquestradores (resolve bug `inf`) | -100 estimado | alto |
| 8 | S32 | Decompor main.py (3.010 linhas) → app/ + api/v1/ | -200 estimado | altíssimo |
| 9 | S33 | Float → Decimal nos modelos | -30 estimado | médio |
| 10 | S34 | Reorganizar services/exportacao/ + tributario/ | -40 estimado | baixo-médio |
| 11 | S35 | Categorizar tests/ em unit/integration/e2e | 0 | baixo |
| 12 | S35.5 | Decisão produto: REMOVER ou ATIVAR contabil/* WIP | -1.015 (A) ou +185 (B) | depende |

**Progresso atual:** 4 de 12 sessões concluídas (~33%).

**Redução real até agora:** -2.776 linhas (S26 + S27 + S27.5).
**Redução estimada total cenário conservador (S26-S35):** -3.171 linhas (-15% backend).
**Redução estimada total cenário S35.5-A (remove WIP):** -4.186 linhas (-19% backend).

### 4.3 Estrutura alvo após S35.5

```
backend/
├── app/                    # FastAPI bootstrap (ex-main.py, S32)
├── api/v1/                 # endpoints HTTP (ex-routers + ex-main.py)
├── domain/
│   ├── models/             # SQLAlchemy ORM (ex-data/database/models.py)
│   ├── schemas/            # Pydantic
│   ├── enums.py
│   └── converters.py       # _to_dec, _to_float
├── services/
│   ├── extracao/           # decomposição de extrator_pdf.py (S30)
│   ├── parsers/            # reorganizado por banco (S28)
│   │   ├── base.py
│   │   ├── _empresa_base.py
│   │   ├── bradesco/
│   │   ├── itau/
│   │   ├── santander/
│   │   └── ... (1 pasta por banco)
│   ├── validacao/
│   ├── exportacao/
│   ├── pipeline/
│   ├── auditoria/
│   ├── conciliacao/matchers/  # TOLERANCIA_VALOR (S29)
│   ├── tributario/
│   └── contabil/           # mantido OU removido pós-S35.5
├── infrastructure/
├── scripts/
├── tests/{unit,integration,e2e}/
└── migrations/
```

## 5. Débitos técnicos

### 5.1 Críticos (afetam produção)

1. **Bug `inf` no validador Sessão 18.** Endpoint HTTP 500 quando SI=None. Stone afetado em uso real. Resolução indireta na S31.

2. **2 orquestradores de pipeline em paralelo.** Endpoint chama ambos. Fonte do bug `inf` indiretamente. Resolução direta na S31.

3. **`extrato_ABRIL.pdf` localhost retorna 422.** Postergado, não-investigado. Provavelmente parser Inter Layout 2.

### 5.2 Estruturais (afetam manutenção)

4. **`extrator_pdf.py` monolito 1.747 linhas.** Alvo da S30.

5. **`main.py` monolito 3.010 linhas.** Alvo da S32.

6. **`models.py` 633 linhas com Float em campos financeiros.** Alvo da S33.

7. **5 arquivos WIP em `services/contabil/`.** ~989 linhas. Decisão de produto na S35.5.

### 5.3 Auditoria

8. **`audit_duplicado.py` da S25 Fase 4 superestima clusters.** Confirmado na S27.5. Outros achados (S29 TOLERANCIA_VALOR, S33 `_to_dec`/`_to_float`) **exigem PRE-CHECK de validação concreta** antes de extrair.

9. **Conflitos de nomes entre helpers de módulo e métodos `ParserBase`.** Caso btg `_normalizar_valor` vs `ParserBase._normalizar_valor`. Auditoria dedicada na S35.

10. **btg.py e n2/itau_n2.py sem testes pytest dedicados.** Validação indireta via parser geral.

### 5.4 Hardcodes residuais

11. **Antipattern de nomes de cliente em parsers** (descoberto S21). Auditoria na S35 para confirmar zero residuais.

## 6. Política de deploy

- **Última deploy em produção:** S14, 30/04/2026 ~12h
- **Cadeia acumulada:** 9 sessões (S20 a S27.5)
- **Próximo deploy planejado:** após S35.5
- **Política:** zero deploy intermediário durante refatoração estrutural. Big-bang após validação completa pós-S35.5.
- **Justificativa:** sistema interno, refator preserva comportamento, deploy intermediário tem risco maior que benefício.

## 7. Pytest baseline

| Sessão | Pytest | Notas |
|---|---|---|
| S22 final | 879 passed | Documentado |
| S24 final | 912 passed | Documentado |
| S25 baseline | 912 passed / 1 failed (zxcvbn) / 1 skipped / 2 errors | Zxcvbn flaky, 2 errors pagbank pré-existentes desde d7f4689 |
| S26 final | 881 passed | -31 testes esperados (25 comparador + 6 categorias) |
| S27 final | 881 passed | Preservado |
| S27.5 final | 881 passed | Preservado |

**Régua atual:** 881 passed deve permanecer. Falha nova (não-zxcvbn) é regressão até prova em contrário.

## 8. Filosofia operacional

### 8.1 Princípios permanentes

1. **Honestidade > VERDE.** Validador prefere VERMELHO honesto a VERDE inventado.
2. **Política gitignore rígida.** Zero PDFs binários commitados. Fixtures sempre `.txt` raw via pdfplumber.
3. **Mudança em código compartilhado exige R-B.** Regression-bench em todos os bancos VERDE críticos.
4. **Auditoria evolutiva.** Este documento mantém histórico vivo.
5. **Deploy manual via SSH.** Sem CI/CD automatizado.
6. **Validação empírica > análise estática.** Auditoria estática pode errar (provado S25 Fase 4). PRE-CHECK obrigatório antes de extrair clusters reportados.

### 8.2 Protocolo R1-R6

Toda sessão de modificação segue estrutura cirúrgica:
- R1 lista de arquivos permitidos
- R2 lista exaustiva de proibidos
- R3 estado inicial validado antes
- R4 condições de disparo de decisão arquitetural
- R5 fases discretas com paradas obrigatórias
- R6 limites de escopo e tempo

### 8.3 Divisão de papéis (operação tripartite)

- **Arquiteto sênior (Claude web):** prompts R1-R6, validação de relatórios, decisões arquiteturais.
- **Allan (dev iniciante, dono):** cola prompts, aprova decisões A/B, validação visual, executa deploys SSH.
- **Claude Code (CLI local Windows):** executa, modifica, testa, comita. Nunca faz deploy.

## 9. Pontos abertos

- **S28** próxima sessão. Reorganizar parsers/ em subpastas por banco. Risco alto, ~60-90 min.
- **Bug localhost OCR** sem investigação dedicada.
- **Decisão produto S35.5** pendente.
