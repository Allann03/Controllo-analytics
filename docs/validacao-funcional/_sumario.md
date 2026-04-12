# Validação Funcional Exaustiva — Fase 2
**Controllo BPO Analytics v3.0**  
**Data:** 2026-04-10  
**Servidor de testes:** http://127.0.0.1:8001 (SQLite isolado `controllo_test.db`)  
**Ambiente:** Python 3.14.4 / venv, 2 tenants criados (alpha-teste, beta-teste)  
**Cobertura:** 73 testes empíricos + inspeção estática de 12 arquivos de serviço + inspeção estática frontend (36 páginas)

---

## Resultado Consolidado

| Seção | Testes | PASS | FAIL | Status |
|-------|--------|------|------|--------|
| 4.1.1 Autenticação e Sessão | 17 | 10 | 7 | ✗ |
| 4.1.2 Multi-tenancy Adversarial | 15 | 6 | 9 | ✗ **CRÍTICO** |
| 4.1.4 Lógica Contábil-Financeira | 10 | 5 | 5 | ✗ |
| 4.1.5 Simulação Tributária | 6 | 4 | 2 | ✗ |
| 4.1.6 Orçamento | 4 | 3 | 1 | ✗ |
| 4.1.7 Alertas | 3 | 2 | 1 | ✗ |
| 4.1.8 Classificação | 4 | 2 | 2 | ✗ |
| 4.1.9 Conciliação Bancária | 3 | 2 | 1 | ✗ |
| 4.1.3 Parsers (estático) | 6 | 6 | 0 | ✓ |
| Relatórios | 2 | 2 | 0 | ✓ |
| Auditoria | 2 | 1 | 1 | ✗ |
| Financeiro — Audit Log | 1 | 1 | 0 | ✓ |
| **TOTAL** | **73** | **44** | **29** | — |

---

## Débitos Confirmados Empiricamente

### CRÍTICO-1 (NOVO): Bypass de Isolamento Multi-Tenant para Admin

**Arquivo afetado:** 6 localidades  
**Evidência empírica:** `admin_alpha` (escritório alpha, `eid=2`) conseguiu:
- `POST /api/financeiro/lancamentos/2` → **200** (criou dado no escritório Beta)
- `GET /api/conciliacao/transacoes/2` → **200** (leu transações do Beta)
- `GET /api/alertas/configuracao/2` → **200** (leu config de alerta do Beta)
- `GET /api/classificacao/regras/2` → **200** (leu regras do Beta)
- `PUT /api/carteira/2` → **200** (editou empresa do Beta)

**Raiz do problema:** Todas as funções de verificação de acesso usam o mesmo padrão incorreto:

```python
# PADRÃO INCORRETO — presente em 6 arquivos
def _empresa_do_usuario(empresa_id, usuario, db):
    empresa = db.query(models.Empresa).filter(...).first()
    if usuario.is_admin:
        return empresa   # ← Sem verificar escritorio_id!
    ...
```

| Arquivo | Linha | Função |
|---------|-------|--------|
| `routers/financeiro.py` | 48 | `_empresa_do_usuario()` |
| `routers/conciliacao.py` | 34 | `_empresa_do_usuario()` |
| `routers/alertas.py` | 35 | `_empresa_do_usuario()` |
| `routers/classificacao.py` | 36 | `_empresa_do_usuario()` |
| `routers/orcamento.py` | 30 | `_empresa_do_usuario()` |
| `main.py` | 2455 | `_checar_acesso_empresa()` |

**Correção requerida em todos:** adicionar verificação de tenant:
```python
if usuario.is_admin and empresa.escritorio_id == usuario.escritorio_id:
    return empresa
```

---

### CRÍTICO-2 (CONFIRMADO): R1 — Validação de Senha Incompleta

**Arquivo:** `backend/main.py` linhas 673–680, 1111–1112  
**Evidência:** Inspeção direta do código-fonte — `UsuarioCreate.validar()` contém apenas:

