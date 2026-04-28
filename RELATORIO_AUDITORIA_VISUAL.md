# RELATÓRIO DE AUDITORIA VISUAL — Fase 0

**Data:** 2026-04-28
**Escopo:** Frontend Next.js do Controllo BPO Analytics
**Status:** Auditoria concluída. Nenhum arquivo foi modificado. Aguardando aprovação para Fase 1.

---

## 0. RESUMO EXECUTIVO

A auditoria identificou os seguintes números brutos:

| Métrica | Total | Distribuição |
|---|---:|---|
| Hex codes (`#xxx`/`#xxxxxx`) | **1.236 ocorrências** | 57 arquivos |
| `rgb()`/`rgba()` | **471 ocorrências** | 36 arquivos |
| `hsl()`/`hsla()` | **1 ocorrência** | 1 arquivo (`dashboard-executivo`) |
| `style={{ ... }}` inline | **1.023 ocorrências** | 47 arquivos |
| `className` com template string dinâmica | **48 arquivos** | maior parte interpola classes existentes (ramos `if/else`), não construção dinâmica de nome de classe |
| Linhas de `globals.css` | **906** | dos quais ~450 são overrides `[class*="bg-slate-X"]` com `!important` |

**Diagnóstico:** o sintoma "mudei a cor mas ficou igual" reportado em tentativas anteriores tem três causas concorrentes confirmadas:

1. **Inline `style={{}}` esmaga classes Tailwind** — 1.023 ocorrências, 47 de 47 arquivos relevantes. Trocar `--bg-primary` em `globals.css` funciona, mas trocar a classe `bg-slate-800` em uma página não funciona quando há `style={{ background: "#1e293b" }}` no mesmo elemento ou em ascendente.
2. **Overrides agressivos em `globals.css` com `!important`** (linhas 230–905) — cerca de 450 linhas de regras como `html.light [class*="bg-slate-8"] { background-color: #FFFFFF !important; }`. Qualquer cor nova que cair no padrão `bg-slate-*` é sobrescrita.
3. **Cache estático do Next.js (`.next/`)** — `output: standalone` no `next.config.ts` é benigno, mas em modo dev o SWC cacheia CSS gerado pelo Tailwind 4. Sem `rm -rf .next`, mudanças em `globals.css` podem não refletir até reiniciar.

A boa notícia: **NÃO há classes Tailwind dinâmicas malformadas** (i.e., zero `bg-${cor}-500`). O único caso (`dashboard-executivo/page.tsx:1`) é um `hsl()` em CSS literal, não uma classe construída dinamicamente. Os 48 arquivos com template string em `className` interpolam **classes pré-existentes via condicional** (`isLight ? "bg-white" : "bg-slate-800"`), o que Tailwind detecta normalmente.

---

## 1. INVENTÁRIO DE CORES HARDCODED (Hex / RGB / HSL)

### 1.1 Hex codes — Top 10 arquivos por densidade

| Arquivo | Ocorrências |
|---|---:|
| `app/insights/page.tsx` | 76 |
| `app/simulacao-tributaria/page.tsx` | 76 |
| `app/painel-tributario/_components/AbaReforma.tsx` | 64 |
| `app/tarefas/page.tsx` | 50 |
| `app/historico-importacoes/page.tsx` | 45 |
| `app/auditoria/page.tsx` | 42 |
| `app/admin/visao-geral/page.tsx` | 42 |
| `app/painel-financeiro/_components/AbaIndicadores.tsx` | 36 |
| `app/page.tsx` (Leitor) | 34 |
| `app/orcamento/page.tsx` | 26 |
| `app/dre/page.tsx` | 32 |
| `app/extrato-lote/page.tsx` | 16 |
| `app/dashboard/page.tsx` | 18 |
| `app/ClientWrapper.tsx` | 16 |

Lista completa: 57 arquivos (incluindo SVGs em `public/` que não são alvo).

### 1.2 Cores recorrentes (paletas hardcoded compartilhadas)

Chart palettes hardcoded localmente em cada página — substituir por `useChartTheme()` (§5.6 do spec):

