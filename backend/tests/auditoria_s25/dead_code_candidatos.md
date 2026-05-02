# Dead Code Candidatos — GRUPO A (S25 Fase 2)

## Sumario

| Arquivo | linhas | classes | funcs | hits_nome | hits_dyn | hits_nao_py | veredito |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/core/config.py` | 0 | 0 | 0 | 50 | 0 | 48 | INVESTIGAR — referencias em docs/configs |
| `backend/services/parsers/itau_extrato_mensal.py` | 245 | 1 | 0 | 0 | 0 | 0 | DEAD CANDIDATE — validar Fase 3 |
| `backend/services/parsers/parser_generico.py` | 77 | 1 | 0 | 1 | 0 | 1 | INVESTIGAR — referencias em docs/configs |
| `backend/services/parsers/parser_itau_mensal.py` | 54 | 1 | 0 | 3 | 0 | 3 | INVESTIGAR — referencias em docs/configs |
| `backend/services/parsers/parser_stone.py` | 49 | 1 | 0 | 1 | 0 | 1 | INVESTIGAR — algum nome publico tem hits |
| `backend/test_parsers.py` | 163 | 0 | 3 | 5 | 0 | 5 | INVESTIGAR — algum nome publico tem hits |

Arquivos orfaos em AMBOS os recortes (producao e completo).
Validacao via renomear .py.disabled na Fase 3.

> **Nota — versao corrigida apos bug do extrator (S25 Fase 1.b)**
>
> Esta lista foi recategorizada apos a correcao do extrator de imports
> (padrao `from PACOTE import MODULO_FILHO` nao era detectado).
>
> Removidos do GRUPO A nesta correcao:
> - `backend/services/importacao_service.py` — passou a in-degree=1
>   (importado por `routers/importacao.py` via `from services import
>   importacao_service as svc`)
> - `backend/services/contabil/indicadores.py` — passou a in-degree>0
>   (importado por `tests/test_comparador_indicadores_score.py` e
>   referenciado por `score_saude.py`).
>
> Ver `inventario_padroes_import.md` para detalhe do bug e correcao.

## `backend/core/config.py`

- Tamanho: **0 linhas**
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Classes publicas (0): (nenhuma)
- Funcoes publicas (0): (nenhuma)

### Referencias por nome do arquivo `config` (50 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:76` — `| Tailwind CSS | ^4.2.2 | Styling (CSS-first config) |`
- `AUDITORIA_TECNICA_CONTROLLO.md:141` — `│   │   └── config.py                 # 0 linhas — VAZIO (placeholder)`
- `AUDITORIA_TECNICA_CONTROLLO.md:145` — `│   │       ├── config.py             # 40 linhas — engine SQLite/PostgreSQL, get_db`
- `AUDITORIA_TECNICA_CONTROLLO.md:208` — `│   ├── tsconfig.json                 # ES2017, strict`
- `AUDITORIA_TECNICA_CONTROLLO.md:209` — `│   ├── next.config.ts                # Vazio (sem config custom)`
- `AUDITORIA_TECNICA_CONTROLLO.md:210` — `│   ├── postcss.config.mjs            # @tailwindcss/postcss`
- `AUDITORIA_TECNICA_CONTROLLO.md:248` — `└── imports data.database: config (get_db, engine), models`
- `AUDITORIA_TECNICA_CONTROLLO.md:883` — `| Arquivos NAO alterados | models.py, config.py, auth_utils.py, financeiro_service.py, importacao_service.py, insights_engine.py, simulacao_tributaria_service.py, motor_classificacao.py, conciliacao/*...`
- `docker-compose.prod.yml:15` — `command: postgres -c config_file=/etc/postgresql/postgresql.conf`
- `docker-compose.prod.yml:76` — `- caddy_config:/config`
- `docker-compose.prod.yml:89` — `caddy_config:`
- `RELATORIO_AUDITORIA_VISUAL.md:26` — `3. **Cache estático do Next.js (`.next/`)** — `output: standalone` no `next.config.ts` é benigno, mas em modo dev o SWC cacheia CSS gerado pelo Tailwind 4. Sem `rm -rf .next`, mudanças em `globals.css...`
- `RELATORIO_AUDITORIA_VISUAL.md:111` — `| `app/configuracoes/page.tsx` | 45 | — | alto |`
- `RELATORIO_AUDITORIA_VISUAL.md:170` — ``postcss.config.mjs` usa apenas `@tailwindcss/postcss`. Não há `@source` directive em `globals.css`. O Tailwind 4 com PostCSS faz auto-discovery a partir do diretório onde o CSS é importado, escaneand...`
- `RELATORIO_AUDITORIA_VISUAL.md:300` — ``next.config.ts`:`
- `RELATORIO_AUDITORIA_VISUAL.md:515` — `**Observação:** `JetBrains_Mono` já está carregado e configurado como `--font-mono`. Trocar por Geist Mono é opcional — JetBrains Mono é igualmente premium e tem `tabular-nums` ativável. **Pode ser um...`
- `.claude/settings.local.json:255` — `"Bash(git config *)",`
- `backend/main.py:40` — `from data.database.config import get_db, engine, SessionLocal`
- `backend/main.py:157` — `# Regras tributárias (alíquotas configuráveis)`
- `docs/analise-critica-auditoria.md:145` — `- `backend/core/config.py` — arquivo com 0 linhas (placeholder vazio)`
- ... +30 hits adicionais


### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (48 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:76` — `| Tailwind CSS | ^4.2.2 | Styling (CSS-first config) |`
- `AUDITORIA_TECNICA_CONTROLLO.md:141` — `│   │   └── config.py                 # 0 linhas — VAZIO (placeholder)`
- `AUDITORIA_TECNICA_CONTROLLO.md:145` — `│   │       ├── config.py             # 40 linhas — engine SQLite/PostgreSQL, get_db`
- `AUDITORIA_TECNICA_CONTROLLO.md:208` — `│   ├── tsconfig.json                 # ES2017, strict`
- `AUDITORIA_TECNICA_CONTROLLO.md:209` — `│   ├── next.config.ts                # Vazio (sem config custom)`
- `AUDITORIA_TECNICA_CONTROLLO.md:210` — `│   ├── postcss.config.mjs            # @tailwindcss/postcss`
- `AUDITORIA_TECNICA_CONTROLLO.md:248` — `└── imports data.database: config (get_db, engine), models`
- `AUDITORIA_TECNICA_CONTROLLO.md:883` — `| Arquivos NAO alterados | models.py, config.py, auth_utils.py, financeiro_service.py, importacao_service.py, insights_engine.py, simulacao_tributaria_service.py, motor_classificacao.py, conciliacao/*...`
- `docker-compose.prod.yml:15` — `command: postgres -c config_file=/etc/postgresql/postgresql.conf`
- `docker-compose.prod.yml:76` — `- caddy_config:/config`

### Veredito heuristico

**INVESTIGAR — referencias em docs/configs**

---

## `backend/services/parsers/itau_extrato_mensal.py`

- Tamanho: **245 linhas**
- Ultima modificacao: 2026-04-12 20:02:04 -0300
- Classes publicas (1): ['ParserItauExtratoMensal']
- Funcoes publicas (0): (nenhuma)

### Referencias por nome do arquivo `itau_extrato_mensal` (0 hits)

Nenhuma referencia.

### Referencias por nomes publicos

#### `ParserItauExtratoMensal` (0 hits)
  Nenhuma referencia. **Nome morto.**

### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (0 hits)

Nenhuma.

### Veredito heuristico

**DEAD CANDIDATE — validar Fase 3**

---

## `backend/services/parsers/parser_generico.py`

- Tamanho: **77 linhas**
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Classes publicas (1): ['ParserGenerico']
- Funcoes publicas (0): (nenhuma)

### Referencias por nome do arquivo `parser_generico` (1 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:191` — `│       │   │   santander_consolidado.py, parser_generico.py,`

### Referencias por nomes publicos

#### `ParserGenerico` (0 hits)
  Nenhuma referencia. **Nome morto.**

### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (1 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:191` — `│       │   │   santander_consolidado.py, parser_generico.py,`

### Veredito heuristico

**INVESTIGAR — referencias em docs/configs**

---

## `backend/services/parsers/parser_itau_mensal.py`

- Tamanho: **54 linhas**
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Classes publicas (1): ['ParserItauMensal']
- Funcoes publicas (0): (nenhuma)

### Referencias por nome do arquivo `parser_itau_mensal` (3 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:192` — `│       │   │   parser_itau_mensal.py, parser_stone.py, stone_n2.py`
- `docs/diagnostico-parsers.md:227` — `Se o Controllo **não tem parser** para este layout (provável — o briefing só cita `parser_itau_mensal` e `itau_empresas_n2`), criar `parser_itau_empresas_legado.py`. Detecção pela presença do cabeçalh...`
- `docs/diagnostico-parsers.md:248` — `Verificar se `parser_itau_mensal` existe e cobre este layout. Se existir, validar que filtra:`

### Referencias por nomes publicos

#### `ParserItauMensal` (0 hits)
  Nenhuma referencia. **Nome morto.**

### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (3 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:192` — `│       │   │   parser_itau_mensal.py, parser_stone.py, stone_n2.py`
- `docs/diagnostico-parsers.md:227` — `Se o Controllo **não tem parser** para este layout (provável — o briefing só cita `parser_itau_mensal` e `itau_empresas_n2`), criar `parser_itau_empresas_legado.py`. Detecção pela presença do cabeçalh...`
- `docs/diagnostico-parsers.md:248` — `Verificar se `parser_itau_mensal` existe e cobre este layout. Se existir, validar que filtra:`

### Veredito heuristico

**INVESTIGAR — referencias em docs/configs**

---

## `backend/services/parsers/parser_stone.py`

- Tamanho: **49 linhas**
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Classes publicas (1): ['ParserStone']
- Funcoes publicas (0): (nenhuma)

### Referencias por nome do arquivo `parser_stone` (1 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:192` — `│       │   │   parser_itau_mensal.py, parser_stone.py, stone_n2.py`

### Referencias por nomes publicos