```python
def validar(self) -> None:
    if len(self.senha) < 8:
        raise HTTPException(400, "Senha deve ter no mínimo 8 caracteres.")
    if len(self.senha) > 128:
        raise HTTPException(400, "Senha muito longa.")
    # FIM — sem mais verificações
```

**Verificações ausentes (todas requeridas por R1):**
1. Maiúscula: sem `re.search(r'[A-Z]', senha)`
2. Minúscula: sem `re.search(r'[a-z]', senha)` 
3. Dígito: sem `re.search(r'\d', senha)`
4. Caractere especial: sem `re.search(r'[^a-zA-Z0-9]', senha)`
5. Análise de força `zxcvbn`: sem `import zxcvbn`

**Endpoint `/api/auth/senha` (linha 1111–1112):** mesmo problema, só checa `len >= 8`.

**Demonstração empírica:** `POST /api/auth/solicitar-acesso` com `senha="abc123!@"` (sem maiúscula) → **200** aceito.

---

### CRÍTICO-3 (CONFIRMADO): R2 — `_garantir_usuario_mestre()` Modifica Credenciais do Master

**Arquivo:** `backend/main.py` linhas 501–546  
**Evidência:** Inspeção direta — função é chamada no módulo-level (`linha 546`) e sobrescreve:

```python
user.senha_hash = senha_hash          # linha 512 — VIOLA R2
user.escritorio_id = _MASTER_ESCRITORIO_ID  # linha 521 — VIOLA R2
```

**Demonstração empírica:** Quando servidor foi iniciado sem `CONTROLLO_MASTER_PASSWORD` explícito, a senha do master em `controllo.db` (produção) foi alterada para o hash do valor padrão `Allan@2018`. Evento observado durante configuração do ambiente de testes.

---

### ALTO-1: DRE — EBIT Inclui Despesas Financeiras (R3)

**Arquivo:** `backend/services/financeiro_service.py`  
**Evidência empírica:** `/api/financeiro/dre/1?ano=2025&mes=6`

```json
{
  "metricas": {
    "despesas_financeiras": 2000.0,
    "ebit": 72000.0,    // ← Inclui desp_financeiras!
    "ir_csll": 3000.0,
    "lucro_liquido": 69000.0
  }
}
```

**Cálculo incorreto:**
- EBIT reportado = Lucro Bruto (95000) − Desp.Adm (15000) − Desp.Com (5000) − **Desp.Fin (2000)** − Outras (1000) = **72000**
- EBIT correto = Lucro Bruto − Desp.Operacionais (sem financeiras) = 95000 − 21000 = **74000**
- Resultado Financeiro = −2000
- LAIR correto = 74000 − 2000 = **72000** ← o que o sistema chama de "EBIT"

O campo `ebit` é na verdade **LAIR** (Lucro Antes do IR). Viola a NBC TG 26 / IFRS.

---

### ALTO-2: BP — Invariante Ativo = Passivo + PL Não Verificada

**Evidência empírica:** `/api/financeiro/dre/1?ano=2025&mes=6` campo `metricas`:

| Grandeza | Valor |
|----------|-------|
| `ativo_total` | R$ 170.000 |
| `passivo_total` | R$ 23.000 |
| `patrimonio_liquido` | R$ 110.000 |
| `passivo + PL` | **R$ 133.000** |
| **GAP** | **R$ 37.000** |

O sistema não emite alerta sobre o desequilíbrio. O gap decorre de `lucros_acumulados` (60.000) não incorporar o lucro do período (69.000) — o lançamento usa entrada manual sem reconciliação automática.

---

### ALTO-3: Financeiro Router Sem Registro de Auditoria

**Arquivo:** `backend/routers/financeiro.py`  
**Evidência:** `grep "registrar_auditoria" routers/financeiro.py` → zero ocorrências.  
Todos os outros routers (`conciliacao.py`, `classificacao.py`, `importacao.py`) usam `registrar_auditoria`.