| Arquivo | Linha | Constante | Conteúdo |
|---|---:|---|---|
| `dashboard/page.tsx` | 76 | `CORES_CATEGORIAS` | (precisa leitura) |
| `dashboard-executivo/page.tsx` | 78 | `CORES_PIE` | `["#102a43","#3b82f6","#06b6d4","#10b981","#f59e0b","#f43f5e","#3b6ea5","#ec4899"]` (8 cores) |
| `sazonalidade/page.tsx` | 439 | `CORES` | `["#3b6ea5","#10b981","#f59e0b","#ef4444","#a78bfa"]` |
| `painel-financeiro/_components/AbaDRE.tsx` | 12 | `DESP_COLORS` | `["#1E4976","#B83030","#92400E","#3b6ea5","#64748B"]` |
| `painel-tributario/_components/AbaCarga.tsx` | 14 | `COLORS` | `["#B83030","#1E4976","#1A6B3C"]` |
| `importar/_components/ModoInicio.tsx` | 44 | `ACCENT_COLORS` | `["#102a43","#3b6ea5","#10b981","#f59e0b","#f43f5e","#a855f7","#06b6d4"]` |

Cores de marca recorrentes em hex (espalhadas):

- `#102a43` (navy 900 institucional) — na maioria dos arquivos.
- `#1e3a5f`, `#3b6ea5`, `#162f52` — variantes navy dispersas.
- `#102a43`, `#0a1f33`, `#243b53` — duplicadas em CSS variables E em hex inline.
- `#10b981` (emerald), `#f43f5e`/`#f87171` (rose/red), `#f59e0b` (amber), `#3b82f6` (blue) — usadas como sucesso/erro/aviso/info dispersas.

### 1.3 RGB/RGBA — Top 10 arquivos

| Arquivo | Ocorrências |
|---|---:|
| `globals.css` | 75 |
| `app/tarefas/page.tsx` | 67 |
| `app/admin/carteiras/page.tsx` | 51 |
| `app/alertas/page.tsx` | 35 |
| `app/orcamento/page.tsx` | 26 |
| `app/page.tsx` (Leitor) | 25 |
| `app/ClientWrapper.tsx` | 20 |
| `app/dre/page.tsx` | 9 |
| `app/conciliacao/page.tsx` | 13 |

A maior parte das ocorrências em CSS são tons de overlay / glassmorphism (ex.: `rgba(79,106,255,0.14)`).

### 1.4 HSL

Apenas 1 ocorrência: `dashboard-executivo/page.tsx:1` — verificar se é uma cor isolada ou uma definição de gradiente. **Não é bloqueante.**

---

## 2. INVENTÁRIO DE STYLES INLINE (`style={{}}`)

**Total: 1.023 ocorrências em 47 arquivos.** Este é o maior vetor de "mudei mas ficou igual" do projeto.

### 2.1 Arquivos críticos (>40 ocorrências)

| Arquivo | Ocorrências | Linhas no arquivo | Densidade |
|---|---:|---:|---:|
| `app/tarefas/page.tsx` | 106 | — | crítico |
| `app/page.tsx` (Leitor) | **88** | 1.002 | crítico |
| `app/agenda/page.tsx` | 79 | — | crítico |
| `app/admin/carteiras/page.tsx` | 74 | — | crítico |
| `app/orcamento/page.tsx` | 59 | — | alto |
| `app/carteiras/page.tsx` | 46 | — | alto |
| `app/configuracoes/page.tsx` | 45 | — | alto |
| `app/extrato-lote/page.tsx` | 43 | — | alto |
| `app/ClientWrapper.tsx` | **42** | 842 | alto (shell) |
| `app/dre/page.tsx` | 41 | — | alto |
| `app/importar/_components/ModoInicio.tsx` | 33 | — | médio |

**Padrão dominante observado em `ClientWrapper.tsx`:**

```tsx
style={{
  color: active ? "var(--nav-active-text)" : "var(--nav-text)",
  background: active ? "var(--nav-active-bg)" : "transparent",
  border: `1px solid ${active ? "var(--nav-active-border)" : "transparent"}`,
}}
```

