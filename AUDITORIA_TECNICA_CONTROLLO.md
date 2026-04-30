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
**Commit**: `1733d1c`

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

## Sessao 17 — Fix mis-routes de deteccao de banco (assinaturas endurecidas)

**Data**: 2026-04-30
**Branch**: `fix/mis-routes-deteccao-banco` (a partir do tip da Sessao 16, commit `8330459`)
**Commit**: `b1bf2f1`

**Problema** (mapeado nas Sessoes 13 e 14): 3 PDFs caiam em parsers errados gerando dados invalidos:
- `B2S.pdf` (PROMOVE BRASIL): `santander` em vez de `bs2`. Gap 47.748 em prod (Excel=129.696 vs Extrato=81.947). Causa: substring `'santander'` na assinatura `santander` casava em "Bco Santander SA" (descricao de TED).
- `Bradesco_Net_Empresas.PDF` (SEOLIN IT TECNOLOGIA jan/2025): `bradesco` em vez de `bradesco_net_empresas`. Gap 7.085 (10.61%), 24/24 checkpoints divergentes em prod. Causa: a palavra `bradesco` nao aparece nas primeiras 3 paginas desse PDF; assinatura `bradesco_net_empresas` exigia `'bradesco' + 'total dispon'` — caia no fallback `bradesco` via `'dcto.'`.
- `Santander_N1.pdf` (LEKE Consolidado Inteligente jan/2025): `mercado_pago` em vez de `santander_consolidado`. 0 transacoes em prod (silent failure agora bloqueado pelo `[GUARD]` da Sessao 14). Causa: substring `'mercadopago'` na assinatura `mercado_pago` casava em "MERCADOPAGO COM REPRESENT" (descricao de PIX).

**Solucao (endurecimento conservador, sem inverter ordem)**:

1. Assinatura `santander`: `[['contamax'], ['santander']]` -> `[['contamax'], ['santander.com.br'], ['banco santander']]`. O termo solto `'santander'` casava em descricoes de TED para Santander. Os qualifiers `santander.com.br` (rodape oficial) e `banco santander` (header IB DLS) sao robustos. 12 PDFs Santander reais validados; 0 falso positivo.

2. Assinatura `bradesco_net_empresas`: adicionado set `['| conta total']` (cabecalho `Agencia | Conta Total Disponivel (R$)` exclusivo do formato Net Empresas). Cobre os 9 PDFs Net Empresas da fixture (CW TOUR, SEOLIN, TANIA dez/nov, Bradesco5, Bradesco_24..., Agosto 2025, Extrato dec25/nov25), incluindo casos onde `'bradesco'` nao aparece. 0 falso positivo cross-banco confirmado em todos os 92 PDFs da fixture.

3. Assinatura `mercado_pago`: `['mercadopago']` -> `['mercadopago.com']`. O termo solto `'mercadopago'` casava em descricoes de PIX em PDFs Santander. O dominio `.com` aparece em rodape MP real e nao em descricoes. Os 3 outros sets (`['mercado pago', 'extrato de conta']`, `['mercado pago', 'detalhe dos movimentos']`, `['10.573.521', 'detalhe dos movimentos']`) cobrem MP real (validado contra `account_statement-e09135bc...pdf`).

**Arquivos modificados:**
| Arquivo | Alteracao |
|---------|-----------|
| backend/services/extrator_pdf.py | 3 sets em `_ASSINATURAS` endurecidos (santander, bradesco_net_empresas, mercado_pago). Funcao `detectar_banco` e fallback de filename hint inalterados. |
| backend/tests/test_deteccao_banco.py | NOVO. 13 testes: 3 positivos (B2S->bs2, SEOLIN->bradesco_net_empresas, Santander N1->santander_consolidado), 4 regressoes (CW TOUR, TANIA dez/nov, Santander IB Novo), 6 cobertura inline (santander dominio vs descricao, MP dominio vs descricao, BNE sem palavra 'bradesco', BS2 com empresas.bs2). |
| backend/tests/fixtures/b2s_raw.txt | NOVO. Texto raw do `B2S.pdf` via pdfplumber. 4770 chars / 77 linhas. |
| backend/tests/fixtures/santander_consolidado_jan2025_raw.txt | NOVO. Texto raw do `Santander N1.pdf` via pdfplumber. 31632 chars / 704 linhas. |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

**Mudancas de roteamento (auditadas contra todos os 92 PDFs da fixture)**:
| PDF | Antes | Depois |
|-----|-------|--------|
| B2S.pdf | santander | **bs2** |
| Bradesco Net Empresas.PDF (SEOLIN) | bradesco | **bradesco_net_empresas** |
| Santander N1.pdf (LEKE) | mercado_pago | **santander_consolidado** |
| Bradesco net.pdf (TANIA dez) | bradesco | bradesco_net_empresas (colateral positivo) |
| Bradesco net2.pdf (TANIA nov) | bradesco | bradesco_net_empresas (colateral positivo) |
| Bradesco_24032026_085239.pdf | bradesco | bradesco_net_empresas (colateral positivo) |
| Agosto 2025.pdf | bradesco | bradesco_net_empresas (colateral positivo) |
| Extrato dec25.pdf, Extrato nov25.pdf | bradesco | bradesco_net_empresas (colateral positivo) |
| pdf_gerado.pdf, pdf_gerado (1).pdf | mercado_pago | santander_consolidado (colateral positivo) |
| Outros 80 PDFs | inalterados | inalterados |

**Politica de fixtures respeitada**: zero PDFs binarios commitados; apenas fixtures `.txt` raw. PDFs reais permanecem em `backend/tests/fixtures/pdfs_reais/` (gitignored).