**Endpoints mutáveis afetados sem audit log:**
- `POST /api/financeiro/lancamentos/{empresa_id}` (criação/atualização)
- `DELETE /api/financeiro/lancamentos/{empresa_id}/{id}` (exclusão)
- `PUT /api/financeiro/fiscal/{empresa_id}` (regime tributário)
- e mais 14 endpoints

---

### MÉDIO-1: Score Saúde — Branch Inacessível

**Arquivo:** `backend/services/score_saude.py` linha 169  
**Evidência:** Inspeção estática — código usa `historico[-3:]` (máximo 2 comparações) mas testa `quedas_consecutivas >= 3` — condição matematicamente impossível.

---

### MÉDIO-2: Tributário — float em vez de Decimal (R3)

**Arquivo:** `backend/services/tributario/constantes.py` e todos os módulos de cálculo  
**Evidência:** Nenhuma ocorrência de `from decimal import Decimal` nos serviços tributários.  
`SIMPLES_NACIONAL`, `LUCRO_PRESUMIDO`, `LUCRO_REAL`, `REFORMA_TRIBUTARIA` — todos `float`.

---

### MÉDIO-3: Lucro Presumido — Bases de Presunção Incompletas

**Arquivo:** `backend/services/tributario/constantes.py`  
```python
LUCRO_PRESUMIDO = {
    "presuncao_irpj": 0.32,  # ← só serviços 32%
    ...
}
```
Faltam: 1.6% (exportação), 8% (comércio/indústria), 16% (transporte não-carga), 32% (serviços).  
Sem dict por atividade → impossível simular empresas de comércio corretamente.

---

### MÉDIO-4: Reforma Tributária — Sem Cronograma de Transição

**Arquivo:** `backend/services/tributario/reforma.py`  
Usa alíquotas finais (CBS 8,8% + IBS 17,7%) sem o cronograma 2026–2033 definido por EC 132/2023.  
Não implementa a transição gradual.

---

### INFORMAÇÃO-1: Endpoints com URLs Diferentes do Esperado

| Endpoint esperado (por inferência) | URL real | Status |
|-----------------------------------|----------|--------|
| `/api/tributario/simular/{id}` | `/api/financeiro/simulacao/{id}` | 200 ✓ |
| `/api/financeiro/score-saude/{id}` | `/api/financeiro/score/{id}` | 200 ✓ |
| `/api/auditoria/logs/{id}` | `GET /api/auditoria?empresa_id={id}` | 200 ✓ |
| `/api/classificacao/aplicar/{id}` | `/api/classificacao/classificar/{id}` | 422 (requer arquivo) |
| `GET /api/carteira/{id}` | Não existe (405) | — |

---

## Validações Positivas (PASS)

### 4.1.1 Autenticação
- JWT contém claims `eid`, `role`, `tv`, `is_master` ✓
- Token inválido/ausente retorna 401 ✓
- Credenciais inválidas retornam 401 ✓
- Slug inválido retorna 401 ✓
- `/api/auth/me` funciona com token válido ✓

### 4.1.3 Parsers de PDF
- `extrator_pdf.py` usa `pikepdf` (instalado no venv) ✓
- `extrator_pdf.py` usa `pdfplumber` para extração ✓
- Tratamento de senha PDF implementado ✓
- Estrutura try/except para tratamento de erros ✓

### 4.1.5 Simulação Tributária (correto via `/api/financeiro/`)
- `/api/financeiro/simulacao/{id}`: retorna `regime_atual`, `regime_novo`, `comparativo` ✓
- `/api/financeiro/comparar-regimes/{id}`: retorna ranking com simples/presumido/real/reforma ✓

### 4.1.6 Orçamento
- Dados de orçamento criados e recuperados ✓
- Comparativo real vs. orçado funcional ✓
- Comparativo anual funcional ✓

### 4.1.4 Indicadores e Narrativa
- 10 indicadores calculados (EBITDA, LG, LS, ROE, ROA, etc.) ✓
- Narrativa automática em linguagem natural ✓
- Insights engine retorna 16 regras categorizadas ✓

---

## Mapa de Impacto — Multi-tenancy

