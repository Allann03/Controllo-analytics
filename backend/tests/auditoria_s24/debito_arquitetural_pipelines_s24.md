# Débito arquitetural: dois orquestradores de pipeline em paralelo

Descoberto durante: S24 Fase 2 (2026-05-02)
Severidade: MÉDIA (não afeta produção, mas mascara realidade em
auditorias e introduz divergência entre testes E2E e endpoint real).

## Resumo

Existem **dois orquestradores** que extraem dados de extratos PDF e
populam `saldo_inicial`/`saldo_final`/`saldos_intermediarios`:

1. **Legado**: `backend/services/extrator_pdf.py::processar_extrato`
   (função módulo, retorna `dict`).
2. **Novo**: `backend/services/pipeline_extracao.py::processar_com_pipeline`
   (pipeline de 8 passos, retorna `ResultadoExtracao` dataclass).

O endpoint `/api/processar-extrato` (`backend/main.py:1378`) chama
**ambos**: `processar_com_pipeline` na linha 1418 (apenas para guardar
`_pipeline_result` e validar guard de "silent failure"), e
`_processar_extrato_pdf` (alias do legado) na linha 1421 (resultado
retornado ao cliente).

## Tabela comparativa

| Característica | Legado | Novo |
|---|---|---|
| Localização | `extrator_pdf.py:1507` | `pipeline_extracao.py:762` |
| Retorno | `dict` | `ResultadoExtracao` |
| Chama `_extrair_saldos_intermediarios()` | Sim (l. 1377) | Sim (l. 337) |
| Backfill SI a partir de saldos intermediários | **Sim** (l. 1397–1401, 1483–1491) | **Não** |
| Conferência cruzada modo abertura/fechamento | Sim (l. 1420–1462) | Sim (l. 484–525) |
| Validador Sessão 18 (VERDE/AMARELO/VERMELHO) | Não | Sim (l. 590–638) |
| Excel pelo pipeline | Não (gera por outra rota) | Sim (l. 696) |
| Logging estruturado de passos | Não | Sim |

## Onde cada um é chamado

**`processar_com_pipeline` (novo)**:
- `backend/main.py:1417–1418` — endpoint principal (uso parcial).
- `backend/tests/auditoria_s23/run_auditoria.py:65` — auditoria S23
  (gera os relatórios VERDE/AMARELO/VERMELHO).
- `backend/tests/auditoria_s23/detalhes_vermelhos.py:43`.
- `backend/tests/test_inter_ocr_fallback.py:165`.

**`processar_extrato` (legado)**:
- `backend/main.py:21, 1421, 1757, 2009` — endpoints principais
  (resultado entregue ao usuário).
- `backend/routers/conciliacao.py:263`.

## Comentário órfão como evidência de migração incompleta

`pipeline_extracao.py:462–466`:

```python
if r.saldo_inicial is None:
    # Tentar usar primeiro saldo intermediario como ponto de partida
    self._log(6, 'Conferencia Progressiva', True,
              'SI nao disponivel — conferencia progressiva limitada')
    return
```

O comentário declara intenção de inferir SI a partir do primeiro saldo
intermediário, mas o código apenas loga e retorna. A lógica análoga já
implementada no legado (`extrator_pdf.py:1397–1401` e backfill em
1483–1491) **nunca foi portada**.

## Implicações

| Contexto | Impacto |
|---|---|
| Produção (endpoint) | Usuário final recebe resultado do legado → backfill ativo → Stone funciona após S24. |
| Auditoria S23 | Pipeline novo subreporta → falsos VERMELHOS para todos os PDFs cuja extração de SI depende de backfill. |
| Testes E2E novos | Precisam saber qual orquestrador usar (S24 Fase 2 escolheu legado para refletir produção). |
| Excel | Gerado por outro caminho — não afetado por SI/SF do pipeline. |
| Validador Sessão 18 | Rodado **apenas** no pipeline novo. Legado não classifica VERDE/AMARELO/VERMELHO. |

## Recomendação para sessão futura (S30+)

**Opção 1 — Portar backfill do legado para o pipeline novo** (~30–50
linhas).
- Inserir após o passo 2 ou no início do passo 6 a lógica
  "se `r.saldo_inicial is None and r.saldos_intermediarios` → usar
  primeiro saldo como SI; recalcular SF se None".
- R-B obrigatória em **todos os bancos** (Bradesco, Nubank, Santander,
  Itaú, etc.), pois mexer no caminho que produz SI/SF afeta todo o
  pipeline.
- Auditoria S23 deve rodar 96 PDFs antes/depois e comparar nível por
  nível.

**Opção 2 — Deprecar o pipeline novo**.
- Sentido inverso da migração planejada (pipeline novo foi criado para
  oferecer validador Sessão 18, classificação de confiança, Excel
  estruturado). Improvável.

**Opção 3 — Refatorar para um único orquestrador** com superset de
features.
- Refactor estrutural; sessão dedicada (vários turnos).
- Estado-alvo: `extrator_pdf.processar_extrato` torna-se thin wrapper
  sobre `processar_com_pipeline` (ou vice-versa).

## Riscos de NÃO atacar

- **Confusão entre duas verdades**: auditoria reporta VERMELHO para
  Stone, mas usuário do endpoint vê SI/SF preenchidos.
- **Manutenção redundante**: bugs de extração de saldo precisam ser
  fixados em ambos quando a divergência envolve heurística.
- **Onboarding confuso**: novos contribuintes precisam aprender qual
  pipeline usar para qual contexto.
- **Risco de regressão em produção** se alguém migrar o endpoint
  apenas para o pipeline novo sem antes portar o backfill.

## Histórico

- Antes da S24: divergência presumivelmente já existia mas não havia
  parser que dependesse de backfill (todos os bancos tinham
  `_extrair_saldos_pdf` retornando SI/SF diretos do texto).
- S24 Fase 2 (2026-05-02): Stone passou a depender do backfill via
  `_extrair_saldos_intermediarios`. A divergência só ficou observável
  então, com 8 testes E2E falhando inicialmente quando rodados pelo
  pipeline novo. Solução S24: testes redirecionados para o legado;
  débito documentado.