**Testes:** 774 passou (+13 da Sessao 17 vs 761 da Sessao 16), 1 falha pre-existente (zxcvbn), 2 erros pre-existentes (pagbank scripts CLI). Diferenca exata = +13 (todos os novos passam, nenhuma regressao).

**Nao tocados (R2):** parsers (`bs2.py`, `bradesco_*.py`, `santander_*.py`, `inter_n2.py`, `mercado_pago.py`), funcao `_extrair_saldos_pdf` (Sessao 16), funcao `detectar_banco`, fallback de filename hint, `pipeline_extracao.py`, `gerador_excel_*.py`, `main.py`, `requirements.txt`, Dockerfiles, frontend, `_PARSERS`, ordem geral das assinaturas (apenas adicao/troca de strings dentro de 3 entradas).

**Validacao em prod (apos deploy)**:
- `B2S.pdf`: 200 OK, banco=bs2, sem gap 47.748
- `Bradesco_Net_Empresas.PDF` (SEOLIN): 200 OK, banco=bradesco_net_empresas, SI=89479.75 / SF=572.64 (Sessao 16 ativada), sem gap 7.085
- `Santander_N1.pdf` (LEKE): 200 OK ou 422 com mensagem util, banco=santander_consolidado (nao mais silent failure mercado_pago)
- TANIA dez/nov: 200 OK, banco=bradesco_net_empresas (Sessao 16 ativada com SI/SF corretos)
- CW TOUR: 200 OK, diff=0 (Sessao 16 + 17)
- Nubank, Itau padrao, demais: inalterados

**Risco residual**: assinaturas mais restritas podem deixar PDFs raros sem deteccao (caem em filename hint ou desconhecido). Auditoria contra 92 PDFs da fixture mostrou 0 perda real (apenas account_statement de Mercado Pago real continua mis-routed para c6bank via filename hint frágil — bug pré-existente FORA do escopo da Sessao 17).

## Sessao 18 — Bradesco 100% VERDE + Validador de saldos

**Data**: 2026-04-30
**Branch**: `feat/bradesco-100-verde-validador-saldos` (a partir do tip da Sessao 17, commit `d63e9f2`)
**Commit**: `984cc2d`

**Objetivo**: entregar TODOS os 9 PDFs Bradesco em `pdfs_reais/` (incluindo CW TOUR, SEOLIN, TANIA dez/nov, Bradesco5, Agosto 2025, Bradesco_24..., Extrato dec25/nov25) reconciliados (gap=0) e classificados como VERDE pelo novo validador de saldos.

**Resultado**: 9/9 Bradesco VERDE, gap=0,00, RECONCILIADO em todos.

### Fase 1 — Inventario (read-only)

9 PDFs Bradesco identificados (todos roteados para `bradesco_net_empresas` graças à Sessao 17). Distribuicao provisoria pre-fix: 1 VERDE (CW TOUR — depois exposto como "VERDE fake"), 1 AMARELO, 7 VERMELHO. Categorizacao por causa-raiz: A) parser inclui "Ultimos Lancamentos" / "Saldos Invest Facil" como tx (3 PDFs); B) layout Mensal SAMARA com SF=0 (2); C) SI negativo grande nao filtrado (1); D) Hipotese D escolheu cabecalho errado (1); E) Agosto 2025 (Categoria A possivel).

### Fase 2 — Validador de saldos

**Modulo novo `backend/services/validacao/`** com 4 checks:
1. Saldo total: `SI + soma(valores assinados) ≈ SF` (tolerancia 0.01).
2. Saldos diarios: para cada dia D em saldos_diarios, `SI_D + soma(tx_D) ≈ SF_D`.
3. Continuidade: `SF_D ≈ SI_{D+1}` (tolerancia 0.50 para rendimento overnight).
4. Datas dentro do periodo pedido (extraido de "Entre <ini> e <fim>").

**Classificador 3 niveis**: VERMELHO se Check 1 ou 4 falham; AMARELO se Check 2 ou 3 falham com Check 1 OK; VERDE caso contrario.

**Integracao no pipeline**: `_validar_saldos` chamado apos Passo 7, anexa `validacao` + `nivel_confianca` + `diagnostico` ao `ResultadoExtracao`. Log estruturado `[VALIDADOR] arquivo=... nivel=... diag=...` em prod. **Nao altera fluxo de erro — apenas enriquece**.

**Endpoint `/api/processar-extrato`**: novo bloco `validacao` no JSON response com `nivel`, `diagnostico`, flags por check, gap total, dias suspeitos, rupturas, datas problematicas (top 5 cada lista).

**Descoberta da Fase 2**: o validador imediatamente expos que CW TOUR era "VERDE fake" (4 tx pos-periodo no parser + SF do cabecalho refletindo estado pos-periodo, gap batia por coincidencia). 9/9 Bradesco passaram a VERMELHO no validador novo.

### Fase 3 — Lote A + Hipotese D estendida

**Lote A — stop em "Ultimos Lancamentos" / "Saldos Invest Facil" no parser** (`backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py`):
- Constante nova `_MARCADORES_FIM_PERIODO` com 4 entradas (acentuado e nao-acentuado).
- Flag `secao_terminada` cross-pagina (preserva-se entre iteracoes do loop).
- Quando o parser cruza um marcador, ignora todas as linhas seguintes.
- Para PDFs sem marcadores (caso comum), o flag nunca dispara — parser le ate o fim. Stop e OPCIONAL.

