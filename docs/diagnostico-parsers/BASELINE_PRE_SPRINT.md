# BASELINE PRÉ-SPRINT PARSERS

**Data:** 2026-04-23
**Commit de setup:** `7d1778e` (docs: diagnostico tecnico dos parsers + ground truth)
**Branch base para todos os turnos:** `main`

---

## Estado da suíte de testes ANTES dos Turnos 1–11

Rodado com:
```bash
cd backend && pytest tests/ --tb=no -q
```

Resultado:
```
731 passed
  1 failed
  2 errors
  0 skipped
Total: 734 testes
Tempo: ~13s
```

## Falhas/erros pré-existentes (NÃO são regressão)

Estas falhas já existiam antes da sprint de parsers começar. Nenhum turno
precisa corrigi-las — elas são de outros escopos.

### `test_validacao_senha` — FAILED
- **Causa:** dependência `zxcvbn-python` não instalada no ambiente
- **Escopo:** fora da sprint de parsers (é do módulo de auth/validação)
- **Fix futuro:** `pip install zxcvbn-python` ou marcar teste com `@pytest.mark.skipif`

### `test_pagbank` — 2 ERRORS
- **Causa:** fixture PDF ausente em `backend/tests/fixtures/pdfs_reais/` (provavelmente
  removido quando `.gitignore` passou a proteger `*.pdf` nessa pasta)
- **Escopo:** indiretamente relacionado à sprint, mas **não deve ser corrigido
  durante ela** — precisaria restaurar o PDF original ou gerar um fixture sintético,
  decisão separada
- **Fix futuro:** após a sprint, criar fixture sintético PagBank ou usar `.txt`
  de ground truth (mesma abordagem dos outros bancos da sprint)

---

## Regra para todos os turnos 1–11

O Claude Code DEVE usar estes números como baseline de comparação:

**Estado aceitável (sem regressão) em cada turno:**
- `passed` >= 731 (pode aumentar se o turno adicionar testes novos)
- `failed` = 1 (apenas `test_validacao_senha`)
- `errors` = 2 (apenas `test_pagbank`)

**Estado inaceitável (regressão introduzida pelo turno):**
- `passed` < 731
- Qualquer falha/erro novo em teste que não seja `test_validacao_senha` ou `test_pagbank`
- Qualquer falha/erro em teste que passava antes

Se o turno adicionar novos testes (esperado), `passed` aumenta — OK.
Se `failed` aumenta além de 1, ou `errors` além de 2, investigar o que quebrou.