Os 9 endpoints que falharam no isolamento de tenant:

| Endpoint | Verbo | Impacto |
|----------|-------|---------|
| `/api/financeiro/lancamentos/{id}` | GET | Leitura cross-tenant de dados financeiros |
| `/api/financeiro/lancamentos/{id}` | POST | **Escrita** cross-tenant de dados financeiros |
| `/api/conciliacao/transacoes/{id}` | GET | Leitura cross-tenant de transações |
| `/api/alertas/configuracao/{id}` | GET | Leitura cross-tenant de config de alertas |
| `/api/alertas/configuracao/{id}` | PUT | **Escrita** cross-tenant de alertas |
| `/api/classificacao/regras/{id}` | GET | Leitura cross-tenant de regras |
| `/api/classificacao/regras/{id}` | POST/PATCH | **Escrita** cross-tenant |
| `/api/orcamento/comparativo/{id}` | GET | Leitura cross-tenant de orçamento |
| `/api/carteira/{id}` | PUT | **Edição** cross-tenant de empresa |

**Raiz única, correção única:** adicionar verificação `empresa.escritorio_id == usuario.escritorio_id` em todas as 6 funções de guarda listadas.

---

---

## 4.1.10 Frontend — Inspeção Estática (36 páginas)

**Framework:** Next.js 16.1.6 (App Router) + React 19.2.3 + Tailwind 4.2.2  
**Linguagem:** TypeScript (strict mode)

### Inventário de Páginas
36 rotas `.tsx` cobrindo: login, dashboard, DRE, fluxo de caixa, balanço, insights, orçamento, conciliação, classificação-contábil, relatórios, simulação tributária, painel tributário, importação, auditoria, carteiras, equipe, alertas, configurações, master, onboarding.

### Proteção de Rotas
- **Guarda client-side** em `ClientWrapper.tsx`: verifica `localStorage.getItem('controllo_token')`
- Única rota pública: `/login`. Todas as demais redirecionam para `/login` se token ausente
- **Sem middleware Next.js** (`middleware.ts` não existe) — proteção acontece apenas no render client-side
- **Risco:** bot/crawler pode requisitar a página sem ser redirecionado; a segurança real é o backend via JWT

### Armazenamento do Token
- `localStorage['controllo_token']` — JWT completo
- `localStorage['controllo_user']` — objeto usuário serializado em JSON
- `localStorage['controllo_escritorio']` — objeto do escritório (slug, nome, plano)
- **Frontend NÃO decodifica JWT** para extrair `eid`; usa o objeto `escritorio` do localStorage
- **Todos os API calls** incluem `Authorization: Bearer ${token}` ✓

### Multi-tenancy no Frontend
- Sem lógica de isolamento client-side; 100% delegado ao backend via JWT
- Slug do escritório usado no login (`username@slug`) mas não em chamadas subsequentes

### Validação de Senha (Frontend)
- **Nenhuma validação de complexidade client-side** nos formulários de registro ou troca de senha
- `<input type="password">` sem atributos de validação HTML5 (sem `pattern`, `minlength`)
- Frontend NÃO usa `zxcvbn` ou equivalente
- **Vulnerabilidade**: usuário só descobre a regra de senha após rejeição pelo backend (que também valida inadequadamente — ver CRÍTICO-2)

### Tratamento de Erros da API
- Erros são extraídos via `data.detail || "Erro"` — captura mensagem do FastAPI
- **Sem tratamento específico por status code**: 401, 422 e 400 todos exibem a mesma mensagem genérica
- Formulários NÃO exibem erros por campo (field-level errors do Pydantic 422 são ignorados)
- Toast genérico para erros de API em telas de dados