#### `ParserStone` (17 hits)
  - `AUDITORIA_TECNICA_CONTROLLO.md:488` — `| Stone | ParserStone | 341 | NAO | SIM (604 tx) |`
  - `backend/services/extrator_pdf.py:862` — `from .parsers.stone import ParserStone`
  - `backend/services/extrator_pdf.py:896` — `'stone': ParserStone,`
  - `backend/tests/test_stone_saldos_s24.py:26` — `from services.parsers.stone import ParserStone`
  - `backend/tests/test_stone_saldos_s24.py:27` — `from services.parsers.stone_n2 import ParserStoneN2`
  - `backend/tests/test_stone_saldos_s24.py:73` — `parser = ParserStone(_path(nome))`
  - `backend/tests/test_stone_saldos_s24.py:90` — `parser = ParserStone(_path(nome))`
  - `backend/tests/test_stone_saldos_s24.py:111` — `parser = ParserStone(_path(nome))`
  - `backend/services/parsers/stone.py:78` — `class ParserStone(ParserBase):`
  - `backend/services/parsers/stone.py:111` — `from .stone_n2 import ParserStoneN2`
  - ... +7 hits adicionais

### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (1 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:192` — `│       │   │   parser_itau_mensal.py, parser_stone.py, stone_n2.py`

### Veredito heuristico

**INVESTIGAR — algum nome publico tem hits**

---

## `backend/test_parsers.py`

- Tamanho: **163 linhas**
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Classes publicas (0): (nenhuma)
- Funcoes publicas (3): ['formatar_brl', 'formatar_brl_linha', 'main']

### Referencias por nome do arquivo `test_parsers` (5 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:139` — `│   ├── test_parsers.py               # 164 linhas — CLI manual, NAO testes automatizados`
- `AUDITORIA_TECNICA_CONTROLLO.md:688` — `**test_parsers.py (164 linhas):** NAO E UM TESTE AUTOMATIZADO. Zero assertions.`
- `.claude/settings.local.json:8` — `"Bash(python test_parsers.py)",`
- `docs/analise-critica-auditoria.md:34` — `- `backend/test_parsers.py` — 164 linhas, ZERO assertions. Não é um teste automatizado.`
- `docs/analise-critica-auditoria.md:630` — `2. **[CRÍTICO]** Zero testes automatizados — `backend/test_parsers.py` tem 0 assertions`

### Referencias por nomes publicos

#### `formatar_brl` (0 hits)
  Nenhuma referencia. **Nome morto.**

#### `formatar_brl_linha` (0 hits)
  Nenhuma referencia. **Nome morto.**

#### `main` (50 hits)
  - `AUDITORIA_TECNICA_CONTROLLO.md:99` — `- **Router pattern:** Endpoints organizados em 12 routers FastAPI + main.py`
  - `AUDITORIA_TECNICA_CONTROLLO.md:137` — `│   ├── main.py                       # 2805 linhas — app principal + 37 endpoints + Excel contabil`
  - `AUDITORIA_TECNICA_CONTROLLO.md:243` — `main.py`
  - `AUDITORIA_TECNICA_CONTROLLO.md:341` — `## Totais: 140 endpoints (44 em main.py + 96 em routers)`
  - `AUDITORIA_TECNICA_CONTROLLO.md:345` — `### Raiz e Health (main.py, sem auth)`
  - `AUDITORIA_TECNICA_CONTROLLO.md:351` — `### Auth (main.py, publicos + auth)`
  - `AUDITORIA_TECNICA_CONTROLLO.md:361` — `### Admin Usuarios (main.py, admin required)`
  - `AUDITORIA_TECNICA_CONTROLLO.md:393` — `### PDF Extrato (main.py, user auth)`
  - `AUDITORIA_TECNICA_CONTROLLO.md:721` — `| 2 | **CRITICO** | Admin de escrit. A pode aprovar/deletar usuarios de B (main.py) | **PENDENTE** (corrigido em master.py, nao em admin) |`
  - `AUDITORIA_TECNICA_CONTROLLO.md:728` — `| 9 | **MEDIO** | Auth duplicado: main.py vs auth_utils.py | **PENDENTE** |`
  - ... +40 hits adicionais

### Possiveis chamadas dinamicas (0 hits)

Nenhuma suspeita.

### Referencias em docs/configs (5 hits)

- `AUDITORIA_TECNICA_CONTROLLO.md:139` — `│   ├── test_parsers.py               # 164 linhas — CLI manual, NAO testes automatizados`
- `AUDITORIA_TECNICA_CONTROLLO.md:688` — `**test_parsers.py (164 linhas):** NAO E UM TESTE AUTOMATIZADO. Zero assertions.`
- `.claude/settings.local.json:8` — `"Bash(python test_parsers.py)",`
- `docs/analise-critica-auditoria.md:34` — `- `backend/test_parsers.py` — 164 linhas, ZERO assertions. Não é um teste automatizado.`
- `docs/analise-critica-auditoria.md:630` — `2. **[CRÍTICO]** Zero testes automatizados — `backend/test_parsers.py` tem 0 assertions`

### Veredito heuristico

**INVESTIGAR — algum nome publico tem hits**

---
