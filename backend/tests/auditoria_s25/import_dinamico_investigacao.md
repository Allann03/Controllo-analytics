# Investigacao de Imports Dinamicos — S25 Fase 3

Pontos cegos do grafo estatico — analise manual.

## §1 `backend/main.py:892` — `__import__("sqlalchemy")`

### Codigo (linhas 887-898)

```python
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check para AWS ALB / ECS / qualquer load balancer."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "healthy", "db": "ok"}
```

### Analise

- **Modulo importado**: `sqlalchemy` — biblioteca **externa** (3rd-party), ja
  presente em `requirements.txt`. Nao e modulo interno do projeto.
- **Status**: ATIVO — endpoint `/api/health` e usado em producao por
  load balancer (AWS ALB / ECS).
- **Uso dinamico**: equivale a `import sqlalchemy` no topo, mas escrito
  inline para uso unico em uma expressao. Nao adiciona nem remove
  dependencias.
- **Efeito no grafo de dead-code interno**: **ZERO**. Nao referencia
  nenhum arquivo do projeto. Nao gera dead-code falso positivo.

### Veredito
**SEM IMPACTO no mapeamento de dead code.** Pode ser ignorado.
(Refator opcional na S30+: substituir por `from sqlalchemy import text`
no topo, mas e melhoria estilistica nao funcional.)

---

## §2 `backend/tests/test_lp_dispatch.py:92` — `import importlib`

### Codigo (linhas 85-105)

```python
        # (o modulo ja carregou com CONTROLLO_LP_ENGINE nao definida ou "legado")
        assert _usar_motor_lp_novo(override=None) is False or True  # depende da env
        # Teste mais robusto: sem override, nao forca "novo"
        assert _usar_motor_lp_novo(override="") is False or True

    def test_dsp_04_flag_invalida_fallback_legado(self):
        """T-DSP-04: flag invalida -> fallback 'legado' + log error."""
        import importlib
        import logging

        with patch.dict(os.environ, {"CONTROLLO_LP_ENGINE": "invalido"}):
            with patch("services.simulacao_tributaria_service._logger") as mock_logger:
                # Reimportar para reavaliar a flag
                import services.simulacao_tributaria_service as mod
                # Testar a funcao _usar_motor_lp_novo diretamente
                # Com override None e flag "invalido" -> cai em fallback "legado"
                # O modulo ja tratou isso no import, entao testamos a funcao
                result = mod._usar_motor_lp_novo(override=None)
                # Sem override "novo", retorna False (usa legado)
                # (a flag original pode ser "legado" ou "novo" dependendo da env de teste)
```

### Analise

- **Modulo importado dinamicamente**: `importlib` — biblioteca **stdlib**.
  Nao e modulo interno.
- **Uso real de `importlib.import_module`**: confirmado **AUSENTE** no
  arquivo (grep `importlib\.` retornou zero matches em todo o test_lp_dispatch.py).
  O `import importlib` e `import logging` foram declarados mas nao usados
  no corpo do teste.
- **Hipotese**: residuo de iteracao anterior do teste (talvez uma versao
  anterior fazia `importlib.reload(mod)` para reavaliar a flag — comentario
  "Reimportar para reavaliar a flag" na linha 97 sugere isso, mas o codigo
  efetivo virou `import services.simulacao_tributaria_service as mod` direto).
- **Efeito no grafo**:
  - `import importlib` -> stdlib, nao gera aresta.
  - `import services.simulacao_tributaria_service as mod` (linha 98) -> esse
    sim e um import interno, normal, **ja capturado** pelo extrator
    (Cenario 3 do `audit_grafo_test.py` — lazy import dentro de funcao).
  - **Conclusao**: o teste contribui com aresta `tests/test_lp_dispatch.py
    -> services/simulacao_tributaria_service.py` ja contabilizada.

### Veredito
**SEM IMPACTO no mapeamento de dead code.** O `import importlib` e residuo
de codigo morto interno-ao-arquivo (uma linha nao-usada), mas nao causa
falso positivo de dead code em modulos do projeto.

---

## §3 Sintese

| Local | Modulo | Tipo | Impacto no dead-code |
| --- | --- | --- | --- |
| `main.py:892` | `sqlalchemy` (externo) | __import__ inline | Nenhum |
| `tests/test_lp_dispatch.py:92` | `importlib` (stdlib) | residuo | Nenhum |

**Nenhum import dinamico aponta para modulo interno do projeto.**
Pontos cegos do grafo confirmados como zero — Fase 3 pode prosseguir
com seguranca de que dead-code nao tem fonte oculta via `importlib.import_module`
ou `__import__`.