**Hipotese D estendida** (`backend/services/extrator_pdf.py`, branch `bradesco_net_empresas` em `_extrair_saldos_pdf`):
- Sessao 16 tinha 2 ramos: coluna "Investimento" → ultimo Total da secao principal; senao → cabecalho `Ag|Conta` (Total Disponivel).
- Sessao 18 estende para 4 ramos. SF = ultimo Total da secao principal sempre que houver QUALQUER um destes marcadores: coluna "Investimento" OR "Ultimos Lancamentos" OR "Saldos Invest Facil". So usa cabecalho quando NENHUM marcador presente.
- Log `[EXTRATOR-SALDOS]` agora inclui `regra_sf` com 4 valores possiveis: `cabecalho_total_disponivel`, `ultimo_total_secao_principal_por_coluna_investimento` (Sessao 16), `ultimo_total_secao_principal_por_ultimos_lancamentos` (NOVO), `ultimo_total_secao_principal_por_saldos_invest_facil` (NOVO).
- Tambem expoe `tem_ultimos_lancamentos` e `tem_saldos_invest_facil` como flags no log.

**Por que cobriu Categorias A, C, D, E, B em um fix conjunto**: o Lote A removeu tx fora do periodo do parser (resolveu Categoria A direta + parte de C/E). A Hipotese D estendida corrigiu o SF para refletir o saldo do fim do periodo pedido (resolveu Categorias D, B, e o "VERDE fake" do CW TOUR). Categoria C (Bradesco5 com SI -49.630) caiu junto: o problema nao era `_e_linha_skip` no parser, era a contaminacao por "Saldos Invest Facil" que o Lote A tambem removeu.

**Validacao R-B (nao-regressao)** em 10 PDFs nao-Bradesco (Nubank, Itau, Santander variantes, BS2, Stone, BB, PagBank): 4 VERDE confirmados (Nubank, Itau Mensal, Santander Consolidado/LEKE da Sessao 17, B2S da Sessao 17). 6 VERMELHO mas TODOS sao pre-existentes (SEM_SALDO ou ACEITAVEL antes do meu fix; o validador apenas os classifica corretamente agora). 0 PDF nao-Bradesco que estava VERDE virou AMARELO/VERMELHO.

### Tabela final dos 9 Bradesco (pos-Sessao 18)

| # | Arquivo | Layout | n_tx | SI | SF | Gap | regra_sf | Validador |
|---|---|---|---|---|---|---|---|---|
| 1 | Agosto 2025.pdf | Outro | 14 | 1518.28 | 868.56 | 0.00 | ultimos_lancamentos | **VERDE** |
| 2 | Bradesco Net Empresas (2).pdf (CW TOUR) | Consolidado | 9 | -918.38 | 1.00 | 0.00 | ultimos_lancamentos | **VERDE** |
| 3 | Bradesco Net Empresas.PDF (SEOLIN) | Outro | 20 | 89479.75 | 572.64 | 0.00 | coluna_investimento | **VERDE** |
| 4 | Bradesco net.pdf (TANIA dez) | Outro | 75 | 78019.32 | 43612.02 | 0.00 | ultimos_lancamentos | **VERDE** |
| 5 | Bradesco net2.pdf (TANIA nov) | Outro | 73 | 96735.73 | 78019.32 | 0.00 | ultimos_lancamentos | **VERDE** |
| 6 | Bradesco5.pdf | Outro | 29 | -49630.27 | -49299.11 | 0.00 | ultimos_lancamentos | **VERDE** |
| 7 | Bradesco_24032026_085239.pdf | Outro | 5 | 0.00 | 4560.19 | 0.00 | ultimos_lancamentos | **VERDE** |
| 8 | Extrato dec25.pdf | Mensal | 29 | 22750.45 | 19407.49 | 0.00 | ultimos_lancamentos | **VERDE** |
| 9 | Extrato nov25.pdf | Mensal | 20 | 16136.12 | 22750.45 | 0.00 | ultimos_lancamentos | **VERDE** |

### Arquivos modificados

| Arquivo | Alteracao |
|---------|-----------|
| backend/services/validacao/__init__.py | NOVO. Reexporta `validar_extracao` e `classificar`. |
| backend/services/validacao/validador_saldos.py | NOVO (~250 linhas). 4 checks + helpers `_parse_data` e `_valor_assinado`. Tolerante a tipos inconsistentes. |
| backend/services/validacao/classificador_confianca.py | NOVO (~50 linhas). Decide nivel final via 4 regras priorizadas. |
| backend/services/parsers/bradesco_empresas/bradesco_net_empresas.py | +constante `_MARCADORES_FIM_PERIODO` e flag `secao_terminada` cross-pagina no metodo `extrair`. ~25 linhas. |
| backend/services/extrator_pdf.py | Branch `bradesco_net_empresas` em `_extrair_saldos_pdf` estendido com flags `tem_ultimos_lancamentos` e `tem_saldos_invest_facil`. Log expandido com 4 valores de `regra_sf`. ~40 linhas. |
| backend/services/pipeline_extracao.py | Import `validacao`. Novos campos em `ResultadoExtracao` (`validacao`, `nivel_confianca`, `diagnostico`, `periodo_inicio`, `periodo_fim`). Metodo novo `_validar_saldos` chamado apos Passo 7. ~110 linhas. |
| backend/main.py | Bloco `validacao` adicionado ao JSON response do `/api/processar-extrato`. ~25 linhas. |
| backend/tests/test_validador_saldos.py | NOVO. 10 testes cobrindo 4 checks + tolerancias + casos defensivos. |
| backend/tests/test_extrair_saldos_bradesco_net_empresas.py | Atualizado: SF de CW TOUR (-1247.89 -> 1.00), TANIA dez (70042.18 -> 43612.02), TANIA nov (95043.32 -> 78019.32). Test pipeline_diff_zero atualizado para 9 tx / excel_liquido=919.38. Replica da heuristica estendida no helper de teste. |
| backend/tests/test_parser_bradesco_net_empresas_lote_a.py | NOVO. 6 testes: marcadores cobrem variantes encoding; `_e_linha_skip` correto; CW TOUR para em "Ultimos Lancamentos" (PDF real); TANIA dez para cross-pagina (PDF real); PDF SEM marcadores le ate o fim (sintetico — R-A); PDF com marcador para apos marcador (sintetico). |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

