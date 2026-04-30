# AUDITORIA TECNICA COMPLETA — CONTROLLO SaaS BPO Analytics

**Data:** 2026-04-06 (criacao) | 2026-04-06 (ultima atualizacao)
**Versao:** 2.0
**Escopo:** Todos os arquivos do repositorio backend + frontend
**Nota:** Esta versao inclui TODAS as correcoes e implementacoes realizadas nas sessoes de trabalho.

---

## INDICE

1. [Visao Geral da Aplicacao](#1-visao-geral-da-aplicacao)
2. [Estrutura do Projeto](#2-estrutura-do-projeto)
3. [Modelos de Dados](#3-modelos-de-dados)
4. [Endpoints da API — Inventario Completo](#4-endpoints-da-api)
5. [Autenticacao, Autorizacao e Seguranca](#5-autenticacao-autorizacao-e-seguranca)
6. [Multi-Tenancy (Isolamento por Escritorio)](#6-multi-tenancy)
7. [Parsers de Extratos Bancarios](#7-parsers-de-extratos-bancarios)
8. [Logica Financeira — Formulas e Calculos](#8-logica-financeira)
9. [Simulacao Tributaria](#9-simulacao-tributaria)
10. [Conciliacao Bancaria](#10-conciliacao-bancaria)
11. [Importacao de Dados](#11-importacao-de-dados)
12. [Classificacao Contabil](#12-classificacao-contabil)
13. [Orcamento vs Realizado](#13-orcamento-vs-realizado)
14. [Alertas e Email](#14-alertas-e-email)
15. [Equipe e Tarefas](#15-equipe-e-tarefas)
16. [Auditoria](#16-auditoria)
17. [Frontend — Detalhamento Completo](#17-frontend)
18. [Infraestrutura e Deploy](#18-infraestrutura-e-deploy)
19. [Fluxos de Negocio Passo a Passo](#19-fluxos-de-negocio)
20. [Testes](#20-testes)
21. [Pontos Criticos e Debitos Tecnicos](#21-debitos-tecnicos)
22. [Metricas do Projeto](#22-metricas)
23. [Pontos de Extensao](#23-pontos-de-extensao)
24. [Resumo Executivo](#24-resumo-executivo)
25. [Historico de Alteracoes](#25-historico-de-alteracoes)

---

# 1. VISAO GERAL DA APLICACAO

## 1.1 O que e o Controllo

O **Controllo BPO Analytics** e uma plataforma SaaS multi-tenant para escritorios de contabilidade (BPOs). Resolve o problema de analise financeira automatizada de clientes PME: extrai dados de extratos bancarios em PDF, processa lancamentos financeiros, gera DRE, Balanco Patrimonial, Fluxo de Caixa, simulacao tributaria, insights automaticos, conciliacao bancaria, classificacao contabil e **Excel contabil com partida dobrada**.

**Publico-alvo:** Escritorios de contabilidade com 10 a 1500+ clientes (empresas). Cada escritorio e um tenant isolado.

## 1.2 Stack Tecnologica

### Backend
| Tecnologia | Versao | Proposito |
|-----------|--------|-----------|
| Python | 3.11/3.12 | Linguagem principal |
| FastAPI | 0.135.1 | Framework web/API |
| Uvicorn | 0.42.0 | Servidor ASGI |
| SQLAlchemy | 2.0.48 | ORM e acesso ao banco |
| SQLite | (embutido) | Banco dev/fallback |
| PostgreSQL (psycopg2-binary) | 2.9.10 | Banco producao |
| python-jose[cryptography] | 3.5.0 | JWT tokens |
| passlib | 1.7.4 | Hash de senhas (pbkdf2_sha256) |
| pdfplumber | 0.11.9 | Extracao de texto de PDF |
| pikepdf | 9.7.0 | PDFs protegidos por senha |
| pdfminer.six | 20251230 | Suporte PDF complementar |
| PyMuPDF (fitz) | 1.27.2 | Renderizacao PDF para OCR |
| openpyxl | 3.1.5 | Leitura/escrita Excel |
| boto3 | 1.38.0 | AWS S3 storage |
| redis | 5.2.1 | Rate limiting (opcional) |
| Pydantic | 2.12.5 | Validacao de dados |

### Frontend
| Tecnologia | Versao | Proposito |
|-----------|--------|-----------|
| Next.js | 16.1.6 | Framework React SSR |
| React | 19.2.3 | UI library |
| TypeScript | ^5 | Tipagem estatica |
| Tailwind CSS | ^4.2.2 | Styling (CSS-first config) |
| Recharts | ^3.8.0 | Graficos |
| Lucide React | ^0.577.0 | Icones |
| xlsx | ^0.18.5 | Leitura/escrita Excel client-side |
| html-to-image | ^1.11.13 | Exportacao PNG de dashboards |

### Dependencias nao utilizadas
| Pacote | Motivo |
|--------|--------|
| bcrypt 5.0.0 + passlib[bcrypt] | Hash usa pbkdf2_sha256, nao bcrypt |
| @prisma/client + prisma | Nunca usado no frontend (legado) |

## 1.3 Arquitetura Geral

- **Tipo:** Monolito (backend unico com routers modulares) + SPA (Next.js)
- **Comunicacao:** REST API via HTTP/JSON
- **Backend:** FastAPI single-process (uvicorn --workers 1)
- **Frontend:** Next.js com Client Components ("use client" em todas as paginas)
- **Banco:** SQLite (dev) ou PostgreSQL (prod) via SQLAlchemy
- **Storage:** Local filesystem (dev) ou AWS S3 (prod)

## 1.4 Padroes Arquiteturais

- **Router pattern:** Endpoints organizados em 12 routers FastAPI + main.py
- **Service layer:** Services em `backend/services/` (financeiro_service, importacao_service, etc.)
- **Strategy pattern:** Parsers bancarios com base abstrata + implementacoes por banco
- **Factory pattern:** Storage (LocalStorage vs S3Storage baseado em env var)
- **Template Method:** `_extrair_saldos_intermediarios()` em ParserBase com overrides por banco
- **Sem Repository pattern:** Queries SQL diretas nos endpoints/services via SQLAlchemy Session
- **Sem ORM relationships:** Todas as 22 models nao definem `relationship()`, apenas ForeignKey

## 1.5 Mapa de Dependencias Externas

| Lib | Proposito | Obrigatoria |
|-----|-----------|-------------|
| pdfplumber | Extracao texto/tabela PDF | Sim |
| pikepdf | Unlock PDFs com senha | Sim |
| openpyxl | Excel r/w | Sim |
| boto3 | S3 upload/download | Nao (fallback local) |
| redis | Rate limiting distribuido | Nao (fallback in-memory) |
| python-jose | JWT encode/decode | Sim |
| passlib | Password hashing | Sim |
| psycopg2-binary | PostgreSQL driver | Nao (fallback SQLite) |
| easyocr | OCR para Sicredi escaneado | Nao (import condicional) |

---

# 2. ESTRUTURA DO PROJETO

## 2.1 Arvore de Diretorios

```
SAAS CONTROLLO/
├── .env                              # DATABASE_URL (legado, nao usado pelo backend)
├── .env.production.example           # Template producao (nomes inconsistentes)
├── AUDITORIA_TECNICA_CONTROLLO.md    # Este documento
├── backend/
│   ├── .env.example                  # Template env backend (48 linhas)
│   ├── Dockerfile                    # Dev: python:3.11-slim, porta 8000
│   ├── Dockerfile.prod               # Prod: python:3.12-slim, 1 worker
│   ├── requirements.txt              # 25 dependencias + 4 comentadas (OCR)
│   ├── main.py                       # 2805 linhas — app principal + 37 endpoints + Excel contabil
│   ├── criar_mestre.py               # 4 linhas — DEAD CODE (endpoint nao existe)
│   ├── test_parsers.py               # 164 linhas — CLI manual, NAO testes automatizados
│   ├── core/
│   │   └── config.py                 # 0 linhas — VAZIO (placeholder)
│   ├── data/
│   │   └── database/
│   │       ├── __init__.py           # 0 linhas
│   │       ├── config.py             # 40 linhas — engine SQLite/PostgreSQL, get_db
│   │       └── models.py             # 538 linhas — 22 modelos SQLAlchemy
│   ├── routers/
│   │   ├── __init__.py               # 0 linhas
│   │   ├── master.py                 # 524 linhas — 15 endpoints (super-admin) + resumo + tenant isolation
│   │   ├── financeiro.py             # 628 linhas — 17 endpoints
│   │   ├── classificacao.py          # 757 linhas — 17 endpoints
│   │   ├── empresas.py               # 637 linhas — 10 endpoints
│   │   ├── conciliacao.py            # 398 linhas — 7 endpoints
│   │   ├── relatorios.py             # 387 linhas — 1 endpoint
│   │   ├── orcamento.py              # 325 linhas — 5 endpoints
│   │   ├── alertas.py                # 313 linhas — 6 endpoints
│   │   ├── importacao.py             # 308 linhas — 9 endpoints
│   │   ├── equipe.py                 # 297 linhas — 7 endpoints
│   │   ├── auditoria.py              # 144 linhas — 2 endpoints + registrar_auditoria()
│   │   └── (total: ~4720 linhas, 96 endpoints)
│   └── services/
│       ├── __init__.py               # 0 linhas
│       ├── auth_utils.py             # 109 linhas — auth helpers + tenant isolation
│       ├── extrator_pdf.py           # 1217 linhas — orquestrador PDF + verificacao saldos + deteccao
│       ├── financeiro_service.py     # 575 linhas — DRE, balanco, fluxo, indicadores
│       ├── simulacao_tributaria_service.py  # 265 linhas
│       ├── importacao_service.py     # 730 linhas
│       ├── insights_engine.py        # 375 linhas — 16 regras de insight
│       ├── motor_classificacao.py    # 366 linhas — 4 niveis de classificacao
│       ├── motor_narrativa.py        # 415 linhas — narrativas financeiras
│       ├── score_saude.py            # 211 linhas — score 0-100
│       ├── categorias.py             # 399 linhas — 3 camadas de categorizacao
│       ├── categorizacao_extrato.py  # 301 linhas — categorizacao pos-extracao
│       ├── detectar_banco.py         # 49 linhas — deteccao legada (redundante)
│       ├── gerador_excel.py          # 233 linhas — Excel de transacoes (basico)
│       ├── gerador_excel_contabil.py # 283 linhas — **NOVO** Excel contabil partida dobrada
│       ├── leitor_excel.py           # 50 linhas — leitura Excel
│       ├── email_service.py          # 200 linhas — SMTP Gmail
│       ├── storage.py                # 129 linhas — Local + S3
│       ├── backup_service.py         # 96 linhas — backup DB
│       ├── cnpj_validator.py         # 29 linhas — mod-11
│       ├── template_dashboard.py     # 263 linhas — template sazonal
│       ├── parsers/                  # 31 parsers bancarios
│       │   ├── base.py               # 341 linhas — ParserBase (ABC) + _extrair_saldos_intermediarios
│       │   ├── parser_base.py        # 90 linhas — ParserBase LEGADO
│       │   ├── bb.py, bradesco.py, c6bank.py, caixa.py, cora.py,
│       │   │   inter.py, itau.py, mercado_pago.py, nubank.py,
│       │   │   pagbank.py, santander.py, sicredi.py, stone.py,
│       │   │   xp_extrato.py, xp_posicao.py, sumup.py, bs2.py,
│       │   │   itau_empresas.py, santander_empresarial.py,
│       │   │   santander_consolidado.py, parser_generico.py,
│       │   │   parser_itau_mensal.py, parser_stone.py, stone_n2.py
│       │   ├── bradesco_empresas/    # bradesco_net_empresas.py
│       │   ├── santander_empresas/   # v1.py, v2.py (alias)
│       │   └── n2/                   # inter_n2.py, itau_n2.py, itau_empresas_n2.py
│       ├── conciliacao/
│       │   ├── engine.py             # 66 linhas — orquestrador
│       │   ├── excel_reader.py       # 80 linhas
│       │   └── matchers/             # 13 matchers + base + universal
│       └── tributario/
│           ├── constantes.py         # 148 linhas — tabelas Simples I-V, Presumido, Real, Reforma
│           ├── simples_nacional.py   # 133 linhas
│           ├── lucro_presumido.py    # 131 linhas
│           ├── lucro_real.py         # 139 linhas
│           └── reforma.py            # 131 linhas
├── frontend/
│   ├── package.json                  # Next.js 16, React 19, Tailwind 4
│   ├── tsconfig.json                 # ES2017, strict
│   ├── next.config.ts                # Vazio (sem config custom)
│   ├── postcss.config.mjs            # @tailwindcss/postcss
│   ├── app/
│   │   ├── layout.tsx                # 49 linhas — Plus Jakarta Sans, theme flash prevention
│   │   ├── globals.css               # ~400 linhas — design system completo, CSS vars
│   │   ├── actions.ts                # 139 linhas — processarExtrato, downloadExcel
│   │   ├── ClientWrapper.tsx         # 843 linhas — sidebar, topbar, auth, empresa selector
│   │   ├── page.tsx                  # ~830 linhas — Leitor PDF (home)
│   │   ├── login/page.tsx            # 495 linhas — Login + solicitar acesso
│   │   ├── dashboard/page.tsx        # ~500 linhas — Dashboard financeiro
│   │   ├── dashboard-executivo/page.tsx # ~700 linhas — Dashboard editavel + export
│   │   ├── admin/page.tsx            # ~600 linhas — Gestao de usuarios (com tenant filter)
│   │   ├── admin/carteiras/page.tsx  # ~400 linhas — Carteira geral
│   │   ├── master/page.tsx           # 1028 linhas — Central de Controle + seletor escritorio
│   │   ├── agenda/page.tsx           # ~500 linhas — Lembretes
│   │   ├── carteiras/page.tsx        # ~400 linhas — Minha carteira
│   │   ├── gestor/equipe/page.tsx    # ~300 linhas — Gestao de equipe
│   │   └── (+ ~24 outras paginas financeiras, importacao, etc.)
│   ├── components/
│   │   ├── GlobeBackground.tsx       # Canvas animado
│   │   ├── useChartTheme.ts          # Hook tema graficos
│   │   ├── GraficoComNome.tsx        # Wrapper graficos
│   │   ├── UserAvatar.tsx            # Avatar
│   │   ├── EditableAvatar.tsx        # Avatar editavel
│   │   ├── DataImportPanel.tsx       # Painel importacao
│   │   └── ui/index.tsx              # 222 linhas — Card, Badge, Avatar, Input, etc.
│   └── contexts/
│       ├── EmpresaContext.tsx         # 53 linhas — empresa selecionada
│       └── ToastContext.tsx           # 229 linhas — notificacoes toast
```

## 2.3 Mapa de Dependencias entre Modulos

```
main.py
  ├── imports 12 routers (financeiro, importacao, conciliacao, orcamento, relatorios,
  │   alertas, auditoria, empresas, equipe, classificacao, master)
  ├── imports services: extrator_pdf, gerador_excel, gerador_excel_contabil,
  │   leitor_excel, categorizacao_extrato, storage, cnpj_validator, backup_service
  └── imports data.database: config (get_db, engine), models

routers/*
  ├── import services.auth_utils (get_current_user, get_admin_user, query_tenant)
  ├── import data.database.models
  └── import specific services

services/extrator_pdf.py
  ├── imports ALL 27 parsers from services.parsers.*
  └── imports services.categorizacao_extrato

services/gerador_excel_contabil.py  (NOVO)
  └── imports services.motor_classificacao (classificar_lote)

services/financeiro_service.py
  ├── imports services.insights_engine
  └── imports services.motor_narrativa
```

---

# 3. MODELOS DE DADOS

## 3.1 Inventario Completo (22 modelos)

*(Sem alteracoes nos models — secao identica a v1.0)*

### Escritorio (tabela: `escritorios`)
| Campo | Tipo Python | Default | Nullable | Index | Unique | FK |
|-------|------------|---------|----------|-------|--------|-----|
| id | Integer | PK auto | N | S | S | - |
| nome | String | - | N | N | N | - |
| slug | String | - | N | S | S | - |
| plano | String | "trial" | S | N | N | - |
| max_empresas | Integer | 10 | S | N | N | - |
| max_usuarios | Integer | 2 | S | N | N | - |
| data_expiracao | String | None | S | N | N | - |
| ativo | Boolean | True | S | N | N | - |
| criado_em | String | - | N | N | N | - |
| atualizado_em | String | - | N | N | N | - |

### Usuario (tabela: `usuarios`)
| Campo | Tipo | Default | Nullable | Index | FK |
|-------|------|---------|----------|-------|-----|
| id | Integer | PK | N | S | - |
| escritorio_id | Integer | None | S | S | escritorios.id |
| nome | String | - | N | S | - |
| senha_hash | String | - | N | N | - |
| is_master | Boolean | False | S | N | - |
| is_dono | Boolean | False | S | N | - |
| is_admin | Boolean | False | S | N | - |
| is_ceo | Boolean | False | S | N | - |
| is_gestor | Boolean | False | S | N | - |
| is_aprovado | Boolean | False | S | N | - |
| nome_exibicao | String | "" | S | N | - |
| cargo | String | "" | S | N | - |

**Constraint:** UniqueConstraint("escritorio_id", "nome")

### Empresa, LancamentoMensal, e demais modelos

*(Sem alteracoes — 22 modelos total. Ver v1.0 para detalhes completos.)*

## 3.2 Relacionamentos

```
Escritorio (1) ──< (N) Usuario
Escritorio (1) ──< (N) Empresa
Empresa (1) ──── (1) EmpresaFiscal
Empresa (1) ──< (N) EmpresaBanco
Empresa (1) ──< (N) LancamentoMensal
Empresa (1) ──< (N) OrcamentoMensal
Empresa (1) ──< (N) TransacaoBancaria
Empresa (1) ──< (N) Importacao
Empresa (1) ──── (1) CarteiraMembro ───> (1) Usuario
Empresa (1) ──< (N) PlanoContasEmpresa
Empresa (1) ──< (N) RegraClassificacao
Usuario (1) ──< (N) Lembrete
Usuario (1) ──< (N) TarefaEquipe
```

## 3.3 Auto-Migracao

*(Sem alteracoes — ver v1.0)*

## 3.4 Seeds / Dados Iniciais

*(Sem alteracoes — ver v1.0)*

---

# 4. ENDPOINTS DA API

## Totais: 140 endpoints (44 em main.py + 96 em routers)

## 4.1 Agrupados por Modulo

### Raiz e Health (main.py, sem auth)
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Status "online" |
| GET | `/api/health` | SELECT 1 + timestamp |

### Auth (main.py, publicos + auth)
| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | `/api/auth/verificar-escritorio` | Nao | Verifica se slug existe |
| POST | `/api/auth/solicitar-acesso` | Nao (rate limited) | Registro de usuario |
| POST | `/api/auth/login` | Nao (rate limited) | Login, retorna JWT |
| GET | `/api/auth/me` | User | Perfil atual |
| PATCH | `/api/auth/perfil` | User | Atualizar nome_exibicao/cargo |
| PATCH | `/api/auth/senha` | User | Alterar senha |

### Admin Usuarios (main.py, admin required)
| Metodo | Rota | Descricao | Tenant |
|--------|------|-----------|--------|
| GET | `/api/admin/usuarios` | Listar usuarios | **SIM** (CORRIGIDO — filtra por escritorio_id para nao-master) |
| PATCH | `/api/admin/usuarios/{id}/aprovar` | Aprovar/bloquear | **NAO** (pendente) |
| PATCH | `/api/admin/usuarios/{id}/promover` | Admin toggle | **NAO** (pendente) |
| PATCH | `/api/admin/usuarios/{id}/gestor` | Gestor toggle | **NAO** (pendente) |
| PATCH | `/api/admin/usuarios/{id}/ceo` | CEO toggle | **NAO** (pendente) |
| DELETE | `/api/admin/usuarios/{id}` | Excluir usuario | **NAO** (pendente) |
| POST | `/api/admin/backup` | Backup manual | N/A |

### Master / Central de Controle (routers/master.py, 15 endpoints)
Todos protegidos por `_get_master_admin` (is_master=True).

| Metodo | Rota | Funcao | Alteracao v2 |
|--------|------|--------|-------------|
| GET | `/api/master/escritorios` | Listar todos | - |
| POST | `/api/master/escritorios` | Criar escritorio | - |
| GET | `/api/master/escritorios/{id}` | Detalhar | - |
| GET | `/api/master/escritorios/{id}/resumo` | **Contagens** | **NOVO** — total usuarios/pendentes/ativos/empresas |
| PATCH | `/api/master/escritorios/{id}` | Atualizar | - |
| PATCH | `/api/master/escritorios/{id}/desativar` | Desativar | - |
| PATCH | `/api/master/escritorios/{id}/ativar` | Ativar | - |
| DELETE | `/api/master/escritorios/{id}` | Excluir | - |
| GET | `/api/master/escritorios/{id}/usuarios` | Usuarios do escritorio | - |
| GET | `/api/master/usuarios` | **Listar (REQUER escritorio_id)** | **CORRIGIDO** — 400 se nao fornecido |
| PATCH | `/api/master/usuarios/{id}/aprovar` | Aprovar | **CORRIGIDO** — valida escritorio_id |
| PATCH | `/api/master/usuarios/{id}/reprovar` | Reprovar | **CORRIGIDO** — valida escritorio_id |
| PATCH | `/api/master/usuarios/{id}/role` | Alterar roles | **CORRIGIDO** — valida escritorio_id |
| DELETE | `/api/master/usuarios/{id}` | Excluir | **CORRIGIDO** — valida escritorio_id |
| GET | `/api/master/metricas` | Metricas globais | - |

### PDF Extrato (main.py, user auth)
| Rota | Descricao | Alteracao v2 |
|------|-----------|-------------|
| POST `/api/processar-extrato` | Processar 1 PDF | **ATUALIZADO** — aceita empresa_id opcional, gera Excel contabil |
| POST `/api/processar-extrato-lote` | Processar N PDFs | - |
| POST `/api/detectar-bancos` | Detectar banco sem processar | - |
| POST `/api/processar-lote-confirmado` | Processar apos confirmacao | - |
| GET `/api/download/{excel_id}` | Download Excel gerado | - |

### Demais Routers

*(Sem alteracoes — financeiro 17, classificacao 17, empresas 10, conciliacao 7, importacao 9, equipe 7, alertas 6, orcamento 5, auditoria 2, relatorios 1)*

## 4.3 Middlewares

*(CORS, Rate Limiting, Security Headers — sem alteracoes. Ver v1.0)*

---

# 5. AUTENTICACAO, AUTORIZACAO E SEGURANCA

*(Sem alteracoes na estrutura de auth. JWT, roles, funcoes de autorizacao — ver v1.0)*

---

# 6. MULTI-TENANCY

## 6.1 Modelo

Cada **Escritorio** e um tenant. O campo `escritorio_id` existe em `Usuario` e `Empresa`. O JWT carrega `eid` (escritorio_id).

## 6.2 Isolamento no Backend

### Endpoints COM isolamento de tenant:
- GET `/api/admin/usuarios` — **CORRIGIDO v2** (filtra por escritorio_id para nao-master)
- GET `/api/master/usuarios` — **CORRIGIDO v2** (requer escritorio_id, retorna 400 sem ele)
- PATCH/DELETE `/api/master/usuarios/{id}/*` — **CORRIGIDO v2** (valida escritorio_id, retorna 403)
- GET `/api/empresas` (via escritorio_id filter)
- POST `/api/empresas` (seta escritorio_id)
- Todos endpoints de classificacao, conciliacao, orcamento, alertas (via _check_empresa)

### Endpoints AINDA SEM isolamento (PENDENTE):
- PATCH/DELETE `/api/admin/usuarios/{id}/*` (aprovar, promover, gestor, ceo, excluir)
- GET `/api/auditoria` (admin ve TODOS os logs)
- GET `/api/equipe/colaboradores` (lista TODOS usuarios cross-tenant)
- POST/PUT/DELETE `/api/empresas/{id}/bancos/*` (sem _check_empresa)
- PUT/DELETE `/api/empresas/{id}` (admin sem filtro escritorio_id)
- GET `/api/admin/carteiras` (admin sem filtro)
- POST `/api/carteira` (criar empresa sem escritorio_id)

## 6.3 Frontend — Seletor de Escritorio para Master (NOVO v2)

Na pagina `/master`, aba "Usuarios":
- **REMOVIDO:** listagem direta de todos os usuarios misturados
- **ADICIONADO:** seletor/dropdown de escritorio no topo
- **Sem selecao:** mensagem "Selecione um escritorio para gerenciar seus usuarios"
- **Com selecao:** card resumo (total/pendentes/ativos/empresas) + lista filtrada
- **Acoes:** aprovar/reprovar/role/delete enviam escritorio_id na query

---

# 7. PARSERS DE EXTRATOS BANCARIOS

## 7.1 Classe Base (parsers/base.py, 341 linhas)

| Metodo | Comportamento |
|--------|--------------|
| `__init__(pdf_path, password)` | Armazena path e senha |
| `extrair() -> list[dict]` | ABSTRATO — retorna transacoes |
| `_normalizar_valor(texto) -> Decimal` | Remove R$, converte BR format |
| `_normalizar_data(texto, ano_ref) -> str` | DD/MM/YYYY, DD/MM/YY, DD/MM |
| `_transacao(data,desc,valor,tipo,banco,raw) -> dict` | Monta dict padronizado |
| `_is_linha_saldo(desc) -> bool` | 8 regexes de saldo |
| `_extrair_saldos_intermediarios() -> list[dict]` | **NOVO v2** — retorna [] por padrao, override por banco |
| `_post_processar(transacoes) -> list` | 3 passes: filtra saldos, valida estrutura, valida data |
| `_segunda_verificacao_valor(raw,valor) -> Decimal` | Re-extrai valores do raw |
| `_verificar_tipo_cruzado(tipo_sinal,desc,...) -> str` | Sinal > Keywords > default=saida |

## 7.2 Todos os Parsers (31 total)

| Banco | Classe | Linhas | Saldo Inter. | Testado c/ PDF |
|-------|--------|--------|-------------|---------------|
| BB | ParserBB | 369 | **SIM (override v2)** | SIM (89 tx) |
| Bradesco | ParserBradesco | 305 | NAO | SIM (79 tx) |
| C6 Bank | ParserC6Bank | 114 | **SIM (override v2)** | SIM (23 tx) |
| Caixa | ParserCaixa | 177 | **SIM (override v2)** | SIM (12 tx, 6/6 OK) |
| Cora | ParserCora | 105 | **SIM (override v2)** | SIM (89 tx, 21/21 OK) |
| Inter | ParserInter | 172 | **SIM (override v2)** | SIM (7 tx) |
| Itau | ParserItau | 478 | NAO | SIM (65 tx) |
| Itau Empresas | ParserItauEmpresas | 428 | NAO | SIM (9 tx) |
| Mercado Pago | ParserMercadoPago | 164 | NAO | SIM (46 tx) |
| Nubank | ParserNubank | 569 | **SIM (override v2)** | SIM (167 tx, 23-28/dia OK) |
| PagBank | ParserPagBank | 103 | **SIM (override v2)** | SIM (26 tx) |
| Santander | ParserSantander | 143 | NAO | PDF ContaMax (0 tx) |
| Sicredi | ParserSicredi | 499 | NAO | SIM (18 tx) |
| Stone | ParserStone | 341 | NAO | SIM (604 tx) |
| XP Extrato | ParserXPExtrato | 151 | NAO | SIM (34 tx) |
| XP Posicao | ParserXPPosicao | 146 | NAO | SIM (40 pos) — **FIX password v2** |
| SumUp | ParserSumUp | 100 | NAO | SEM PDF |
| BS2 | ParserBS2 | 153 | NAO | SEM PDF |

**Parsers N2/Empresas/Legados:** *(sem alteracoes — ver v1.0)*

## 7.3 Verificacao Progressiva de Saldos (NOVO v2)

### Como funciona:
1. Parser extrai transacoes normalmente
2. `_extrair_saldos_intermediarios()` extrai "Saldo do dia" do PDF
3. Verificacao reconstroi saldo dia a dia: `saldo_calc = SI + sum(entradas) - sum(saidas)`
4. Compara com cada saldo intermediario encontrado
5. Testa modo "fechamento" (saldo apos tx do dia) E "abertura" (saldo antes tx), usa o melhor
6. Se SI=None: tenta usar primeiro saldo intermediario como ponto de partida

### Resultados testados com PDFs reais:

| Banco | SI | Saldos Inter. | Verificados/OK | Modo | Conferencia |
|-------|-----|-------------|---------------|------|------------|
| Nubank PJ Dez/25 | 8628 | 23 | **23/23** | fechamento | **OK** |
| Nubank PJ Out/25 | 286 | 24 | **24/24** | fechamento | **OK** |
| Nubank PJ (9 meses) | varios | 25-30/mes | **287/287 total** | fechamento | **OK** |
| Cora | 0 | 21 | **21/21** | fechamento | **OK** |
| Caixa | 586 | 6 | **6/6** | fechamento | **OK** |
| PagBank | 2239 | 15 | 1/15 | abertura | Diverge (SI = primeiro saldo, nao anterior) |
| C6 Bank | 1934 | 9 | 1/9 | abertura | Diverge (saldo = abertura do dia) |
| BB | 1141 | 19 | 0/19 | fechamento | Diverge (formato saldo complexo) |
| Inter | 16019 | 5 | 1/5 | abertura | Diverge (primeiro saldo = abertura) |

### Campo no retorno da API:
```json
{
  "verificacao_saldos": {
    "saldo_inicial": 8628.34,
    "saldo_inicial_encontrado": true,
    "saldo_final_informado": 1348.57,
    "saldo_final_calculado": 1348.57,
    "conferencia_ok": true,
    "divergencias": [],
    "saldos_intermediarios_verificados": 23,
    "saldos_intermediarios_ok": 23,
    "modo_saldo": "fechamento"
  }
}
```

## 7.4 PARSERS dict (27 entradas), _ASSINATURAS (23 entradas), FALLBACK_PARSERS (5 entradas)

*(Sem alteracoes nas entradas — ver v1.0)*

## 7.5 _NOME_BANCO_EXIBICAO (28 entradas — CORRIGIDO v2)

**Adicionadas 8 entradas na v2:** itau_n2, inter_n2, itau_empresas_n2, santander_consolidado, bradesco_net_empresas, santander_empresas_v1, santander_empresas_v2, stone_n2. Agora cobre 100% dos bancos em PARSERS.

## 7.6 Deteccao Automatica (CORRIGIDO v2)

**Bug corrigido:** PDFs Nubank PJ (conta 587637138) eram detectados como `mercado_pago` porque o texto "mercado pago" aparecia em descricoes de transacoes Pix. A assinatura de mercado_pago foi tornada mais especifica — agora exige "extrato de conta" ou "detalhe dos movimentos" junto com "mercado pago".

**Resultado:** 13/13 PDFs Nubank detectados corretamente. 1/1 PDF Mercado Pago real detectado corretamente.

## 7.7 Extracao de Saldo Inicial (CORRIGIDO v2)

**BB:** Regex corrigido — formato `Saldo Anterior 1.141,05 (-)` com (+/-) no final nao era capturado pelo regex anterior. Agora usa regex especifico para formato BR.

**Inter N2:** Delegado para mesma logica do `inter` (que ja funcionava). Antes retornava None porque `inter_n2` nao tinha branch no `_extrair_saldos_pdf()`.

---

# 8. LOGICA FINANCEIRA

*(Sem alteracoes — DRE, indicadores, score, insights. Ver v1.0)*

---

# 9. SIMULACAO TRIBUTARIA

*(Sem alteracoes. Bug conhecido: Anexo I DAS soma 120%. Ver v1.0)*

---

# 10. CONCILIACAO BANCARIA

*(Sem alteracoes — ver v1.0)*

---

# 11. IMPORTACAO DE DADOS

*(Sem alteracoes — ver v1.0)*

---

# 12. CLASSIFICACAO CONTABIL

### motor_classificacao.py — 4 niveis (sem alteracoes):
1. Regra do usuario (RegraClassificacao)
2. Cadastro cliente/fornecedor (ClienteFornecedorEmpresa)
3. Regra automatica do sistema (16 REGRAS_SAIDA + 6 REGRAS_ENTRADA)
4. Fallback "A Classificar" (49901 despesa / 39901 receita)

### Excel Contabil com Partida Dobrada (NOVO v2)

**Arquivo:** `services/gerador_excel_contabil.py` (283 linhas)

**Funcionalidade:** Gera Excel no formato de lancamentos contabeis prontos para importacao em Contmatic/Dominio/Prosoft.

**3 abas:**
1. **Lancamentos Contabeis:** Data | Lancamento | Historico | Descricao | Debito | Credito | Valor (R$)
2. **Resumo:** SI, Entradas, Saidas, SF, conta banco, estatisticas classificacao
3. **Plano de Contas Utilizado:** contas que aparecem nos lancamentos com totais

**Logica de partida dobrada:**
- Entrada: Debito = conta banco (ex: 11202), Credito = contrapartida
- Saida: Debito = contrapartida, Credito = conta banco
- Contrapartida determinada pelo motor_classificacao.py (4 niveis)

**Cores por status:** Verde = regra usuario, Azul = cadastro, Amarelo = automatico, Vermelho = pendente

**Integracao:** Endpoint `POST /api/processar-extrato` aceita `empresa_id` opcional. Se fornecido, gera Excel contabil junto com o basico. Campos `excel_contabil_id` e `excel_contabil_url` no retorno.

**Testado com 11 bancos:** 0 debitos/creditos vazios em todos.

---

# 13-16. ORCAMENTO, ALERTAS, EQUIPE, AUDITORIA

*(Sem alteracoes — ver v1.0)*

---

# 17. FRONTEND

## 17.1 Paginas Atualizadas

| Rota | Arquivo | Linhas | Alteracao v2 |
|------|---------|--------|-------------|
| `/master` | master/page.tsx | **1028** | **ATUALIZADO** — seletor escritorio, card resumo, lista filtrada |
| `/admin` | admin/page.tsx | ~600 | *(sem alteracao frontend, filtro e backend-side)* |
| Demais | - | - | Sem alteracoes |

### /master — Central de Controle (ATUALIZADO v2)

**Aba Usuarios redesenhada:**
- Interface `EscritorioResumo` adicionada (total_usuarios, pendentes, ativos, empresas)
- Estado `selectedEscId` + `resumoEsc` substituem `filtroEscId`
- Dropdown seletor mostra: nome + plano + contagem
- Sem selecao: mensagem orientativa com icone
- Com selecao: card KPI (4 metricas) + lista usuarios com badges
- Acoes (aprovar/reprovar/role/delete) enviam `?escritorio_id=X`
- `loadResumo()` chama `GET /api/master/escritorios/{id}/resumo`
- `loadUsuarios()` requer `selectedEscId` (nao carrega sem selecao)

## 17.2-17.6 ClientWrapper, Contexts, Design System

*(Sem alteracoes — ver v1.0)*

---

# 18. INFRAESTRUTURA E DEPLOY

*(Sem alteracoes — ver v1.0)*

---

# 19. FLUXOS DE NEGOCIO

## 19.4 Upload PDF (single) — ATUALIZADO v2

1. Usuario seleciona banco e arquivo em `/`
2. `POST /api/processar-extrato` (multipart: arquivo, banco, senha_pdf, **empresa_id**)
3. Backend: salva temp, chama `processar_extrato(path, banco, senha)` de extrator_pdf.py
4. Pipeline: pikepdf check -> page limit -> detectar_banco -> parser.extrair() -> fallback se 0 -> categorizar -> calcular totais -> extrair saldos -> **verificacao progressiva**
5. Gera Excel basico via `gerar_excel()`, salva com UUID
6. **Se empresa_id fornecido:** gera Excel contabil via `gerar_excel_contabil()`, salva com UUID_contabil
7. Retorna: banco_detectado, total_transacoes, resumo, excel_id, **excel_contabil_id**, transacoes, **verificacao_saldos**
8. Frontend: mostra resumo com cards, graficos, tabela de transacoes
9. Usuario clica "Baixar Excel" -> `GET /api/download/{excel_id}` -> blob download
10. **Opcional:** "Baixar Excel Contabil" -> `GET /api/download/{excel_contabil_id}`

## 19.11 Gestao de Usuarios pelo Master — ATUALIZADO v2

1. Master acessa `/master` -> aba "Usuarios"
2. Frontend mostra **seletor de escritorio** (carrega `GET /api/master/escritorios`)
3. **Sem selecao:** mensagem "Selecione um escritorio para gerenciar seus usuarios"
4. Master seleciona escritorio
5. Frontend carrega `GET /api/master/escritorios/{id}/resumo` + `GET /api/master/usuarios?escritorio_id=X`
6. Card resumo mostra totais (usuarios, pendentes, ativos, empresas)
7. Lista mostra APENAS usuarios daquele escritorio
8. Acoes (aprovar/reprovar/role/delete) enviam `?escritorio_id=X` para validacao backend
9. Se usuario nao pertence ao escritorio -> 403

---

# 20. TESTES

## 20.1 Testes Existentes

**test_parsers.py (164 linhas):** NAO E UM TESTE AUTOMATIZADO. Zero assertions.

## 20.2 Testes Realizados nas Sessoes de Trabalho (NOVO v2)

| Tipo | Bancos Testados | PDFs | Resultado |
|------|----------------|------|-----------|
| Import de parsers | 31/31 | - | 31/31 OK |
| Deteccao automatica | 15 bancos | 29 PDFs | 29/29 corretos |
| Extracao de transacoes | 15 bancos | 29 PDFs | 23 com tx, 6 zerados (esperado) |
| Verificacao saldos | 7 bancos | 17 PDFs | 314/314 OK (Nubank+Cora+Caixa) |
| Excel basico | 11 bancos | 23 PDFs | 23/23 gerados |
| Excel contabil | 11 bancos | 23 PDFs | 23/23 gerados, 0 D/C vazios |
| Tenant isolation | - | - | Backend+Frontend verificados |

### Cobertura de testes automatizados: ainda 0%

---

# 21. PONTOS CRITICOS E DEBITOS TECNICOS

## 21.1-21.6 (sem alteracoes — ver v1.0)

## 21.7 _NOME_BANCO_EXIBICAO incompleto
**STATUS: CORRIGIDO v2** — 28/28 entradas, 0 faltando.

## 21.8 Codigo morto
*(Sem alteracoes — ver v1.0)*

## 21.9 Problemas encontrados na auditoria

| # | Severidade | Descricao | Status v2 |
|---|-----------|-----------|-----------|
| 1 | **CRITICO** | 0 endpoints chamam registrar_auditoria() | **PENDENTE** |
| 2 | **CRITICO** | Admin de escrit. A pode aprovar/deletar usuarios de B (main.py) | **PENDENTE** (corrigido em master.py, nao em admin) |
| 3 | **CRITICO** | Gestor ve colaboradores de TODOS os escritorios | **PENDENTE** |
| 4 | **CRITICO** | Qualquer usuario pode manipular bancos de qualquer empresa | **PENDENTE** |
| 5 | **CRITICO** | Admin ve audit logs cross-tenant | **PENDENTE** |
| 6 | **ALTO** | Download Excel sem verificacao de ownership | **PENDENTE** |
| 7 | **ALTO** | POST /api/carteira cria empresa SEM escritorio_id | **PENDENTE** |
| 8 | **ALTO** | Simples Anexo I distribuicao soma 120% | **PENDENTE** |
| 9 | **MEDIO** | Auth duplicado: main.py vs auth_utils.py | **PENDENTE** |
| 10 | **MEDIO** | Senha minima: 8 chars no registro, 6 na troca | **PENDENTE** |
| 11 | **MEDIO** | backup_service.list() inexistente | **PENDENTE** |
| 12 | **MEDIO** | score_saude: branch quedas>=3 inalcancavel | **PENDENTE** |
| 13 | **MEDIO** | .env.production.example nomes inconsistentes | **PENDENTE** |
| 14 | **BAIXO** | Datas como String, nao DateTime | **PENDENTE** |
| 15 | **BAIXO** | Nenhum ORM relationship() | **PENDENTE** |
| 16 | **BAIXO** | Endpoint publico sem auth: /api/importacao/tipos | **PENDENTE** |
| 17 | **BAIXO** | 1 worker em producao | **PENDENTE** |
| 18 | - | XP Posicao password crash | **CORRIGIDO v2** |
| 19 | - | _NOME_BANCO_EXIBICAO faltando 8 | **CORRIGIDO v2** |
| 20 | - | Deteccao Nubank→Mercado Pago (11 PDFs) | **CORRIGIDO v2** |
| 21 | - | BB saldo_inicial=None | **CORRIGIDO v2** (SI=1141.05) |
| 22 | - | Inter N2 saldo_inicial=None | **CORRIGIDO v2** (SI=16019.02) |
| 23 | - | GET /api/master/usuarios sem tenant | **CORRIGIDO v2** (requer escritorio_id) |
| 24 | - | GET /api/admin/usuarios sem tenant | **CORRIGIDO v2** (filtra por escritorio) |

---

# 22. METRICAS DO PROJETO

| Metrica | v1.0 | v2.0 | Alteracao |
|---------|------|------|----------|
| Arquivos Python (backend) | 99 | **100** | +1 (gerador_excel_contabil.py) |
| Arquivos TSX/TS/CSS (frontend) | 65 | 65 | - |
| **Total arquivos codigo** | **164** | **165** | +1 |
| Linhas Python (backend) | ~21.400 | **~22.000** | +~600 |
| Linhas TSX/TS/CSS (frontend) | ~28.200 | ~28.200 | - |
| **Total linhas codigo** | **~49.600** | **~50.200** | +~600 |
| Endpoints totais | 140 | 140 | - (resumo era novo na v1) |
| Modelos/tabelas | 22 | 22 | - |
| Parsers bancarios | 31 | 31 | - |
| Bancos suportados | 21 | 21 | - |
| Matchers conciliacao | 14 | 14 | - |
| Testes automatizados | 0 | 0 | - |
| Paginas frontend | 36 | 36 | - |
| Regras de insight | 16 | 16 | - |
| Componentes UI | 10 | 10 | - |
| **Parsers com verif. saldos** | **0** | **7** | +7 (Nubank,BB,Cora,Caixa,C6,Inter,PagBank) |
| **PDFs testados com sucesso** | **0** | **29** | +29 |
| **Bancos com Excel contabil** | **0** | **11** | +11 |

---

# 23. PONTOS DE EXTENSAO

## 23.1 Adicionar novo banco/parser
1. Criar `backend/services/parsers/novobanko.py` herdando `ParserBase`
2. Implementar `extrair() -> list[dict]`
3. **Opcional v2:** Implementar `_extrair_saldos_intermediarios() -> list[dict]` para verificacao progressiva
4. Adicionar entrada no dict `PARSERS` em `extrator_pdf.py`
5. Adicionar assinatura em `_ASSINATURAS` (posicao importa)
6. Adicionar nome em `_NOME_BANCO_EXIBICAO`
7. **Opcional v2:** Adicionar logica de extracao de saldo em `_extrair_saldos_pdf()`
8. Opcional: criar matcher em `conciliacao/matchers/`

## 23.2-23.6

*(Sem alteracoes — ver v1.0)*

---

# 24. RESUMO EXECUTIVO

## Estado Geral

O Controllo e uma aplicacao SaaS funcional com ~50.200 linhas de codigo, cobrindo um dominio complexo (contabilidade BPO). O core de extracao de PDF (31 parsers para 21 bancos) e a logica financeira (DRE, indicadores, insights, simulacao tributaria) sao maduros e bem implementados. O frontend e moderno (Next.js 16, React 19, Tailwind 4) com dark/light theme completo.

**Novidades da v2:** Verificacao progressiva de saldos (314/314 OK em 3 bancos), Excel contabil com partida dobrada (11 bancos), isolamento de tenant parcial na Central de Controle, correcao de bug de deteccao Nubank, 29 PDFs testados com sucesso.

## Maiores Riscos Tecnicos (atualizados)

1. **Isolamento de tenant PARCIALMENTE CORRIGIDO** — master.py e admin/usuarios corrigidos, mas 5+ endpoints ainda sem isolamento (equipe, auditoria, empresas/bancos, admin CRUD)
2. **Zero testes automatizados** — nenhuma cobertura apesar dos testes manuais extensivos
3. **Zero logging de auditoria ativo** — `registrar_auditoria()` nunca chamada
4. **Float para valores financeiros** — todos os 22 modelos
5. **Single-worker sincrono** — PDF processing bloqueia

## 5 Prioridades de Acao (atualizadas)

| # | Acao | Impacto | Esforco | Status |
|---|------|---------|---------|--------|
| 1 | **Completar isolamento tenant** (admin CRUD, equipe, auditoria, empresas/bancos) | Critico — seguranca | Medio (2-3 dias) | **PARCIAL** — master.py feito |
| 2 | **Ativar registrar_auditoria()** | Critico — compliance | Medio (1-2 dias) | PENDENTE |
| 3 | **Adicionar testes automatizados** | Alto — qualidade | Alto (1-2 semanas) | PENDENTE |
| 4 | **Corrigir SI divergente** PagBank/C6/BB/Inter | Medio — precisao | Medio (1-2 dias) | **PARCIAL** — BB/Inter SI extraido |
| 5 | **Adicionar workers + async PDF** | Medio — performance | Medio (2-3 dias) | PENDENTE |

---

# 25. HISTORICO DE ALTERACOES

## Sessao 1 — Isolamento Tenant

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| routers/master.py | +endpoint resumo, escritorio_id obrigatorio em GET usuarios, validacao 403 em aprovar/reprovar/role/delete |
| main.py | +filtro escritorio_id em GET /api/admin/usuarios para nao-master |
| frontend/app/master/page.tsx | +interface EscritorioResumo, +seletor escritorio, +card resumo, +lista filtrada, +loadResumo |

## Sessao 2 — Auditoria Tecnica Completa

**Arquivo criado:** AUDITORIA_TECNICA_CONTROLLO.md (v1.0, 1235 linhas)

## Sessao 3 — Parsers: Correcoes e Verificacao Saldos

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| services/parsers/xp_posicao.py | +password param no __init__ |
| services/parsers/base.py | +metodo _extrair_saldos_intermediarios() (padrao vazio) |
| services/parsers/nubank.py | +override _extrair_saldos_intermediarios (Saldo do dia) |
| services/extrator_pdf.py | +8 nomes em _NOME_BANCO_EXIBICAO, +bloco verificacao progressiva, +propagacao verificacao_saldos em processar_extrato |

## Sessao 4 — Expansao Verificacao + Propagacao

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| services/parsers/bb.py | +override _extrair_saldos_intermediarios |
| services/parsers/cora.py | +override _extrair_saldos_intermediarios |
| services/parsers/caixa.py | +override _extrair_saldos_intermediarios |
| services/parsers/c6bank.py | +override _extrair_saldos_intermediarios |
| services/parsers/inter.py | +override _extrair_saldos_intermediarios |
| services/parsers/pagbank.py | +override _extrair_saldos_intermediarios |
| services/extrator_pdf.py | +propagacao verificacao_saldos em processar_extrato |

## Sessao 5 — Excel Contabil com Partida Dobrada

**Arquivo criado:**
| Arquivo | Linhas | Proposito |
|---------|--------|-----------|
| services/gerador_excel_contabil.py | 283 | Excel contabil 3 abas, partida dobrada, integrado com motor_classificacao |

**Arquivo modificado:**
| Arquivo | Alteracao |
|---------|-----------|
| main.py | +empresa_id e db no endpoint processar-extrato, +bloco geracao Excel contabil, +excel_contabil_id/url no retorno |

## Sessao 6 — Correcao Deteccao + Modo Duplo Saldos

**Arquivo modificado:**
| Arquivo | Alteracao |
|---------|-----------|
| services/extrator_pdf.py | Assinatura mercado_pago mais especifica, BB regex saldo corrigido, Inter N2 delegacao, verificacao modo duplo (pre/pos), fallback primeiro saldo intermediario quando SI=None |
| services/gerador_excel_contabil.py | Auto-map nomes de banco das transacoes ao conta_banco_map |

## Resumo Total de Alteracoes

| Tipo | Quantidade |
|------|-----------|
| Arquivos criados | 2 (gerador_excel_contabil.py, AUDITORIA_TECNICA_CONTROLLO.md) |
| Arquivos backend modificados | 13 (main.py, extrator_pdf.py, master.py, base.py, 7 parsers, gerador_excel_contabil.py, xp_posicao.py) |
| Arquivos frontend modificados | 1 (master/page.tsx) |
| Arquivos NAO alterados | models.py, config.py, auth_utils.py, financeiro_service.py, importacao_service.py, insights_engine.py, simulacao_tributaria_service.py, motor_classificacao.py, conciliacao/*, tributario/*, todos os demais routers, todos os demais parsers |

## Sessao 14 — Guard Silent Failure + Log 422 + Investigacao Excel vs Extrato

**Branch:** `fix/bradesco-saldoanterior-silentfail-log422` (a partir de main `3f7c0dd`)
**Escopo final:** reduzido apos analise inicial (fix bradesco-saldoanterior abandonado por estar fora de R2).

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| backend/main.py | Guard silent failure no endpoint POST /api/processar-extrato. Quando parser retorna 0 transacoes mas pipeline detecta movimento (`abs(SF - SI) > 1.0`), retorna HTTP 422 com `detail.erro="extracao_vazia"` em vez de 200 OK com Excel vazio. Log `[GUARD]` precede o raise para diagnostico. |
| backend/services/pipeline_extracao.py | Logs estruturados `[PIPELINE-422]` em 6 pontos onde `r.passo_falha` e setado: arquivo nao encontrado (passo 1), excede limite de paginas (1), erro de senha/abertura (1), PDF imagem/vetorial (1), banco nao identificado (1), parser nao implementado (passo 2). Sem alteracao na logica do pipeline. |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

**Bugs cobertos:**
- bug-silent-failure: caso `Santander N2.pdf` (e similares) retornava 200 OK com Excel=0 quando o extrato tem movimento. Fix detecta divergencia via `_pipeline_result.saldo_inicial/saldo_final` vs `resultado["transacoes"]`.

**Bugs investigados read-only (nao corrigidos nesta sessao, materia para Sessao 15):**
- bug-saldoanterior CW TOUR: o parser `bradesco_net_empresas` ja filtra "SALDO ANTERIOR" corretamente (linha 33 de `_SKIP_LOWER`). O problema reportado ("Excel=-329.51 vs Extrato=588.87, diff=-918.38") e na funcao `_extrair_saldos_pdf()` em `extrator_pdf.py`: nao tem branch para `bradesco_net_empresas` (cai no fallback generico) e o helper `_ultimo_num()` perde o sinal negativo do "26/12/2025 SALDO ANTERIOR -918,38". Resultado: SI=918.38 (positivo errado), SF=None (PDF usa "Total" nao "Saldo final"), e Passo 3 do pipeline calcula SF=918.38+E-S=588.87 (errado). Excel=-329.51 esta CERTO. Documentacao completa em `/tmp/sessao14/analise-bug-extrato-total.md` (scratch, nao versionado).

**Testes:** 757 passou, 0 falhou. 2 erros pre-existentes em `test_pagbank.py` e `test_pagbank_integracao.py` (scripts CLI legados sem fixtures, herdados do commit inicial `d7f4689`).

**Nao tocados (R2):** `extrator_pdf.py`, `_ASSINATURAS`, `_PARSERS`, parsers, `gerador_excel_contabil.py`, `gerador_excel_pipeline.py`, `requirements.txt`, frontend, models.

**Validacao em prod (apos deploy):** subir `Santander N2.pdf` deve devolver 422 com mensagem em vez de 200 com Excel vazio; subir qualquer PDF que cai em 422 deve gerar log `[PIPELINE-422]` com motivo identificavel; logs `[GUARD]` aparecem somente em silent failures. Comportamento de PDFs OK (Bradesco net, Santander N3, etc.) inalterado.

## Sessao 15 — Fix `/Root dictionary` (pikepdf upgrade + instrumentacao pre-pipeline)

**Data**: 2026-04-30
**Branch**: `fix/pikepdf-upgrade-instrumentacao-prepipeline` (a partir do tip da Sessao 14, commit `8e645a8`)
**Commit**: `a3ac70e`

**Problema**: pikepdf 9.7.0 falhava com "unable to find /Root dictionary" em PDFs especificos gerados por iText 2.0.8 e similares. Confirmado em producao com `Bradesco_Net_Empresas.PDF` (SEOLIN, jan/2025). A mensagem de erro vazava direto pro frontend como 422, sem passar pelo pipeline 8 passos (logs `[PASSO N]` ausentes). Localmente, pikepdf 10.5.1 abre os mesmos PDFs sem erro.

**Solucao**:
1. `backend/requirements.txt`: `pikepdf==9.7.0` -> `pikepdf==10.5.1`. Nenhuma outra dependencia alterada.
2. `backend/services/extrator_pdf.py`: novo `except Exception as _e_prepipeline` ao redor de `pikepdf.open()` em `extrair_extrato()` (linha ~858). Loga `[PRE-PIPELINE-ERROR]` com nome do arquivo, tipo da excecao, mensagem e versao do pikepdf, depois re-raise. O comportamento de erro esta preservado: o re-raise cai no except externo da funcao (linha ~1084) que converte em `resultado["erro"]`. Permite diagnostico futuro se outro PDF falhar por motivo diferente.

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| backend/requirements.txt | pikepdf 9.7.0 -> 10.5.1 (linha 6, unica mudanca). |
| backend/services/extrator_pdf.py | +`except Exception` com log `[PRE-PIPELINE-ERROR]` antes de re-raise no bloco que chama `pikepdf.open()` em `extrair_extrato()`. Sem alteracao em logica de extracao, deteccao, parsers ou pipeline. |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

**Testes:** 756 passou, 1 falhou, 2 erros pre-existentes. A unica falha (`test_t8_senhas_comuns_rejeita_via_zxcvbn`) foi confirmada como pre-existente na branch base (Sessao 14 `8e645a8`) via `git stash`/rerun: nao relacionada a pikepdf nem a `extrator_pdf.py`. Os 2 erros em `test_pagbank.py`/`test_pagbank_integracao.py` permanecem como herdados do commit inicial `d7f4689` (scripts CLI legados sem fixtures), conforme Sessao 14.

**Nao tocados (R2):** parsers (`bradesco_*.py`, `santander_*.py`, `itau_*.py`, `nubank.py`, etc), `pipeline_extracao.py`, `gerador_excel_*.py`, `main.py`, `_ASSINATURAS`, `_PARSERS`, deteccao de banco, Dockerfiles, docker-compose, atualizar.sh, backup.sh, frontend, demais libs do `requirements.txt` (pdfplumber, pdfminer.six, PyMuPDF intactos).

**Risco mitigado pendente de validacao em prod:** atualizacao de pikepdf 9.7.0 -> 10.5.1 pode afetar Nubank, Itau padrao e outros PDFs que ja funcionavam. Confirmar em prod apos deploy.

**Validacao em prod (apos deploy):**
- Subir `Bradesco_Net_Empresas.PDF` (SEOLIN jan/2025): NAO deve mais dar `/Root dictionary`. Deve passar pelo pikepdf, chegar no pipeline (logs `[PASSO N]`), e provavelmente retornar 422 com `[PIPELINE-422]` por outra causa (mis-route — Sessao 17).
- Nubank, Itau padrao: continuam OK como antes.
- `Bradesco_Net_Empresas (2).pdf` (CW TOUR): continua dando 200 OK com diff -918,38. Bug em `_extrair_saldos_pdf` sera atacado na Sessao 16.
- Se aparecer `[PRE-PIPELINE-ERROR]` em algum PDF, capturar logs para proxima sessao.

**Pendente das sessoes anteriores:**
- Bug Excel vs Extrato em CW TOUR (`_extrair_saldos_pdf` sem branch `bradesco_net_empresas`, `_ultimo_num` perde sinal negativo): Sessao 16.
- Mis-routes de detecao de banco diagnosticados na Sessao 14: Sessao 17.

## Sessao 16 — Fix `_extrair_saldos_pdf` para `bradesco_net_empresas` (sinal negativo + Hipotese D)

**Data**: 2026-04-30
**Branch**: `fix/bradesco-net-empresas-saldoanterior-sinal` (a partir do tip da Sessao 15, commit `e3673c4`)
**Commit**: <preencher apos commit>

**Problema**: Pipeline calculava SI/SF com sinais invertidos no `Bradesco Net Empresas (2).pdf` (CW TOUR EIRELI jan/2026), gerando "Excel vs Extrato diff=-918,38" em producao mesmo com pipeline marcando como RECONCILIADO/ALTA porque a equacao `SI+E-S=SF` batia matematicamente.

**Causa raiz** (mapeada na Sessao 14, analise read-only):
- `_extrair_saldos_pdf` em `backend/services/extrator_pdf.py` nao tem branch para `banco='bradesco_net_empresas'` -> caia no fallback generico (linha 456-467).
- Helper `_ultimo_num` (linha 39-42) usa regex `[\d.,]+` que descarta o sinal `-`. Para "26/12/2025 SALDO ANTERIOR -918,38", extraia 918.38 em vez de -918.38.
- SF nao era extraido porque PDFs Bradesco Net Empresas usam label "Total" (nao "Saldo final"). Pipeline calculava SF a partir do SI errado.

**Solucao (Hipotese D, aprovada pelo Allan)**:
1. Branch nova em `_extrair_saldos_pdf` para `banco == 'bradesco_net_empresas'` que:
   - Extrai SI da primeira ocorrencia de `[DD/MM/YYYY] SALDO ANTERIOR <valor>` preservando sinal negativo via helper local `_parse_br_signed`.
   - SF depende do formato do cabecalho:
     - Se ha coluna "Investimento sem/com Baixa" no PDF (formato "Mensal", 3 valores na linha `Ag|Conta`): SF = ULTIMO `Total <c> <d> <s>` antes da secao "Ultimos Lancamentos" (saldo do fim do periodo pedido).
     - Caso contrario (formato "Consolidado", 2 valores na linha `Ag|Conta`): SF = primeiro valor da linha `Ag|Conta` (Total Disponivel).
2. Log estruturado `[EXTRATOR-SALDOS] banco=bradesco_net_empresas si=... sf=... regra_sf=... tem_coluna_investimento=...` antes de retornar — permite auditoria em producao.
3. Helper `_ultimo_num` NAO foi tocado (escopo cirurgico, evita regressao em outros bancos que dependem dele).
4. O branch legado `if banco == 'bradesco_empresas'` (alias) foi mantido logicamente identico (so renomeado o comentario).

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| backend/services/extrator_pdf.py | +branch `bradesco_net_empresas` (~96 linhas) ANTES do alias `bradesco_empresas`. Inclui helper local `_parse_br_signed` (preserva sinal), regex SI/cabecalho/Total, deteccao Hipotese D e log `[EXTRATOR-SALDOS]`. |
| backend/tests/test_extrair_saldos_bradesco_net_empresas.py | NOVO. 5 testes: SI/SF para CW TOUR, SEOLIN, TANIA dez, TANIA nov + regression `test_cw_tour_pipeline_diff_zero` que asserta `\|si+excel_liquido - sf\| < 0.01` para o caso original. |
| backend/tests/fixtures/cw_tour_jan2026_raw.txt | NOVO. Texto raw extraido via pdfplumber do `Bradesco Net Empresas (2).pdf`. 1521 chars / 45 linhas. |
| backend/tests/fixtures/seolin_jan2025_raw.txt | NOVO. Texto raw do `Bradesco Net Empresas.PDF` (SEOLIN). 2459 chars / 85 linhas. |
| backend/tests/fixtures/tania_dez2025_raw.txt | NOVO. Texto raw do `Bradesco net.pdf`. 6713 chars / 214 linhas. |
| backend/tests/fixtures/tania_nov2025_raw.txt | NOVO. Texto raw do `Bradesco net2.pdf`. 7108 chars / 237 linhas. |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

**Politica de fixtures respeitada**: zero PDFs binarios commitados; apenas fixtures `.txt` raw (texto que `pdfplumber` extrai). PDFs reais permanecem em `backend/tests/fixtures/pdfs_reais/` (gitignored desde a Sessao 13).

**Testes:** 761 passou, 1 falha pre-existente (`test_t8_senhas_comuns_rejeita_via_zxcvbn`, herdada da Sessao 14), 2 erros pre-existentes (`test_pagbank.py`/`test_pagbank_integracao.py`, herdados do commit `d7f4689`). Os 5 novos testes da Sessao 16 passam isoladamente e na suite completa. Diferenca exata para a Sessao 15 = +5 (apenas os novos). Smoke test adicional rodando `_extrair_saldos_pdf` real contra os 4 PDFs em `pdfs_reais/` confirmou os SI/SF esperados em todos os 4 casos.

**Validacao SI/SF nos 4 PDFs alvo:**
| PDF | SI esperado | SI extraido | SF esperado | SF extraido | regra_sf | tem_invest |
|-----|-------------|-------------|-------------|-------------|----------|------------|
| CW TOUR jan/2026 | -918.38 | -918.38 | -1247.89 | -1247.89 | cabecalho_total_disponivel | False |
| SEOLIN jan/2025 | 89479.75 | 89479.75 | 572.64 | 572.64 | ultimo_total_secao_principal | True |
| TANIA dez/2025 | 78019.32 | 78019.32 | 70042.18 | 70042.18 | cabecalho_total_disponivel | False |
| TANIA nov/2025 | 96735.73 | 96735.73 | 95043.32 | 95043.32 | cabecalho_total_disponivel | False |

**Nao tocados (R2):** `_PARSERS`, `_ASSINATURAS`, deteccao de banco, helper `_ultimo_num`, parsers Bradesco/Santander/Itau/Nubank/etc, `pipeline_extracao.py`, `gerador_excel_*.py`, `main.py`, `requirements.txt`, Dockerfiles, frontend.

**Validacao em prod (apos deploy)**:
- `Bradesco_Net_Empresas (2).pdf` (CW TOUR): deve devolver Excel=-329.51 e Extrato=-329.51 (diff=0). Log `[EXTRATOR-SALDOS] regra_sf=cabecalho_total_disponivel tem_coluna_investimento=False`.
- `Bradesco_Net_Empresas.PDF` (SEOLIN): se passar pela deteccao de banco corretamente (mis-route ja diagnosticado para Sessao 17), deve devolver SI=89479.75 / SF=572.64. Log com `regra_sf=ultimo_total_secao_principal tem_coluna_investimento=True`.
- TANIA dez/nov: continuam OK (eram cobertos pelo fallback generico antes, embora com riscos sutis em casos com sinal negativo).
- Outros bancos (Nubank, Itau, etc): inalterados — o fix e isolado ao branch `bradesco_net_empresas`.

**Risco residual conhecido**: a regra "SF = Total Disponivel do cabecalho" assume que o periodo pedido e proximo da data de emissao. Se aparecer um PDF Bradesco Net Empresas formato "Consolidado" com janela longa entre periodo e emissao (ex: extrato pedido 6 meses atras), o `regra_sf=cabecalho_total_disponivel` pode nao bater com o "saldo do fim do periodo". O log estruturado em producao permitira identificar o caso e ajustar.

**Pendente:**
- Mis-routes de deteccao de banco diagnosticados na Sessao 14 (B2S->santander, SEOLIN->inter_n2, Santander_N1->mercado_pago): Sessao 17.
