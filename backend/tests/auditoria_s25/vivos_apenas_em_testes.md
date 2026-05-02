# Vivos APENAS via Testes — GRUPO B (S25 Fase 2 + Fase 3c)

Arquivos com in-degree=0 no recorte producao mas in-degree>0 no completo.
NAO sao dead code para deletar. Sao features sem integracao em endpoints.

> **Nota — versao corrigida apos bug do extrator (S25 Fase 1.b)**
>
> Removidos do GRUPO B apos correcao:
> - `backend/services/financeiro_service.py` — passou a in-degree=2 no
>   producao (importado por `routers/financeiro.py:26` e por
>   `main.py:2378/2450` via `from services import financeiro_service as fs`)
> - `backend/services/simulacao_tributaria_service.py` — passou a
>   in-degree=1 no producao (importado por `routers/financeiro.py:27`
>   via `from services import simulacao_tributaria_service as sts`)
>
> Ambos sao codigo de producao integrado. NAO eram "vivos so via teste"
> — eram dependencias funcionais nao detectadas pelo extrator antigo.

## Sumario com sub-categorizacao (Fase 3c)

| Arquivo | Linhas | Testes | Linhas teste | Sub-categoria |
| --- | --- | --- | --- | --- |
| `services/categorias.py` | 398 | 6 (`test_categorias.py`) | 38 | **Ramo duplicado** |
| `services/contabil/comparador.py` | 191 | 80 (`test_comparador_indicadores_score.py`) | 475* | **WIP nao integrado** |
| `services/contabil/dfc.py` | 340 | 48 (`test_dfc.py`) | 552 | **WIP nao integrado** |
| `services/contabil/difal.py` | 136 | 60 (`test_retencoes_difal_st.py`) | 413* | **WIP nao integrado** |
| `services/contabil/icms_st.py` | 108 | 60 (`test_retencoes_difal_st.py`) | 413* | **WIP nao integrado** |
| `services/contabil/retencoes.py` | 138 | 60 (`test_retencoes_difal_st.py`) | 413* | **WIP nao integrado** |
| `services/contabil/score_saude.py` | 267 | 80 (`test_comparador_indicadores_score.py`) | 475* | **Refator paralelo nao ativado** |

`*` testes compartilhados entre arquivos do mesmo dominio.

**Nenhum arquivo do GRUPO B usa feature flag** (`CONTROLLO_DRE_ENGINE`,
`CONTROLLO_LP_ENGINE`, `os.environ`, `os.getenv`) — checado por grep.

---

## §1 `services/categorias.py` — RAMO DUPLICADO

- Tamanho: 398 linhas
- Ultima modificacao: 2026-04-12 00:40:32 -0300
- Funcao publica: `aplicar_categorias(descricao: str) -> str`
- Importadores: 1 (`tests/test_categorias.py`)

**Achado critico** — `aplicar_categorias` esta DUPLICADA em codigo de producao:

| Local | Tipo | Status |
| --- | --- | --- |
| `services/categorias.py:335` | `def aplicar_categorias(descricao: str) -> str` | **GRUPO B (orfao)** |
| `services/extrator_pdf.py:1648` | `def aplicar_categorias(transacoes: list) -> list` | **PRODUCAO ATIVO** |

A versao em `extrator_pdf.py` e:
- Chamada em `extrator_pdf.py:1337` (mesmo arquivo)
- Re-exportada via `pipeline_extracao.py:34` (`from .extrator_pdf import aplicar_categorias`)
- Usada em `pipeline_extracao.py:321`

Note que **assinaturas sao diferentes** (uma toma string, outra toma lista),
mas o nome colide.

**Sub-categoria: Ramo duplicado** — implementacao paralela `categorias.py`
nao integrada em producao. Os 6 testes em `test_categorias.py` validam
APENAS essa versao morta. Candidato forte a deletar (ramo + testes).

---

## §2 `services/contabil/comparador.py` — WIP NAO INTEGRADO

- Tamanho: 191 linhas
- Classes: `ComparativoRegimes`, `PerfilEmpresa`
- Funcao: `comparar_regimes`
- Importadores: 1 (`tests/test_comparador_indicadores_score.py`)

**Achado** — colisao de nome com endpoint:

| Local | Tipo | Status |
| --- | --- | --- |
| `routers/financeiro.py:253` | `def comparar_regimes(...)` (endpoint) | **PRODUCAO** |
| `services/contabil/comparador.py:88` | `def comparar_regimes(perfil: PerfilEmpresa, ...)` | **GRUPO B** |

Mas o endpoint **nao chama** a funcao do comparador.py — usa `simulacao_tributaria_service`
(verificado pelo grafo). Sao implementacoes paralelas com mesmo nome,
sem integracao.

**Sub-categoria: WIP nao integrado.** A logica em `comparador.py` parece
ser uma proposta de "comparar regimes via PerfilEmpresa unificado" que
nao foi adotada pelo router. Decisao de produto: ativar (substituir
endpoint atual) ou remover.

---

## §3 `services/contabil/dfc.py` — WIP NAO INTEGRADO