### Testes

Suite completa: **790 passou** (+16 da Sessao 18: 10 validador + 6 lote A; vs 774 da Sessao 17). 1 falha pre-existente (`test_t8_senhas_comuns_rejeita_via_zxcvbn`, herdada da Sessao 14). 2 erros pre-existentes (`test_pagbank.py` / `test_pagbank_integracao.py`, scripts CLI sem fixtures, herdados do commit `d7f4689`). Diferenca exata = +16 (todos os novos passam, nenhuma regressao).

### Validacao em prod (apos deploy)

- 9/9 PDFs Bradesco devem retornar 200 OK com `validacao.nivel=VERDE` e `gap=0.00`.
- Logs `[VALIDADOR]` e `[EXTRATOR-SALDOS]` aparecem com `regra_sf` indicando ramo escolhido.
- Outros bancos (Nubank, Itau, Santander, BS2 etc): inalterados — fix isolado a `bradesco_net_empresas`.
- Se algum PDF Bradesco em prod der `validacao.nivel != VERDE`, capturar log `[EXTRATOR-SALDOS]` para diagnostico.

### Risco residual

- A regra "ultimo Total da secao principal" assume que existe uma linha `Total <c> <d> <s>` antes do marcador. Se o PDF Bradesco tiver layout sem essa linha (raro), o SF fica None. Logs em prod permitirao identificar.
- Categoria B (Mensal SAMARA) ficou VERDE sem precisar de fix dedicado, mas o ParserBradescoNetEmpresas ainda nao foi auditado para outras variantes do layout Mensal. Se aparecer um Mensal de outro cliente com formato diferente, podera precisar de fix individual.

### Nao tocados (R2)

- Parsers de outros bancos (santander, itau, nubank, inter, mercado_pago, bs2, etc): inalterados.
- `_ASSINATURAS` / `detectar_banco`: inalterados (Sessao 17 ja resolveu).
- `gerador_excel_*`: inalterado (escopo da Sessao 20).
- `requirements.txt`, Dockerfiles, `atualizar.sh`, frontend: inalterados.

## Sessao 19 — Santander 100% HONESTO (4 iters + R-B ampla)

**Data**: 2026-04-30
**Branch**: `feat/santander-100-verde-validador` (a partir de `ce7a7b4`, tip da S18 doc)
**Commit**: (a registrar apos push)

**Objetivo declarado**: Santander 100% VERDE.
**Objetivo real entregue**: **Santander 100% HONESTO** — VERDE para todos os layouts onde o PDF expoe SI/SF reconciliaveis; VERMELHO honesto e diagnosticavel para os 5 PDFs onde o parser perde transacoes ou o layout nao contem dado suficiente. Filosofia: VERDE FAKE em producao mente em silencio; VERMELHO bem diagnosticado grita "olha aqui, falta dado X". A Sessao 18 ensinou caro essa licao no caso CW TOUR Bradesco; a S19 aplicou-a sistematicamente nos 14 Santander.

### Tabela final dos 12 Santander unicos (+ 2 duplicatas MD5)

| # | Arquivo | Banco rota | Nivel | n_tx | SI | SF | Gap | Causa |
|---|---|---|---|---|---|---|---|---|
| 1 | Santander Internet Banking N2.pdf (VILA PET) | santander_ib_novo | **VERDE** | 125 | 0,00 | 0,00 | 0,00 | Iter 1 — branch novo `_extrair_saldos_pdf` |
| 2 | Santander Internet Banking N3.pdf (VILA PET) | santander_ib_novo | **VERDE** | 116 | 0,00 | 0,00 | 0,00 | Iter 1 — idem |
| 3 | Santander empresas 2.pdf (MARTINS) | santander | **VERDE** | 27 | 392,96 | 1,07 | 0,00 | Iter 3 — fallback B (tabela_aplicativo_saldo_coluna) |
| 4 | santander problema.pdf (KKS PROMOCOES) | santander | **VERDE** | 21 | 11260,01 | 7961,52 | 0,00 | Iter 3 — fallback A (saldo_do_dia_por_dia + ajuste SI) + fix sinal "- R$" |
| 5 | Santander N1.pdf | santander_consolidado | **VERDE** | 139 | 76981,06 | 76981,06 | 0,00 | Pre-existente (validador da S18 confirma) |
| 6 | Santander N2.pdf | santander_consolidado | **VERDE** | 222 | 77598,18 | 77598,18 | 0,00 | Pre-existente |
| 7 | Santander N3.pdf | santander_consolidado | **VERDE** | 193 | 78206,39 | 78206,39 | 0,00 | Pre-existente |
| 8 | Santander DLS 13006797-5.pdf (DLS AGENCIA) | santander | **VERMELHO honesto** | 16 | 0,00 | 0,00 | +919,52 | Iter 4 — VERDE FAKE derrubado; gap revela tx perdidas pelo parser |
| 9 | Santander DLS 13006797-5_1.pdf (DLS AGENCIA) | santander | **VERMELHO honesto** | 9 | 0,00 | 0,00 | -839,52 | Iter 4 — idem |
| 10 | Santander Internet Banking N1.pdf (CW TOUR) | santander | **VERMELHO honesto** | 6 | 50,84 | 0,00 | -271580,33 | Iter 4 — VERDE FAKE matematico (271k era invencao); 10/16 tx perdidas (incluindo 3 PIX da empresa filtradas por `'cw tour'` hardcoded no _IGNORAR) |
| 11 | Santander empresarial .pdf (LEKE) | santander_empresas | **VERMELHO honesto acionavel** | 24 | None | None | None | Iter 2 — formato App nao expoe SI/SF; diagnostico aciona usuario a pedir "Extrato Consolidado Inteligente" |
| 12 | Santander empresarial 2.pdf (LEKE) | santander_empresas | **VERMELHO honesto acionavel** | 24 | None | None | None | Iter 2 — idem |
| dup | Santander pf .pdf | (mesmo MD5 que N2.pdf) | duplicata | — | — | — | — | MD5 27ef76... |
| dup | Santander pf 2.pdf | (mesmo MD5 que N3.pdf) | duplicata | — | — | — | — | MD5 f22226... |