Boa notícia: muitos inline styles **já consomem CSS variables** — esses não atrapalham a Fase 1 (mudar a variável é suficiente).

Má notícia: vários inline styles têm **hex hardcoded ou rgba()**:
- `ClientWrapper.tsx:240` — `style={{ background: "#1e3a5f", color: "white" }}`
- `ClientWrapper.tsx:248` — `style={{ color: "#102a43" }}`
- `ClientWrapper.tsx:272` — `style={{ color: empresaSelecionada ? "#3b6ea5" : "#64748b" }}`
- `ClientWrapper.tsx:309` — `style={{ color: empresaSelecionada ? "#3b6ea5" : undefined }}`
- `ClientWrapper.tsx:475` — `style={{ background: "rgba(2,4,16,0.88)", borderBottom: "1px solid rgba(79,106,255,0.14)", ... }}` (header)
- `ClientWrapper.tsx:484` — `style={{ color: "#64748b", border: "1px solid rgba(79,106,255,0.15)" }}` (toggle)
- `ClientWrapper.tsx:537` — ring color do avatar
- `ClientWrapper.tsx:541-557` — backgrounds e borders dos pills de role com `rgba(79,106,255,0.12)`, `rgba(234,179,8,0.12)`, etc.
- `ClientWrapper.tsx:154,162` — ThemeToggle com `background: "#102a43"` hardcoded.

Em `app/page.tsx` (estado de erro, linha 619-643):

```tsx
style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}
// e botão:
className="px-5 py-2.5 bg-[#1e3a5f] hover:bg-[#162f52] text-white rounded-xl"
```

**Implicação para Fases 1-5:** quando trocarmos um token CSS, os inline styles que usam `var(--token)` migram automaticamente. Os que têm hex inline precisam ser editados arquivo a arquivo na Fase 5.

---

## 3. INVENTÁRIO DE CLASSES TAILWIND DINÂMICAS

### 3.1 Verificação de risco

