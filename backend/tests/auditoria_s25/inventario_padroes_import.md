# Inventario de Padroes de Import — S25 Fase 1 (correcao)

Levantamento via grep (excluindo `__pycache__`, `venv/`, `auditoria_s2*`).
Base: `backend/`.

## Contagem por padrao

| # | Padrao | Ocorrencias | Tratado pelo extrator? |
| --- | --- | --- | --- |
| 1 | `import X` (modulo simples, sem `as`) | 223 | OK (sempre tratado) |
| 2 | `import X as Y` | 10 | OK |
| 3 | `import X.Y` (modulo aninhado) | 3 | OK (resolve para X/Y.py) |
| 5/6/7 | `from X import Y[, Z]` (X sem `.`) | 613 | **PARCIAL — bug detectado**, ver §1 |
| 8 | `from X.Y import Z` | 331 | OK |
| 9/10/11 | `from .` / `from .X` / `from ..X` (relativo) | 119 | OK (level>0 ja tratado) |
| 12 | `importlib.import_module(...)` | 1 (test) — sem uso | **NAO RASTREAVEL — listado §3** |
| 13 | `__import__(...)` | 1 (`main.py:892`) — externo (`sqlalchemy`) | **NAO RASTREAVEL — listado §3** |
| — | Lazy imports (indentados, dentro de funcoes) | 159 | OK (AST percorre todos os nodes) |

## §1 Bug detectado: `from PACOTE import MODULO_FILHO`

Quando `from X import Y` e:
- `X` e um pacote Python (pasta `X/__init__.py`)
- `Y` e um modulo filho (arquivo `X/Y.py`)

O extrator antigo gera apenas `X/__init__.py` como destino. Deve gerar **tambem** `X/Y.py`.

### Ocorrencias confirmadas no projeto

```
backend/routers/financeiro.py:26   from services import financeiro_service as fs
backend/routers/financeiro.py:27   from services import simulacao_tributaria_service as sts
backend/routers/importacao.py:18   from services import importacao_service as svc
backend/main.py:2378               from services import financeiro_service as _fs   (lazy)
backend/main.py:2450               from services import financeiro_service as _fsD  (lazy)
```

Tambem padrao `from data.database import models` (existe `data/database/models.py`)
— **muitas ocorrencias** que tambem se beneficiam da correcao (ver lista no item §2).

## §2 Padroes "from PACOTE import MODULO" detectados via re-grep

Apos corrigir, sao convertidos automaticamente em arestas adicionais:

- `from data.database import models` (em main.py, routers/*, scripts/*) — **multiplas**
- `from services import financeiro_service / simulacao_tributaria_service / importacao_service` — 5
- `from routers.auditoria import registrar_auditoria` — ja resolvido (era `from X.Y import Z` => OK)

## §3 Imports nao-rastreaveis estaticamente (auditoria manual)

Locais onde imports dinamicos aparecem; foram inspecionados e:

- `backend/tests/test_lp_dispatch.py:92` — `import importlib` declarado mas
  **sem uso de `importlib.import_module(...)`** no arquivo (verificado por grep).
  Provavel residuo. Nao gera aresta dinamica.

- `backend/main.py:892` — `db.execute(__import__("sqlalchemy").text("SELECT 1"))`.
  Importa modulo **externo** (sqlalchemy). Nao gera aresta interna.

**Conclusao:** zero imports dinamicos efetivos para modulos internos.
Nenhum risco de "dead code falsamente declarado".

## §4 Correcoes aplicadas em `audit_grafo.py`

1. **Padrao "from PACOTE import MODULO_FILHO"**: para cada `alias.name` em
   `ImportFrom`, tentar resolver `module + "." + alias.name` como arquivo
   ou pacote. Se resolver, adicionar aresta para o modulo filho.
   Mantida a aresta original para o pacote (ambas sao reais).

2. **Robustez no caso `from . import X`** (level>0, module=None):
   resolver `X` como arquivo dentro do diretorio relativo.

3. **Lazy imports**: ja eram capturados por `ast.walk(tree)` (visita
   todos os nodes), mas confirmado via teste ad-hoc.

## §5 Testes ad-hoc

`audit_grafo_test.py` (ou seguir como descrito no protocolo). Casos:

- `services/bar.py` com `from services import foo` → deteccao OK
- `main.py` com `from services.foo import hello` → deteccao OK
- `lazy.py` com import dentro de funcao → deteccao OK
- `from . import X` em pacote relativo → deteccao OK