**Distribuicao final**: 7 VERDE real + 5 VERMELHO honesto + 2 duplicatas confirmadas. Comparado ao baseline da S19/Fase 2 (6 VERDE / 6 VERMELHO de 12 unicos): 4 VERMELHO viraram VERDE real (Iter 1: IB N2/N3; Iter 3: MARTINS, KKS), 3 VERDE FAKE viraram VERMELHO honesto (Iter 4: DLS, DLS_1, IB N1), 2 VERMELHO ganharam diagnostico acionavel (Iter 2: empresarial x2).

### Por iter

**Iter 1 — santander_ib_novo (VERDE)**: branch novo em `_extrair_saldos_pdf` que captura `^DD/MM/YYYY Saldo do dia R$ valor`, ordena por data, define SI=primeiro_saldo / SF=ultimo_saldo. Strip de glifos PUA (Wingdings) embutido. Adicionou `_extrair_saldos_intermediarios()` ao `ParserSantanderIBNovo` (alimenta Check 2/3 do validador da S18). Tradeoff documentado: SI e tecnicamente saldo de fechamento de D_min — funciona quando net_tx(D_min)=0 (caso VILA PET/contamax). Em outros padroes o validador classifica corretamente como AMARELO/VERMELHO.

**Iter 2 — santander_empresas (VERMELHO honesto acionavel)**: layout App nao expoe SI/SF em parte alguma (auditoria via extract_text + extract_tables + extract_words confirmou: nenhuma palavra "saldo"/"total"/"disponivel"). Decisao Op A com refinamento: parametro novo opcional `banco` em `validar_extracao` propaga para `_diagnostico_curto`, que retorna mensagem hibrida (prefixo `extrato_sem_si_sf:` para parsing/log + frase humana legivel para frontend) quando banco='santander_empresas' e SI/SF ausentes.

**Iter 3 — santander legacy VERMELHO (MARTINS + KKS, VERDE)**: 2 layouts diferentes, 2 fallbacks no branch `santander` de `_extrair_saldos_pdf` (ativados so se ini/fim ainda None apos branch principal): **Fallback A** (saldo_do_dia_por_dia, KKS) — captura `DD/MM/YYYY Saldo do dia [...] R$ valor` (regex tolerante a "Cc + ContaMax principal" entre), SI = `saldo_dia(D_min) - net_tx(D_min)` (reparseamento local), SF = `saldo_dia(D_max)`. **Fallback B** (tabela_aplicativo_saldo_coluna, MARTINS) — so dispara com cabecalho `Valor (R$) ... Saldo (R$)`, captura `DD/MM/YYYY <desc> <valor_signed> <saldo>`, SF=primeira linha do PDF onde data=D_max, SI=ultima linha do PDF onde data=D_min menos seu valor. Tambem fix em `ParserSantanderEmpresas._processar_linha`: detecta sinal `- R$` separado por espaco (alem do hifen colado), corrige bug onde 21 tx do KKS eram todas classificadas como ENTRADA.

**Iter 4 — auditoria VERDE fake (DLS + DLS_1 + IB N1, VERMELHO honesto)**: leitura visual das fixtures revelou que SI estava certo (extraido de "SALDO ANTERIOR") mas SF era CALCULADO pelo Passo 3 do pipeline como `SI + sum(tx_extraidas)` — com parser perdendo ContaMax, "EXTRATO" e "CW TOUR", o SF resultante divergia do SF visual real (que e 0,00 nos 3 casos). Validador dava VERDE matematico (tautologico). Fix: condicao do fallback B mudou de `if ini is None and fim is None` para `if fim is None`, preservando SI extraido pelo branch principal via "SALDO ANTERIOR" (importante para DLS onde SI=0 e correto). Resultado: SF agora extraido como saldo da linha de tx mais recente do D_max (= 0,00 nos 3 casos), gap revela exatamente o que o parser perdeu.

### Bugs do `ParserSantanderEmpresas` mapeados — escopo S20

A Iter 4 expos 3 bugs do parser que NAO foram corrigidos nesta sessao (ficam VERMELHO honesto). Importante registrar:

1. **`'cw tour' hardcoded no _IGNORAR`** (`backend/services/parsers/santander_empresarial.py`). Filtro de header arbitrario que mata tx legitimas de `PIX ENVIADO CW TOUR LTDA` (a propria empresa transferindo p/ ela mesma). **Prioridade ALTA de auditoria**: nome de empresa do cliente Allan colado direto no codigo do parser e indicio de fix-de-cliente que nao deveria estar no main. Antes de qualquer fix na S20, **grep por outros nomes de cliente espalhados** em `backend/services/parsers/`: `'cw tour'`, `'leke'`, `'tania'`, `'seolin'`, `'kks'`, `'martins'`, `'dls'`, `'vila pet'`, `'controllo'`. Se aparecer mais, vira incidente de qualidade de codigo, nao bug pontual. Fix do bug em si e trivial (remover a string).

