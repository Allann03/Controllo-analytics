# Dead Code Validado — S25 Fase 3 (LOTE)

Validacao via renomeacao temporaria + pytest baseline.

Baseline aceitavel: 912-913 passed / 0-1 failed (zxcvbn) / 1 skipped / 2 errors

## Sumario

| Indice | Arquivo | PRE-CHECK | Acao | pos-disabled | pos-revert | Veredito |
| --- | --- | --- | --- | --- | --- | --- |
| 1/6 | `backend/core/config.py` | LIMPO (referencias todas falsos positivos genericos em docs) | VALIDADO | OK | - | DEAD CONFIRMED |
| 2/6 | `backend/services/parsers/itau_extrato_mensal.py` | LIMPO | VALIDADO | OK | OK | DEAD CONFIRMED |
| 3/6 | `backend/services/parsers/parser_generico.py` | LIMPO | VALIDADO | OK | OK | DEAD CONFIRMED |
| 4/6 | `backend/services/parsers/parser_itau_mensal.py` | LIMPO | VALIDADO | OK | OK | DEAD CONFIRMED |
| 5/6 | `backend/services/parsers/parser_stone.py` | LIMPO (manual, ignorando colisao classe) | VALIDADO | OK | OK | DEAD CONFIRMED |
| 6/6 | `backend/test_parsers.py` | LIMPO | VALIDADO | OK | OK | DEAD CONFIRMED |

## Detalhes por Arquivo

### [1/6] `backend/core/config.py` — DEAD CONFIRMED
- **PRE-CHECK**: LIMPO (referencias todas falsos positivos genericos em docs)
- pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 308.18s`
- pytest pos-revert: `(implicita via pytest do [2/6] que foi interrompido)`

### [2/6] `backend/services/parsers/itau_extrato_mensal.py` — DEAD CONFIRMED
- **PRE-CHECK**: LIMPO
  - Greps:
    - nome_arquivo `itau_extrato_mensal`: 0 hits (0 nao-triviais)
    - classe `ParserItauExtratoMensal`: 0 hits (0 nao-triviais)
    - extrator_pdf — classes referenciadas: 0
- pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 305.19s (0:05:05)`
- pytest pos-revert: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 309.35s (0:05:09)`

### [3/6] `backend/services/parsers/parser_generico.py` — DEAD CONFIRMED
- **PRE-CHECK**: LIMPO
  - Greps:
    - nome_arquivo `parser_generico`: 1 hits (0 nao-triviais)
    - classe `ParserGenerico`: 0 hits (0 nao-triviais)
    - extrator_pdf — classes referenciadas: 0
- pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 305.06s (0:05:05)`
- pytest pos-revert: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 302.97s (0:05:02)`

### [4/6] `backend/services/parsers/parser_itau_mensal.py` — DEAD CONFIRMED
- **PRE-CHECK**: LIMPO
  - Greps:
    - nome_arquivo `parser_itau_mensal`: 3 hits (0 nao-triviais)
    - classe `ParserItauMensal`: 0 hits (0 nao-triviais)
    - extrator_pdf — classes referenciadas: 0
- pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 301.76s (0:05:01)`
- pytest pos-revert: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 303.44s (0:05:03)`

### [5/6] `backend/services/parsers/parser_stone.py` — DEAD CONFIRMED (validacao manual)
- **PRE-CHECK automatico**: bloqueou em INVESTIGAR por **colisao de nome de classe** —
  `ParserStone` existe em DOIS arquivos:
  - `parser_stone.py:5` (legado, GRUPO A — orfao)
  - `stone.py:78` (ATIVO — usado por extrator_pdf, tests)

  Os 16 hits nao-triviais **TODOS apontam para `stone.py`**, nenhum para
  `parser_stone.py`.

- **PRE-CHECK manual** (Allan aprovou): focado no nome do MODULO, nao da classe.
  - `grep "parser_stone"` em arquivos `.py`: **0 hits** fora do proprio arquivo
  - `grep "from .parser_stone\|from services.parsers.parser_stone\|import parser_stone"`: **0 hits**
  - Em docs: 1 mencao em `AUDITORIA_TECNICA_CONTROLLO.md:192` (auditoria retrospectiva, trivial)

- **Validacao**:
  - pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 306.28s (0:05:06)`
  - pytest pos-revert: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 305.48s (0:05:05)`
  - Baseline preservado em ambos.
- **Veredito**: DEAD CONFIRMED. Linhas: 49.`

### [6/6] `backend/test_parsers.py` — DEAD CONFIRMED
- **PRE-CHECK**: LIMPO
  - Greps:
    - nome_arquivo `test_parsers`: 5 hits (0 nao-triviais)
    - funcao `formatar_brl`: 0 hits (0 nao-triviais)
    - funcao `formatar_brl_linha`: 0 hits (0 nao-triviais)
    - funcao `main`: 30 hits (0 nao-triviais)
    - extrator_pdf — classes referenciadas: 0
- pytest pos-disabled: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 303.71s (0:05:03)`
- pytest pos-revert: `1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 302.72s (0:05:02)`