Padrão buscado: `` className={`bg-${variable}` `` ou `className={"bg-" + cor}` (Tailwind v4 não detecta).

**Resultado: 0 ocorrências** com construção de nome de classe a partir de variável.

Os 48 arquivos com template string em className todos seguem o padrão **seguro**:

```tsx
className={`flex items-center ${active ? "bg-blue-500 text-white" : "bg-slate-800 text-slate-400"}`}
```

Tailwind v4 detecta `bg-blue-500` e `bg-slate-800` perfeitamente — nada a corrigir aqui.

### 3.2 Tailwind 4 source detection

`postcss.config.mjs` usa apenas `@tailwindcss/postcss`. Não há `@source` directive em `globals.css`. O Tailwind 4 com PostCSS faz auto-discovery a partir do diretório onde o CSS é importado, escaneando todo o projeto. **Isto é OK** — todas as classes Tailwind usadas serão detectadas.

---

## 4. SISTEMA DE TOKENS ATUAL EM `globals.css`

O arquivo tem 906 linhas. Estrutura atual:

### 4.1 Tokens definidos no `@theme` (Tailwind 4)

```
--color-navy-{50..950}    → produzem classes `bg-navy-X`, `text-navy-X`, etc.
--color-surface-{50..300} → produzem classes `bg-surface-X`
--font-jakarta            → mapeia para `font-jakarta`
--font-mono               → mapeia para `font-mono`
```

### 4.2 Tokens definidos em `:root` (CSS variables tradicionais)

Brand:
```
--brand-primary, --brand-primary-hover, --brand-primary-light,
--brand-primary-dark, --brand-primary-muted, --brand-accent
```

Surfaces:
```
--bg-primary, --bg-secondary, --bg-card, --bg-card-hover
```

Borders:
```
--border, --border-accent
```

Text:
```
--text-primary, --text-secondary, --text-muted
```

Accents:
```
--accent-indigo, --accent-blue, --accent-emerald, --accent-rose, --accent-amber
```

Gradients:
```
--gradient-primary, --gradient-success, --gradient-danger
```

Sidebar (escopo separado, ~21 tokens):
```
--sidebar-bg, --sidebar-border, --sidebar-shadow,
--nav-text, --nav-text-hover, --nav-active-text,
--nav-active-bg, --nav-active-border, --nav-active-shadow,
--nav-hover-bg, --nav-icon-active-bg, --nav-icon-active-shadow,
--sidebar-footer-border, --sidebar-profile-bg, --sidebar-profile-border,
--sidebar-profile-shadow, --nav-indicator, --nav-indicator-glow
```

Geo (decorativo):
```
--geo-dots-opacity, --geo-ring-opacity
```

### 4.3 Quem é consumido por quem

- **`--bg-primary`, `--bg-card`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border`** — consumidos em ~30+ arquivos via `style={{...}}` e em CSS via `var()`. **Renomeá-los quebraria muita coisa.** Recomendação: na Fase 1, **manter os nomes existentes como aliases** apontando para os novos tokens. Ex.: `--bg-primary: var(--bg-canvas);`.
- **`--brand-primary`, `--brand-accent`, `--accent-indigo` etc.** — consumidos parcialmente. Aliasáveis sem risco.
- **`--sidebar-*` e `--nav-*`** — consumidos apenas em `ClientWrapper.tsx`. Podemos redefinir junto com o redesign do shell na Fase 4.
- **`--gradient-primary`, `--gradient-success`, `--gradient-danger`** — usados em `.gradient-text` (globals.css:195) e provavelmente em algumas páginas. Como o spec da §4.1 elimina gradientes de marca decorativos, **podemos zerar essas variáveis** para `currentColor` e remover usos na Fase 5 caso a caso (ou mantê-las como cores sólidas planas).

### 4.4 Definidos mas NÃO consumidos

Verificação superficial — alguns candidatos (a ser confirmado):
- `--brand-primary-muted` (definido `:root` linha 46) — sem consumidor direto encontrado.
- `--accent-blue`, `--accent-rose` — pouco usados, a maioria das páginas hardcoda os hex equivalentes.

### 4.5 Consumidos mas NÃO definidos

Não foram detectados — todos os `var(--xxx)` encontrados têm definição no `:root` ou em `html.light`.

### 4.6 Classes CSS utilitárias custom (precisam decisão)

Definidas em `globals.css`, consumidas espalhadamente (provavelmente em mais de 5 páginas cada):

- `.glass-card` (linha 203)
- `.gradient-text` (linha 195) — depende de `--gradient-primary`
- `.card-premium`, `.card-premium:hover` (450, 457)
- `.kpi-emerald/blue/violet/rose/amber/indigo` (463-468, redefinida em 833)
- `.section-title` (473)
- `.chart-container`, `.chart-header` (484, 490)
- `.badge`, `.badge-indigo/emerald/rose/amber/violet` (502-543)
- `.table-premium thead/tbody/tr/th` (548-582)
- `.page-header` (587, redefinida em 592)
- `.pdf-page-bg`, `.pdf-upload-card`, `.pdf-select-btn`, `.pdf-chart-bg`, `.pdf-resumo-card-{green,red,indigo}` (600-682)
- `.skeleton`, `.animate-pulse-slow`, `.page-enter`, `.animate-fade-in-up`
- `.alerta-warning-banner`, `.alerta-warning-text`, `.alerta-ok-banner`, `.alerta-ok-text` (838-847)
- `.feedback-msg-ok`, `.feedback-msg-erro` (846-847)
- `.section-card-alertas` (850)
- `.upload-zone` + variantes (859-865)
- `.greeting-name`, `.logo-box` (873, 880)

**Recomendação:** *manter* essas classes (não deletar) e *redefinir suas regras* na Fase 1 para usar os novos tokens. Isso evita quebrar o JSX existente.

### 4.7 Overrides agressivos com `!important` (CRÍTICO)

`globals.css:230-799` — **cerca de 450 linhas de overrides `[class*="bg-slate-X"]`, `[class*="text-slate-X"]`, etc., todos com `!important`.**

Exemplo (linhas 246-249):
```css
html.light [class*="bg-slate-8"],
html.light [class*="bg-slate-7"] {
  background-color: #FFFFFF !important;
}
```

Estes existem para "consertar" tema claro genericamente quando o JSX foi escrito assumindo tema escuro (Tailwind class `bg-slate-800` originalmente "fundo escuro"). **Eles vão atropelar quase qualquer cor nova que dependa das mesmas classes Tailwind.**

**Decisão crítica para a Fase 1:**

- **Opção A (recomendada):** **deletar todo o bloco linhas 230-905** (mantendo apenas o reset, tipografia, scrollbar, animations e classes utilitárias custom da §4.6). O sistema novo de tokens da §4.1 do spec deve funcionar sem necessidade desses overrides "all caps". As páginas que usam `bg-slate-800` direto serão tratadas na Fase 5 (substituídas por `bg-surface` / token novo).
- **Opção B (segura mas suja):** manter os overrides mas adicionar especificidade ainda maior nas regras novas. Resulta em CSS cada vez mais frágil.

⚠ **PARADA OBRIGATÓRIA aqui** — esta decisão precisa aprovação do usuário antes da Fase 1.

---

## 5. CACHE DO NEXT.JS

`next.config.ts`:
```ts
const nextConfig: NextConfig = { output: "standalone" };
```

`output: "standalone"` afeta apenas build de produção, não dev. Em dev, o Next.js 16 + Tailwind 4 + PostCSS gera CSS no `.next/static/css/`. Mudanças em `globals.css` em geral hot-reload corretamente, mas **trocas de `@theme` (Tailwind v4) podem falhar em hot-reload e exigir restart**.

**Procedimento obrigatório após cada fase:**

```bash
cd frontend
rm -rf .next
npm run dev
```

Em Windows (bash/git-bash):
```bash
rm -rf frontend/.next && npm --prefix frontend run dev
```

Hard refresh do navegador: `Ctrl+Shift+R` (ou `Cmd+Shift+R` no Mac).

---

## 6. CONFLITOS POTENCIAIS

### 6.1 [CRÍTICO] Overrides `!important` em `globals.css:230-905`

Já tratado em §4.7 acima. Decisão pendente.

### 6.2 [CRÍTICO] `GlobeBackground` no `<main>` de toda a app

`ClientWrapper.tsx:832` renderiza `<GlobeBackground />` no `<main>` — afeta **TODAS as páginas autenticadas**, não só a home. O componente desenha um globo orbital animado em canvas com `position: absolute; inset: 0; z-index: 0`.

O spec (§5.1) diz: *"Remover qualquer pattern de globo (ou manter APENAS no estado vazio do Leitor de Extrato como elemento decorativo intencional — perguntar antes)."*

**OPÇÕES:**

- **A)** Remover `<GlobeBackground />` do `ClientWrapper.tsx:832` completamente. Manter o componente no repositório (não deletar arquivo) para reaproveitamento eventual.
- **B)** Mover para o `<main>` apenas em `app/page.tsx` (Leitor de Extrato), em estado `idle` (sem PDF carregado).
- **C)** Manter como está.

**RECOMENDAÇÃO: A.** O globo é decorativo, dá ruído visual em telas densas (DRE, tabelas, gráficos), e contradiz a estética "refined banking-tech editorial" do spec. Se o usuário quiser preservá-lo, B é o melhor compromisso (presença intencional, contexto único).

⚠ **PARADA OBRIGATÓRIA** — preciso da decisão do usuário.

### 6.3 [MÉDIO] `useChartTheme()` já existe — atualizar não recriar

`components/useChartTheme.ts:8-42` retorna objeto com `gridStroke`, `tickFill`, `axisStroke`, `lineStroke`, `tooltipStyle`, `tooltipLabelStyle`, `tooltipItemStyle`. Não retorna `colors`.

Spec §5.6 quer que o hook retorne `colors: ['var(--chart-1)', ...]` e `grid`, `axis`, `tooltip`.

**Plano:** **adicionar** as novas propriedades sem remover as antigas (que estão em uso em vários lugares: `dashboard-executivo`, `page.tsx`, etc.). Os consumidores existentes continuam funcionando; a Fase 5 migrará uso a uso.

### 6.4 [MÉDIO] Gradientes de marca (`--gradient-primary`, etc.)

Definidos em `globals.css:72-74`. Consumidos por `.gradient-text` e talvez página de login. O spec (§4.1, §5.6) elimina gradientes decorativos de marca.

**RECOMENDAÇÃO:** redefinir esses tokens para cor sólida (`linear-gradient(0deg, var(--accent), var(--accent))`) — mantém o token vivo, mas visualmente vira uma cor plana. Quem usa `.gradient-text` continua compilando; só não tem mais gradient.

### 6.5 [MÉDIO] Layout dark padrão é forçado por script

`layout.tsx:36`:
```js
var t=localStorage.getItem('controllo_tema')||'dark';document.documentElement.classList.add(t);
```

Adiciona `class="dark"` (ou `"light"`) ao `<html>`. O CSS atual usa `@custom-variant dark (:is(html:not(.light)) &)`, então o **dark mode é o "default" sem precisar de class explícita** — mas o script adiciona `class="dark"` mesmo assim. **Não é um conflito**, mas o spec menciona usar `.dark` ou `[data-theme="dark"]`. **Decisão: manter `html:not(.light)` como dark mode + manter `html.light` como light mode** (consistente com o que já está no script e em todo CSS).

### 6.6 [BAIXO] Conflito de tokens existentes vs novos

O spec novo define:
- `--bg-canvas`, `--bg-surface`, `--bg-elevated`, `--bg-overlay`, `--bg-inset`
- `--text-primary`, `--text-secondary`, `--text-tertiary`, `--text-disabled`, `--text-inverse`

Sistema atual:
- `--bg-primary`, `--bg-secondary`, `--bg-card`, `--bg-card-hover`
- `--text-primary`, `--text-secondary`, `--text-muted`

**Não dá para fazer rename direto** porque ~30 arquivos consomem os nomes antigos. **Solução proposta:** definir os tokens novos em `globals.css`, e adicionar **aliases** dos antigos:

```css
/* Aliases retro-compat — pontes entre tokens antigos e novo design system */
--bg-primary:    var(--bg-canvas);
--bg-secondary:  var(--bg-elevated);
--bg-card:       var(--bg-surface);
--bg-card-hover: var(--bg-elevated);
--text-muted:    var(--text-tertiary);
--border:        var(--border-default);
--border-accent: var(--accent-border);
```

Assim: 0 quebras imediatas + Fase 5 migra consumidores para os nomes novos página a página + aliases são removidos no final.

### 6.7 [BAIXO] `EditableAvatar`, `UserAvatar`, `GraficoComNome`

Componentes auxiliares com hex/rgb hardcoded (avatares têm paleta de fundo determinística). **Não é problema visual de prioridade alta** — paleta de avatares pode ser preservada (cores deterministicas para iniciais). Tratar na Fase 3 como redefinição via tokens.

---

## 7. SIDEBAR — TRUNCAMENTO E DECISÃO NECESSÁRIA

### 7.1 Medições

`ClientWrapper.tsx:600-608`:
- **Largura sidebar expandida:** `width: sidebarAberta ? 224 : 56` → **224px expandida.**
- **Largura sidebar colapsada:** **56px**.

`ClientWrapper.tsx:65-73` (NavLink):
- **`maxWidth` do label:** **155px**.
- Padding interno do nav: `paddingLeft/Right: collapsed ? 8 : 12` → **12px** cada lado quando expandida.
- Padding interno do `<Link>`: `padding: collapsed ? "10px 10px" : "10px 12px"` → **12px** cada lado.
- Gap entre ícone e label: 12px.
- Ícone: 22px largura.

**Cálculo do espaço disponível para o label:**
```
224 (sidebar) − 24 (nav padding) − 24 (link padding) − 22 (ícone) − 12 (gap) = 142px
```

A `maxWidth: 155px` é otimista — só "cabe" quando a barra de scroll some, e ainda assim o label corta.

### 7.2 Labels do menu (mais longos primeiro)

| Label | Caracteres | Largura aproximada @ Plus Jakarta 14px (Tailwind text-sm) regular |
|---|---:|---:|
| Histórico de Importações | 24 | ~178px |
| Orçamento vs. Realizado | 23 | ~170px |
| Classificação Contábil | 22 | ~163px |
| Visão geral da equipe | 21 | ~155px |
| Conciliação Bancária | 20 | ~148px |
| Insights Financeiros | 20 | ~148px |
| Simulação Tributária | 20 | ~148px |
| Dashboard Executivo | 19 | ~140px |
| Balanço Patrimonial | 19 | ~140px |
| Central de Controle | 19 | ~140px |
| Alertas por E-mail | 18 | ~133px |
| Análise Tributária | 18 | ~133px |
| Painel Financeiro | 17 | ~125px |
| Bradesco/Empresas... | varia | — |

Conclusão: ~7 dos 25 itens **truncam visivelmente** com `maxWidth: 155px`, e mais 4 estão no limite.

### 7.3 Opções

**Opção A — Ampliar sidebar para 256px (w-64) + ajustar `maxWidth: 192px`:**

- ✅ Cabem todos os labels exceto "Histórico de Importações" e "Orçamento vs. Realizado" (precisariam ainda de truncamento ou trim).
- ✅ Padrão da indústria (Mercury, Linear, Stripe usam 240–264px).
- ✅ Sem mudança de copy.
- ❌ +32px lateral consumindo área de conteúdo.
- ❌ "Histórico de Importações" continua no limite, ainda truncaria em alguns zooms.

**Opção B — Ampliar para 240px (w-60) + trim de 2 labels:**

- ✅ Equilíbrio melhor.
- ✅ Cabem 22 dos 25 labels.
- ❌ Precisa trim de copy:
  - "Histórico de Importações" → "Histórico" *(perde precisão)*
  - "Orçamento vs. Realizado" → "Orçamento" *(perde semântica do "vs Realizado")*
  - "Classificação Contábil" → "Classificação" *(aceitável)*
- ⚠ Spec §1 proibe alterar conteúdo textual sem autorização específica desta spec — esta é justamente uma das exceções autorizadas pela Fase 0.

**Opção C — Ampliar para 256px + manter labels integrais:**

- ✅ Labels todos legíveis sem trim.
- ✅ Sem alteração de copy.
- ❌ Sidebar mais "pesada" visualmente (mais 14% que o atual).

**RECOMENDAÇÃO: Opção C — sidebar 256px (w-64), `maxWidth: 200px`, todos os labels intactos.**

Justificativa:
1. O produto tem **25+ itens de menu**; legibilidade é prioridade máxima na sidebar.
2. Alterar copy de itens já memorizados pelo usuário tem custo cognitivo. "Histórico de Importações" é um termo do glossário do produto — encurtar para "Histórico" perde precisão.
3. Mercury usa 256px. Linear usa 240px. 256px é editorial e não dramático.
4. A área de conteúdo continua com >1024px em monitores 1280px (mínimo do spec §7).

⚠ **PARADA OBRIGATÓRIA** — precisa aprovação do usuário entre A, B ou C.

---

## 8. PERGUNTAS ESPECÍFICAS PARA O USUÁRIO

Resumindo as 4 decisões pendentes que bloqueiam a Fase 1:

### Q1. Overrides `!important` em `globals.css:230-905`

**Pergunta:** posso deletar todo o bloco de overrides `[class*="bg-slate-X"]` / `[class*="text-slate-X"]` (linhas 230 a ~799) ao redefinir o design system?

- ☐ **A)** Sim, deletar tudo (~450 linhas). Os ajustes de tema claro/escuro serão refeitos via tokens.
- ☐ **B)** Não, manter. Adicionar especificidade nas regras novas (CSS mais frágil).

### Q2. `GlobeBackground` (globo decorativo no fundo de TODA a app)

**Pergunta:** o que fazer com `<GlobeBackground />` em `ClientWrapper.tsx:832`?

- ☐ **A)** Remover do shell completamente (manter o arquivo do componente para usos futuros).
- ☐ **B)** Mover só para a tela inicial do Leitor de Extrato em estado idle.
- ☐ **C)** Manter como está.

### Q3. Largura da sidebar

**Pergunta:** qual estratégia para resolver truncamento?

- ☐ **A)** 256px + `maxWidth label: 192px` + trim de "Histórico de Importações" e "Orçamento vs. Realizado".
- ☐ **B)** 240px + trim de 3 labels.
- ☐ **C)** 256px + `maxWidth label: 200px`, sem trim (RECOMENDADO).

### Q4. Instalar pacote `geist` para Geist Mono

O spec §4.2 autoriza instalação de `geist`. Confirmar?

- ☐ **A)** Sim, rodar `npm install geist` no frontend.
- ☐ **B)** Não — manter `JetBrains_Mono` (já carregado via `next/font/google` em `layout.tsx:14`).

**Observação:** `JetBrains_Mono` já está carregado e configurado como `--font-mono`. Trocar por Geist Mono é opcional — JetBrains Mono é igualmente premium e tem `tabular-nums` ativável. **Pode ser uma economia razoável manter JetBrains.**

---

## 9. ESTIMATIVA DE ESFORÇO POR FASE (PÓS-APROVAÇÃO)

| Fase | Arquivos tocados | Risco | Tempo estimado |
|---|---:|---|---|
| Fase 1 — `globals.css` redesign | 1 | médio | 1 sessão |
| Fase 2 — Fontes + `layout.tsx` | 1-2 | baixo | 30 min |
| Fase 3 — `components/ui/index.tsx` | 1 | médio (consumido por ~muitos) | 1 sessão |
| Fase 4 — `ClientWrapper.tsx` (843 linhas) | 1 | **alto** (é o shell) | 2 sessões com 3 commits parciais |
| Fase 5 — Páginas individuais | ~28 | médio (1 por vez) | múltiplas sessões |
| Fase 6 — Toast + Error states | 2 | baixo | 1 sessão |
| Fase 7 — Verificação final | — | baixo | 1 sessão |

---

## 10. RECOMENDAÇÕES FINAIS DA AUDITORIA

1. **Prioridade absoluta:** decidir Q1 (overrides `!important`) e Q2 (GlobeBackground) — sem isso, Fase 1 não pode prosseguir limpa.
2. **Aliases retrocompat:** adicionar na Fase 1 (§6.6) para minimizar quebras.
3. **Recharts:** mapear semanticamente cores (receita = chart-1, lucro = chart-2, etc.) — spec §5.6 já define isso, executar à risca na Fase 5.
4. **Inline styles com hex hardcoded em `ClientWrapper.tsx`:** ~16 ocorrências (linhas 154, 162, 240, 248, 272, 309, 475, 484, 537, 541-557). Trocar por `var(--accent)` etc. na Fase 4.
5. **Estado de erro do Leitor (`app/page.tsx:619-643`):** atualmente é só um card vermelho com `resultado?.erro` raw. A Fase 6 reescreve seguindo §6.2 do spec — adicionando microcopy, sugestão e detalhes técnicos colapsáveis.
6. **`dashboard-executivo/page.tsx:78` (`CORES_PIE`)** — 8 cores hardcoded. Reduzir para 6 da paleta `--chart-1..6` na Fase 5.

---

## 11. AGUARDANDO

**Aguardando decisão do usuário em Q1, Q2, Q3 e Q4 antes de iniciar Fase 1.**

Após aprovação, próximos passos:

1. Commit do relatório (caso o usuário queira preservá-lo no git).
2. Iniciar Fase 1 — redesign de `globals.css`.
3. Aplicar protocolo de teste 5-rounds (§8 do spec).
4. Continuar fases subsequentes conforme §10 do spec.