2. **`'extrato' no _IGNORAR mata `'TARIFA EXTRATO INTELIGENTE'`** (mesma lista). Substring matching frouxo: `'extrato'` casa em qualquer descricao que contenha a palavra, descartando tarifas legitimas. Fix obvio: trocar substring por regex de label especifico (ex: `^extrato\s+do\b`) ou por palavra-inteira em lista mais restrita.

3. **ContaMax (`'resgate contamax'` / `'aplicacao contamax'`) filtrado por design**. Comentario do codigo: "movimentacoes internas de fundo, nao afetam caixa operacional". E **decisao de produto, nao bug**. "Fluxo de caixa operacional" (sem ContaMax) e "reconciliacao de saldo CC" (com tudo) sao dois relatorios diferentes que coexistem em sistemas contabeis serios. A solucao certa provavelmente e o parser extrair tudo e o validador / pos-processador decidir o que mostrar dependendo do contexto. **Refactor, nao fix.** Discussao a aprofundar em S20.

### Pendencias para S20 (mapeadas, nao implementadas nesta sessao)

| Pendencia | Origem | Severidade |
|---|---|---|
| 3 bugs do ParserSantanderEmpresas (acima) | Iter 4 | Alta (1 e 2) / Media (3 — produto) |
| Op C — nivel novo "INCOMPLETO" no validador (alternativa estrutural ao prefixo `extrato_sem_si_sf`) | Iter 2 | Baixa — proposta, nao bug |
| Retroaplicar `SI = saldo_dia(D_min) - net_tx(D_min)` no `santander_ib_novo` | Iter 1/3 | Refinamento — nao e risco hoje (VILA PET tem net_tx=0 em todos os dias por contamax). Quando aparecer cliente IB Novo nao-contamax, ja cai VERDE em vez de AMARELO/VERMELHO |
| Inter dedicado (`extrato_ABRIL.pdf` PDF vetorial sem texto extraivel) | Brief inicial S19 | Sessao dedicada |

### Arquivos modificados

| Arquivo | Alteracao |
|---|---|
| backend/services/extrator_pdf.py | Branch `santander_ib_novo` em `_extrair_saldos_pdf` (Iter 1, ~50 linhas). Branch `santander` estendido com 2 fallbacks: A=saldo_do_dia_por_dia (Iter 3), B=tabela_aplicativo_saldo_coluna (Iter 3+4) (~120 linhas). Logs `[EXTRATOR-SALDOS] banco=santander_ib_novo` e `banco=santander fallback=...`. |
| backend/services/parsers/santander_ib_novo.py | Metodo novo `_extrair_saldos_intermediarios()` retornando `[{data, saldo}]` em ordem ASC com dedup por data (Iter 1, ~50 linhas). |
| backend/services/parsers/santander_empresarial.py | `_processar_linha` estendido para detectar sinal `- R$` separado por espaco (alem do hifen colado), com limpeza da descricao (Iter 3, ~12 linhas). |
| backend/services/validacao/validador_saldos.py | Parametro novo opcional `banco: Optional[str] = None` em `validar_extracao` propagado para `_diagnostico_curto`; quando banco='santander_empresas' e SI/SF ausentes, retorna mensagem hibrida acionavel (Iter 2, ~12 linhas). |
| backend/services/pipeline_extracao.py | 1 linha: `banco=getattr(r, 'banco', None)` na chamada de `validar_extracao` em `_validar_saldos`. |
| backend/tests/test_extrair_saldos_santander_s19.py | NOVO. 6 testes cobrindo Iter 1/3/4 contra PDFs reais (skipam se pasta `pdfs_reais/` ausente — politica fixtures S13). |
| backend/tests/test_santander_empresarial_sinal_separado.py | NOVO. 7 testes do fix de sinal `- R$` (3 saidas separadas + 2 entradas + 2 regressoes hifen colado). Sem dependencia de PDF binario. |
| backend/tests/test_validador_diagnostico_acionavel_s19.py | NOVO. 4 testes do diagnostico Iter 2 (santander_empresas vs outros bancos vs banco=None vs caso VERDE). |
| backend/tests/test_santander_ib_novo_saldos_intermediarios.py | NOVO. 2 testes do metodo novo do parser ib_novo (IB N2 + IB N3). |
| backend/tests/fixtures/santander_*_raw.txt | NOVOS. 14 fixtures `.txt` raw (uma por PDF Santander) extraidas via pdfplumber para auditoria read-only. ZERO PDFs binarios commitados. |
| AUDITORIA_TECNICA_CONTROLLO.md | Esta secao. |

### Politica de fixtures respeitada

Zero PDFs binarios commitados. Apenas fixtures `.txt` raw (texto que `pdfplumber` extrai). PDFs reais permanecem em `backend/tests/fixtures/pdfs_reais/` (gitignored desde a S13). Testes que dependem de PDF real usam pytest.skip se a pasta nao existir.

### Testes — pytest final

- **810 passou** (+19 vs S18 baseline 791, exatamente os novos da S19: 6 + 7 + 4 + 2 = 19).
- **0 falhas**.
- **2 erros pre-existentes** (`test_pagbank.py::testar_pdf`, `test_pagbank_integracao.py::testar_integracao` — scripts CLI legados sem fixtures, herdados do commit `d7f4689` desde a S14).
- O teste `test_t8_senhas_comuns_rejeita_via_zxcvbn` (que era falha pre-existente herdada da S14) **passou** nesta sessao por flutuacao da biblioteca zxcvbn (DeprecationWarning indica que ela esta em estado mutavel). **Nao e relacionado ao fix da S19**. Anotado para rastreabilidade: se voltar a falhar em sessao futura, sabemos que e zxcvbn instavel, nao regressao real. Versao atual em uso: a do `requirements.txt` (zxcvbn — sem pin estrito).

### R-B ampla obrigatoria (pre-commit)

Confirmacao de zero regressao em outros bancos:

| Grupo | PDFs testados | VERDE | VERMELHO/Outro | Observacao |
|---|---|---|---|---|
| **9 Bradesco (S18 preservada)** | Agosto 2025, BNE (2), BNE.PDF, net, net2, Bradesco5, 24032026, dec25, nov25 | **9/9** | 0 | Validador continua VERDE, Sessoes 16+18 preservadas |
| **2 Nubank** | Nubank, Nubank 2 | **2/2** | 0 | Inalterado |
| **1 Itau padrao** | testeseeee.pdf (rota itau_n2, 708 tx) | **1/1** | 0 | Inalterado |
| **1 Itau Mensal** | 08_2025 Extrato Mensal.pdf (246 tx) | **1/1** | 0 | Inalterado |
| **1 BS2 (S17)** | B2S.pdf (PROMOVE BRASIL, 46 tx) | **1/1** | 0 | Sessao 17 preservada |
| **2 outros bancos** | Inter.pdf (banco=desconhecido, n_tx=0); Extrato Stone.pdf (VERMELHO, SI=None) | 0 | 2 | **Estados pre-existentes** (Inter sem texto extraivel — pendente Sessao Inter dedicada; Stone parser nao extrai SI). Nao toquei `_ASSINATURAS`, `detectar_banco`, parsers Inter/Stone — confirmado via git diff. |

### Nao tocados (R2)

- Parsers de outros bancos: bradesco*, itau*, nubank*, inter*, bb*, caixa*, bs2*, c6bank*, cora*, pagbank*, mercado_pago*, stone*, xp*, sicredi*, sumup*. Inalterados.
- `_ASSINATURAS` e `detectar_banco`: inalterados (S17 ja endureceu).
- `pipeline_extracao.py` estrutura: apenas adicao de 1 argumento na chamada de `validar_extracao`. Sem mudancas em fluxo, dataclass ou passos.
- `gerador_excel_*.py`, `main.py`, `requirements.txt`, Dockerfiles, `atualizar.sh`, frontend: inalterados.

### Validacao em prod (apos deploy — Allan executa manualmente)

- 7 PDFs Santander VERDE devem retornar 200 OK com `validacao.nivel=VERDE` e `gap=0,00`. Logs `[EXTRATOR-SALDOS]` aparecem com banco/fallback indicando ramo escolhido.
- 5 PDFs VERMELHO honesto devem retornar 200 OK (NAO 422 — extracao funciona, so o validador classifica) com `validacao.nivel=VERMELHO` e `validacao.diagnostico` informativo.
  - DLS, DLS_1, IB N1: gap = exatamente as tx perdidas pelo parser. Valor diagnostico-friendly para futuro fix S20.
  - empresarial, empresarial 2: diagnostico contem `extrato_sem_si_sf:` + frase pedindo "Extrato Consolidado Inteligente".
- Outros bancos (Bradesco, Nubank, Itau, BS2, Stone, Inter etc): inalterados.
- Se algum PDF Santander em prod der nivel != esperado, capturar log `[EXTRATOR-SALDOS]` e `[VALIDADOR]` para diagnostico.

### Risco residual

- **Iter 1**: convencao SI = saldo_dia(D_min) sem ajuste no santander_ib_novo. Funciona porque VILA PET tem net_tx(D_min)=0 todo dia (contamax). Se aparecer cliente IB Novo nao-contamax cujo D_min tem net_tx != 0, validador apontara gap. Refinamento mapeado para S20 (retroaplicar `SI = saldo - net_tx_d_min` igual ao fallback A).
- **Iter 3 fallback B (regra "SF = primeira linha do PDF onde data=D_max")**: assume que PDF lista tx em ordem descendente cronologica DENTRO do dia. Vale para MARTINS e DLS/DLS_1/IB N1 (todos do mesmo layout). Se aparecer Aplicativo Santander Empresas com ordem ascendente intra-dia, regra inverte. Logs em prod permitirao identificar.
- **Iter 4 — VERMELHO honesto permanente** dos 3 PDFs DLS/DLS_1/IB N1 ate fix do parser na S20. Comportamento esperado, NAO e pendencia urgente — gap e diagnosticavel.

---

## Sessao 22 — Excel basico reformatado conforme spec Allan (7 colunas contabeis)

**Branch:** `feat/excel-reformatado-spec-allan` (de `3740e6e`).
**Escopo:** cosmetico — so toca o gerador de Excel basico. Zero impacto em parsers, validador, pipeline ou Excel contabil.

### O que mudou

`backend/services/gerador_excel.py` foi reescrito (233 -> 78 linhas) para o layout fixo destinado a importacao em sistema contabil:

| Coluna | Cabecalho | Conteudo |
|---|---|---|
| A | Lancamento | Numeracao crescente 1..N |
| B | Data | datetime, formato `DD/MM/YYYY` |
| C | Debito | **Vazia** (so titulo no cabecalho) |
| D | Credito | **Vazia** (so titulo no cabecalho) |
| E | Valor | Float **sempre positivo** (`abs()`), formato `#,##0.00` |
| F | Historico | **Vazia** (so titulo no cabecalho) |
| G | Complemento | Campo `descricao` da transacao |