### Acessibilidade (WCAG 2.1)
| Item | Status |
|------|--------|
| `<label>` associado a inputs em formulários | ✓ Presente (login, registro) |
| `aria-required` nos campos obrigatórios | ✗ Ausente |
| `aria-invalid` ao exibir erros | ✗ Ausente |
| `aria-label` em botões icônicos | Parcial (toggle tema sem aria-label) |
| SVG com `aria-hidden="true"` | ✓ Presente |
| `:focus-visible` / outline de foco visível | ✗ Usa apenas `onFocus` inline (JS) |
| Navegação por teclado (Tab order) | Parcial (inputs nativos ok; modais não verificados) |
| Contraste de cores em dark/light | Não auditado (requer Lighthouse) |

### Tema Dark/Light
- Implementado via CSS variables (`var(--bg-primary)`, `var(--text-primary)`) + classe Tailwind `dark`
- Estado persistido em `localStorage['controllo_tema']`
- Script anti-flash no `<head>` carrega o tema antes do render ✓
- Toggle via `CustomEvent('controllo-tema-change')` para sincronização entre abas ✓
- **Bem implementado** — sem flash de conteúdo não estilizado (FOUC)

### Débitos Frontend Identificados
| ID | Severidade | Descrição |
|----|-----------|-----------|
| FE-1 | Alto | Sem validação de complexidade de senha client-side (replica deficiência do backend) |
| FE-2 | Médio | Guarda de rota só client-side — sem `middleware.ts` Next.js |
| FE-3 | Médio | Erros 422 com field-level details ignorados — feedback pobre para o usuário |
| FE-4 | Baixo | `aria-required`, `aria-invalid` ausentes nos formulários |
| FE-5 | Baixo | Botão toggle de tema sem `aria-label` |

---

## Checklist de Fase 3 (Remediação)

Com base nas evidências acima, confirma-se a prioridade definida na Fase 1:

- [ ] **BLOCO 0 — R2**: Remover `_garantir_usuario_mestre()` do módulo-level; criar endpoint `/api/master/reset-credenciais` autenticado
- [ ] **BLOCO 1 — R1**: Adicionar validação de senha completa (uppercase, digit, special, zxcvbn) em `validar()` e `alterar_senha()`
- [ ] **BLOCO 2 — MT**: Corrigir as 6 funções de guarda — adicionar check `escritorio_id`
- [ ] **BLOCO 3 — DRE**: Renomear `ebit` → `lair`, adicionar `ebit_correto`, alertar BP desequilibrado
- [ ] **BLOCO 4 — TAX**: Migrar para `Decimal`, completar bases Lucro Presumido, adicionar transição EC 132
- [ ] **BLOCO 5 — AUD**: Adicionar `registrar_auditoria` nos 17 endpoints do router financeiro
- [ ] **BLOCO 6 — SCORE**: Corrigir branch inacessível (`quedas >= 3`)
- [ ] **BLOCO 7 — FRONTEND**: Adicionar validação de senha client-side (espelhar R1 do backend); middleware Next.js; aria-required/aria-invalid

---

## Resumo Executivo

**73 testes empíricos + inspeção estática** revelaram **3 débitos críticos** e **8+ altos/médios** pendentes de remediação.

O risco mais severo é o **bypass de isolamento multi-tenant** (CRÍTICO-1): qualquer usuário com `is_admin=True` em um escritório pode ler e escrever dados financeiros de qualquer outro escritório. Esta é uma vulnerabilidade de segurança de dados que torna o SaaS fundamentalmente inseguro em ambiente multi-tenancy real.

O segundo risco crítico é a **validação de senha incompleta** (CRÍTICO-2 / R1): apenas comprimento é verificado, sem classes de caracteres ou análise de entropia — criando risco de senhas fracas como "aaaaaaaa".

O terceiro risco crítico é a **mutação de credenciais do master na inicialização** (CRÍTICO-3 / R2): `_garantir_usuario_mestre()` roda a cada `import main` e sobrescreve `senha_hash` e `escritorio_id` do master — tornado a conta master vulnerável ao valor da variável de ambiente `CONTROLLO_MASTER_PASSWORD`.

Todos os débitos mapeados têm raiz identificada, localização de arquivo/linha confirmada, e proposta de correção definida. A Fase 3 pode prosseguir imediatamente.