- Tamanho: 340 linhas
- Classes: `DFC`, `LinhaDFC`
- Funcao: `calcular_dfc`
- Importadores: 1 (`tests/test_dfc.py` — 48 testes, 552 linhas)

**Achado** — `calcular_dfc` UNICA implementacao no codebase. Nenhum endpoint
chama. Nenhum service de producao chama.

DFC = Demonstracao do Fluxo de Caixa, peca contabil obrigatoria.
A ausencia de integracao sugere feature contabil completa que
**nao foi exposta via API ainda**.

**Sub-categoria: WIP nao integrado.** Implementacao validada por 48
testes mas sem rota publica.

---

## §4 `services/contabil/difal.py` — WIP NAO INTEGRADO

- Tamanho: 136 linhas
- Classes: `OperacaoInterestadual`, `ResultadoDIFAL`
- Funcao: `calcular_difal`
- Importadores: 1 (`tests/test_retencoes_difal_st.py`)

DIFAL = ICMS Diferencial de Aliquota em operacoes interestaduais.
Unica implementacao, sem endpoint.

**Sub-categoria: WIP nao integrado.**

---

## §5 `services/contabil/icms_st.py` — WIP NAO INTEGRADO

- Tamanho: 108 linhas
- Classes: `OperacaoST`, `ResultadoICMSST`
- Funcao: `calcular_icms_st`
- Importadores: 1 (`tests/test_retencoes_difal_st.py`)

ICMS ST = Substituicao Tributaria. Idem padrao acima.

**Sub-categoria: WIP nao integrado.**

---

## §6 `services/contabil/retencoes.py` — WIP NAO INTEGRADO

- Tamanho: 138 linhas
- Classes: `PagamentoServico`, `ResultadoRetencoes`
- Funcao: `calcular_retencoes`
- Importadores: 1 (`tests/test_retencoes_difal_st.py`)

Retencoes (PIS/COFINS/CSLL/IRRF). Idem padrao.

**Sub-categoria: WIP nao integrado.**

> Os 3 arquivos `difal.py`, `icms_st.py`, `retencoes.py` sao co-validados
> pelo mesmo `test_retencoes_difal_st.py` (60 testes, 413 linhas) — sao
> um cluster contabil-fiscal unificado.

---

## §7 `services/contabil/score_saude.py` — REFATOR PARALELO NAO ATIVADO

- Tamanho: 267 linhas
- Classe: `ResultadoScore`
- Funcao: `calcular_score`
- Importadores: 1 (`tests/test_comparador_indicadores_score.py`)

**Achado critico** — DUAS implementacoes coexistem:

| Local | Status |
| --- | --- |
| `services/score_saude.py` (LEGADO) | **PRODUCAO ATIVO** — usado por `main.py:2377/2449`, `routers/financeiro.py:28` |
| `services/contabil/score_saude.py` (NOVO, GRUPO B) | **NAO ATIVADO** — apenas tests |

A docstring do arquivo NOVO confirma: *"Correcoes sobre o legado: MEDIO-1...
ALTO-SCORE-1: float -> Decimal..."*. E uma reescrita corrigindo bugs do legado.

A flag literal "legado"/"novo" nao e variavel de ambiente — e referencia
textual ao status. Nao ha mecanismo automatizado de switch.

**Sub-categoria: Refator paralelo nao ativado.** Versao nova esta validada
por 80 testes mas o codigo de producao continua usando `services/score_saude.py`
antigo. Decisao de produto: substituir (e migrar consumidores) ou remover.

---

## §8 Sintese para a S26+

### Ramo morto que pode ser deletado:
- `services/categorias.py` + `tests/test_categorias.py` — duplicata da
  funcao `aplicar_categorias` ja em `extrator_pdf.py:1648`. **Ramo morto
  com testes mortos.**

### Reescritas paralelas que precisam decisao Allan:
- `services/contabil/score_saude.py` (vs `services/score_saude.py` legado)
  — qual ativar?
- `services/contabil/comparador.py` (vs endpoint `routers/financeiro.py:253`)
  — ativar a versao service-layer ou manter no router?

### WIP nao integrados — decisao Allan:
- `services/contabil/dfc.py` — expor via novo endpoint `/api/financeiro/dfc`?
- `services/contabil/difal.py` + `icms_st.py` + `retencoes.py` — expor via
  novo endpoint `/api/tributario/retencoes`?

### Custo de remocao TOTAL (se Allan decidir abandonar):
- ~1.578 linhas de codigo de servico (398 + 191 + 340 + 136 + 108 + 138 + 267)
- ~1.478 linhas de testes (38 + 475 + 552 + 413)
- Total **3.056 linhas** removiveis em conjunto, sem afetar pytest baseline.

### NENHUM dos arquivos do GRUPO B esta sob feature-flag.
Confirmado por grep negativo em `CONTROLLO_*`, `FEATURE_FLAG`,
`os.environ`, `os.getenv` — tanto nos arquivos quanto nos testes.

---

## §9 Sub-categorizacao A/B/C (Fase 3c finalizada)