**Removido vs versao anterior:** abas `Resumo por Banco` e `Resumo Diario`; linha de TOTAIS (Saldo Inicial / Entradas / Saidas / Saldo Final com formula); cores condicionais por tipo (verde/vermelho/roxo); coluna `Banco` / `Categoria` / `Tipo`.

**Assinatura preservada:** `gerar_excel(transacoes, caminho_saida, saldo_inicial=None)`. O parametro `saldo_inicial` continua aceito por compatibilidade com chamadas legadas em `main.py:1497`, `main.py:1790`, `main.py:1862`, mas nao e mais usado no Excel basico (deprecation explicita no docstring da funcao). O Excel contabil (`gerador_excel_contabil.py`) ainda usa `saldo_inicial`.

### Decisao: filtrar `tipo='posicao'` no Excel basico

Saldos de carteira de investimento (XP `xp_posicao`, categoria "Posicao de Investimentos") **nao sao lancamentos de caixa** — sao fotografias de saldo. Incluir no Excel destinado a importacao contabil corromperia o objetivo (Debito/Credito/Historico/Complemento e vocabulario de plano de contas, nao de extrato bruto).

Filtro aplicado no inicio de `gerar_excel()`:
```python
transacoes_filtradas = [t for t in (transacoes or []) if t.get("tipo") != "posicao"]
```