Investigacao adicional: a infraestrutura de feature flag do projeto
(`CONTROLLO_DRE_ENGINE`, `CONTROLLO_LP_ENGINE`) **EXISTE** e e usada por
`financeiro_service.py` e `simulacao_tributaria_service.py`, que
chamam `services.contabil.dre`, `lucro_presumido`, `cnae_presuncao`,
`core` quando a flag esta `novo`.

**MAS nenhum dos 7 arquivos do GRUPO B e referenciado pelos motores
novos sob flag.** Verificacao por grep: zero hits para
`from services.{categorias,contabil.comparador,contabil.dfc,contabil.difal,
contabil.icms_st,contabil.retencoes,contabil.score_saude}` em
`financeiro_service.py`, `simulacao_tributaria_service.py`,
`main.py`, `routers/*`.

Os testes do Grupo B tambem nao mockam ou setam variaveis de ambiente
de feature flag (verificado por grep em `test_categorias.py`,
`test_comparador_indicadores_score.py`, `test_dfc.py`,
`test_retencoes_difal_st.py`).

Tambem confirmado: nenhum dos 4 arquivos de teste e referenciado
fora deles mesmos (sao folhas absolutas do grafo).

### Classificacao final

| Arquivo | Sub-cat | Justificativa |
| --- | --- | --- |
| `services/categorias.py` | **A — RAMO INTEIRO MORTO** | `aplicar_categorias` ja existe em `extrator_pdf.py:1648` (versao usada em producao via pipeline_extracao.py). Esta versao e duplicata morta. + 6 testes em `test_categorias.py` (38 linhas) validam apenas a versao morta. |
| `services/contabil/comparador.py` | **A — RAMO INTEIRO MORTO** | `comparar_regimes` aqui NAO e chamado pelo endpoint `/api/financeiro/comparar-regimes` (que usa `simulacao_tributaria_service`) nem pelos motores sob flag. Implementacao desconectada. + parte de `test_comparador_indicadores_score.py`. |
| `services/contabil/dfc.py` | **C — WIP nao integrado** | `calcular_dfc` (DFC = Demonstracao do Fluxo de Caixa, peca contabil obrigatoria). Implementacao completa (340 linhas, 48 testes) mas sem endpoint nem chamada de motor. Decisao Allan: ativar via novo endpoint ou abandonar. |
| `services/contabil/difal.py` | **C — WIP nao integrado** | `calcular_difal` (DIFAL = ICMS Diferencial Aliquota interestadual). Implementacao completa, sem endpoint. |
| `services/contabil/icms_st.py` | **C — WIP nao integrado** | `calcular_icms_st` (ICMS Substituicao Tributaria). Implementacao completa, sem endpoint. |
| `services/contabil/retencoes.py` | **C — WIP nao integrado** | `calcular_retencoes` (PIS/COFINS/CSLL/IRRF). Implementacao completa, sem endpoint. |
| `services/contabil/score_saude.py` | **C — Refator paralelo nao ativado** | DUAS implementacoes coexistem: `services/score_saude.py` (LEGADO ATIVO em main.py + routers/financeiro.py) vs esta nova versao (267 linhas, validada por 80 testes). Docstring confirma que sao correcoes do legado (Decimal vs float, cobertura de juros). Decisao Allan: migrar consumidores. |

### Totais

- **Sub-categoria A (RAMO INTEIRO MORTO)**: 2 arquivos (`categorias.py` +
  `contabil/comparador.py`) + 1 teste inteiro (`test_categorias.py`) + porcao
  de `test_comparador_indicadores_score.py` (testes especificos da
  classe `ComparativoRegimes` / `comparar_regimes`).
  **~589 linhas removiveis se Allan aprovar** (398 + 191).

- **Sub-categoria B (FEATURE FLAG INATIVA)**: **ZERO arquivos**. Nenhum
  Grupo B se enquadra — nao ha mecanismo automatizado de ativacao.

- **Sub-categoria C (WIP nao integrado)**: 5 arquivos (`dfc.py`, `difal.py`,
  `icms_st.py`, `retencoes.py`, `score_saude.py`) + parte dos testes
  `test_dfc.py`, `test_retencoes_difal_st.py`,
  `test_comparador_indicadores_score.py`. ~989 linhas de servico.
  **NAO REMOVER — decisao de produto.**

### Recomendacao para a S26+

1. **S26 (remocao GRUPO A consolidada)**: incluir `services/categorias.py` +
   `tests/test_categorias.py` apos confirmacao adicional ad-hoc
   (rodar pytest desabilitando esses dois arquivos juntos).
2. **S26 (remocao parcial GRUPO B sub-A)**: deletar
   `services/contabil/comparador.py` apos extracao das funcoes-teste
   correspondentes em `test_comparador_indicadores_score.py`. Cuidar para
   nao perder os testes de `score_saude.py` e `indicadores.py` que
   coabitam o mesmo arquivo de teste.
3. **Sx (decisao Allan)**: avaliar ativacao das pecas C (DFC, DIFAL,
   ICMS ST, retencoes, score novo) ou abandona-las — ~989 linhas de
   servico + ~1440 linhas de teste em jogo.