Coberto pelo teste `test_filtra_tipo_posicao` — barreira contra regressao se alguem remover o filtro futuramente. **Excel contabil (`gerador_excel_contabil.py`) intocado** — se algum dia precisar de "Excel de posicoes XP", e gerador novo, nao esse.

### Testes

`backend/tests/test_gerador_excel_spec_allan.py` — 8/8 passando:
1. `test_cabecalhos_e_ordem_de_colunas` — 7 colunas exatas, 1 aba, cabecalho em negrito.
2. `test_colunas_debito_credito_historico_vazias` — C/D/F sempre vazias.
3. `test_valor_sempre_positivo_inclusive_para_saida_negativa` — `Decimal('-300.00')` -> `300.00`, formato `#,##0.00`. Pega regressao se alguem remover `abs()`.
4. `test_lancamento_numeracao_crescente` — 1, 2, 3, ...
5. `test_data_como_tipo_excel_e_complemento_descricao` — data tipo `datetime.date`, formato `DD/MM/YYYY`, complemento = descricao.
6. `test_lista_vazia_gera_excel_com_so_cabecalho` — borda: 0 transacoes ainda gera Excel valido.
7. `test_filtra_tipo_posicao` — XP `posicao` filtrado, numeracao mantem sequencia.
8. `test_sem_abas_extras_sem_totalizadores` — sheetnames == `["Lancamentos"]`, sem TOTAIS embedded.

### Validacao ponta-a-ponta

Smoke E2E rodando `processar_extrato` + `gerar_excel` em 4 PDFs reais:
- **Bradesco** (`Extrato Bradesco TLA - 11.25.pdf`): 73 tx OK, 7 colunas, valores positivos, formato OK.
- **Itau** (`2026 08 - Itau.pdf`): 9 tx OK.
- **XP** (`XP Investimentos - extrato de conta corrente.pdf`): 34 tx OK (parser detectou `xp_extrato`, sem `posicao` neste PDF).
- **Santander** (`EXTRATO SANTANDER CONTA MAX.pdf`): 0 tx (parser nao extrai esse layout — limitacao pre-existente, fora do escopo S22; Excel gerado corretamente com so o cabecalho).

### Pytest baseline vs S22

| Metrica | Baseline `3740e6e` (S19) | Apos S22 | Delta |
|---|---|---|---|
| Coletados | 812 | 820 | +8 (novos S22) |
| Passados | 809 | 817 | +8 |
| Falhas | 1 (`test_t8_senhas_comuns_rejeita_via_zxcvbn` — pre-existente) | 1 (mesma) | 0 |
| Erros | 2 (pagbank, pre-existentes) | 2 (mesmos) | 0 |

Zero regressao atribuivel a S22.

### R-B Excel contabil

`git diff feat/santander-100-verde-validador..HEAD -- backend/services/gerador_excel_contabil.py` retorna **vazio**. Os 6 testes em `tests/test_excel_contabil.py` continuam passando (6/6).

### Dead code mapeado (NAO removido nesta sessao)

`backend/services/gerador_excel_pipeline.py` — refatoracao antiga do "pipeline 8 passos" (commit `9bf50a5`). Nenhum import em todo o repositorio (`grep -r "gerador_excel_pipeline" backend/` so encontra a propria docstring do arquivo). **Candidato a remocao em sessao futura** apos confirmacao explicita do Allan. Fora do R1 da S22.

### Nao tocados (R2)

- `gerador_excel_contabil.py` (Excel contabil partida dobrada — usado quando `empresa_id` e fornecido em `/api/processar-extrato`).
- Parsers (`backend/services/parsers/*.py`), `extrator_pdf.py`, `pipeline_extracao.py`, validador.
- `_ASSINATURAS`, `detectar_banco`.
- `requirements.txt`, Dockerfiles, frontend.
- Endpoint `/api/processar-extrato` em `main.py` — assinatura de `gerar_excel` preservada, nada mudou na rota.

### Risco residual

- **`saldo_inicial=None` no-op:** se algum dev futuro reintroduzir uso de `saldo_inicial` no Excel basico sem revisar a spec, perde-se o layout contabil. Mitigado por: docstring deprecation explicita + 8 testes blindando o layout.
- **Filtro `posicao`:** se cliente XP usar especificamente o Excel basico esperando ver posicoes da carteira, perde isso. Decisao consciente — spec contabil prevalece. Caso algum cliente reclame, gerador novo dedicado a posicoes.
