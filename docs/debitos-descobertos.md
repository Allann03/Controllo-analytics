# Debitos Tecnicos Descobertos -- Controllo BPO Analytics

Registro formal de debitos identificados durante auditoria e remediacao.
Cada entrada inclui severidade, bloco de remediacao associado e referencia cruzada.

---

## CRITICO-NEW-2 (ALTO-1b) -- Depreciacao e Amortizacao nunca subtraida da DRE

| Campo | Valor |
|---|---|
| **Severidade** | CRITICO |
| **Descoberto em** | BLOCO 3B.2 Fase B -- validacao paralela |
| **Arquivo afetado** | `backend/services/financeiro_service.py:73` |
| **Status** | Bug presente na engine legada; engine nova (BLOCO 3B.1) ja corrige |

### Descricao

`financeiro_service.py:73` soma apenas `da_adm + da_com + da_fin + da_out`, omitindo
`depreciacao_amortizacao`. CPC 26 par.102 e Lei 6.404/76 art. 187 IV sao inequivocos:
depreciacao e amortizacao sao despesas operacionais que impactam o resultado.

### Impacto

Toda empresa com D&A > 0 tem Resultado Liquido superestimado por D&A/mes.
Exemplo: Empresa Industria sintetica, D&A=20000/mes, LL inflado em R$240k/ano.

Afeta: LALUR, distribuicao de lucros, covenants bancarios, EBITDA reportado.

### Causa raiz

Bug coexiste com ALTO-1 (DFin incluida em despesas operacionais) desde a implementacao
original. A auditoria tecnica v2.0 nao detectou porque focou na reclassificacao DFin/EBIT
e nao inspecionou o consumo de depreciacao_amortizacao.

### Formula da divergencia

```
EBIT_novo - EBIT_legado  = +despesas_financeiras - depreciacao_amortizacao
LAIR_novo - LAIR_legado   = -depreciacao_amortizacao
LL_novo   - LL_legado     = -depreciacao_amortizacao
EBITDA_novo - EBITDA_legado = +despesas_financeiras (D&A cancela)
```

### Correcao

Ativar cutover de `CONTROLLO_DRE_ENGINE=novo` (motor 3.0.0 em `services/contabil/dre.py`).
Retroacao de dados historicos agendada para BLOCO 3K.

---

## ~~DEBITO-BLOCO0-1~~ -- `UsuarioMestreProtegidoError` sem conversao HTTP -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | BAIXA |
| **Descoberto em** | BLOCO 0 -- validacao pos-aplicacao (item 4.3) |
| **Resolvido em** | BLOCO 2 (antecipado) -- 2026-04-11 |

Exception handler global adicionado em `main.py`. Nao ha mais propagacao como HTTP 500.

---

## DEBITO-BLOCO2-1 -- zxcvbn nao da score >= 3 para senhas de 8 caracteres

| Campo | Valor |
|---|---|
| **Severidade** | INFO (decisao de design, nao bug) |
| **Descoberto em** | BLOCO 2 -- teste T2 |

Decisao de design aceita -- R1 honrada no piso formal (8 chars), seguranca reforcada
na pratica pela combinacao com zxcvbn.

---

---

## Correcao de especificacao — INV-P3' (EBITDA)

| Campo | Valor |
|---|---|
| **Tipo** | Correcao de especificacao pelo executor — aceita pelo mandato |
| **Descoberto em** | BLOCO 3B.2 Fase B — segunda execucao da validacao paralela |

A formula original INV-P3' especificada pelo mandato dizia `EBITDA_novo - EBITDA_leg == DFin`.
A derivacao estava algebricamente incorreta porque assumia que D&A cancela entre os dois motores.
Nao cancela: o legado faz `EBITDA_leg = (LB - adm - com - fin - out) + D&A`, adicionando D&A
a um EBIT que nunca a subtraiu. A formula correta e `EBITDA_diff == DFin - D&A`, confirmada
em 36/36 meses da validacao paralela. Protocolo permite divergencia com justificativa matematica.

---

---

## DEBITO-BLOCO2-2 -- zxcvbn-python ausente no venv local -- PARCIALMENTE RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | BAIXA (producao funciona; afeta apenas ambiente local de dev) |
| **Descoberto em** | Preparacao de deploy AWS (pos-BLOCO 3C) |
| **Parcialmente resolvido em** | Tarefa 0 da preparacao de infraestrutura -- 2026-04-11 |
| **Confirmado em** | BLOCO 3F.2 -- 2026-04-12 (requirements.txt L25 OK, venv local sem a lib) |

### Descricao

No BLOCO 2, `zxcvbn-python==4.4.24` foi instalada via `pip install` direto para testes,
mas nao foi persistida no `backend/requirements.txt`. Em producao com `CONTROLLO_ENV=production`,
`auth_utils.py` levanta `RuntimeError` no startup se a lib esta ausente.

### Correcao parcial

Adicionada linha `zxcvbn-python==4.4.24` ao `backend/requirements.txt` (L25) como excecao
cirurgica autorizada (manifesto de dependencias, nao codigo de aplicacao).

**Em producao AWS:** funciona corretamente. Container Docker reinstala todas as dependencias
do `requirements.txt` durante o build, incluindo zxcvbn-python.

**No venv local de desenvolvimento:** a lib ainda nao esta instalada. `auth_utils.py`
degrada silenciosamente (`_ZXCVBN_DISPONIVEL = False`), e o teste
`test_t8_senhas_comuns_rejeita_via_zxcvbn` falha porque senhas comuns passam nas 5 regras
deterministicas sem a validacao de entropia zxcvbn.

### Acao necessaria

Em ambiente local, rodar `pip install zxcvbn-python==4.4.24` antes de rodar pytest
para que `test_t8_senhas_comuns_rejeita_via_zxcvbn` passe.

---

## DEBITO-TESTE-1 -- test_pagbank.py e script CLI coletado erroneamente por pytest

| Campo | Valor |
|---|---|
| **Severidade** | BAIXA (nao afeta producao, apenas polui output do pytest) |
| **Descoberto em** | BLOCO 3F.2 -- investigacao pre-cutover LP -- 2026-04-12 |
| **Arquivo** | `backend/tests/test_pagbank.py:38` |
| **Erro pytest** | `fixture 'path' not found` |
| **Status** | Registrado. Correcao agendada para sprint de limpeza (BLOCO 7). |

### Descricao

`test_pagbank.py` e um script CLI standalone (`if __name__ == '__main__': main()`)
projetado para rodar manualmente contra PDFs locais do PagBank. A funcao
`testar_pdf(path: str, label: str, esperado: dict)` tem prefixo `testar_` que
pytest coleta automaticamente como teste. Pytest interpreta os parametros como
nomes de fixtures, que nao existem.

O script nunca foi projetado para rodar via `pytest` — funciona apenas como
`python tests/test_pagbank.py` com os PDFs presentes no disco local.

### Solucoes possiveis (nao aplicar agora)

1. Renomear funcoes de `testar_*` para `_run_*` (nao coletadas por pytest)
2. Adicionar `@pytest.mark.skip(reason="Script CLI, nao teste pytest")`
3. Mover para `scripts/` em vez de `tests/`

---

## DEBITO-TESTE-2 -- test_pagbank_integracao.py mesma causa que DEBITO-TESTE-1

| Campo | Valor |
|---|---|
| **Severidade** | BAIXA (nao afeta producao, apenas polui output do pytest) |
| **Descoberto em** | BLOCO 3F.2 -- investigacao pre-cutover LP -- 2026-04-12 |
| **Arquivo** | `backend/tests/test_pagbank_integracao.py:24` |
| **Erro pytest** | `fixture 'pdf_path' not found` |
| **Status** | Registrado. Tratar junto com DEBITO-TESTE-1 em sprint de limpeza (BLOCO 7). |

### Descricao

Mesma causa que DEBITO-TESTE-1. `testar_integracao(pdf_path: str, label: str)` e funcao
de script CLI coletada por pytest. Depende de PDFs locais do PagBank. Mesma arquitetura,
mesmas solucoes, mesma severidade. Tratar junto com DEBITO-TESTE-1.

---

## CRITICO-LP-1 -- CSLL com base 32% para comercio/industria

| Campo | Valor |
|---|---|
| **Severidade** | CRITICO |
| **Descoberto em** | BLOCO 3F -- diagnostico do motor legado |
| **Lei violada** | Lei 9.249/95 art. 20 |
| **Arquivo afetado** | `backend/services/tributario/lucro_presumido.py:44` e `constantes.py:97` |
| **Status** | Corrigido no motor BLOCO 3F (aguarda integracao) |

Base de presuncao da CSLL hardcoded em 32% para todas as atividades.
Deveria ser 12% para comercio, industria, hospitais, transporte de cargas (Lei 9.249/95 art. 20).
Impacto: empresa comercial RB 500k/mes paga CSLL sobre 160k (32%) em vez de 60k (12%).
Diferenca: R$ 9.000/mes = R$ 108.000/ano por cliente.

---

## CRITICO-LP-2 -- IRPJ com base 32% unica (era MEDIO-3 da auditoria)

| Campo | Valor |
|---|---|
| **Severidade** | CRITICO (promovido de MEDIO-3) |
| **Descoberto em** | Auditoria v2.0, confirmado BLOCO 3F |
| **Lei violada** | Lei 9.249/95 art. 15 par. 1 |
| **Arquivo afetado** | `backend/services/tributario/lucro_presumido.py:43` e `constantes.py:96` |
| **Status** | Corrigido no motor BLOCO 3F (aguarda integracao) |

Apenas base 32% implementada. Faltam 1.6% (combustiveis), 8% (comercio/industria) e 16% (transp. passageiros).
Impacto: empresa comercial RB 500k/mes paga IRPJ sobre 160k (32%) em vez de 40k (8%).
Diferenca: R$ 18.000/mes = R$ 216.000/ano por cliente.

Combinado com CRITICO-LP-1: ~R$ 27.000/mes = ~R$ 324.000/ano de superpagamento por empresa comercial.

---

## CRITICO-LR-1 -- LALUR completamente ausente no Lucro Real

| Campo | Valor |
|---|---|
| **Severidade** | CRITICO |
| **Descoberto em** | BLOCO 3G -- diagnostico do motor legado |
| **Arquivo afetado** | `backend/services/tributario/lucro_real.py:47` |
| **Status** | Corrigido no motor BLOCO 3G (aguarda integracao) |

"Lucro Real" legado = `max(0, receita_bruta - custo_servicos)` — e lucro bruto simplificado,
nao lucro real. Nenhuma adicao/exclusao do LALUR. Qualquer empresa com despesas indedutiveis
ou exclusoes legais tem IRPJ impreciso (sub ou superpagamento, bidirecional).

---

## CRITICO-LR-2 -- Compensacao de prejuizo fiscal ausente

| Campo | Valor |
|---|---|
| **Severidade** | CRITICO |
| **Descoberto em** | BLOCO 3G -- diagnostico |
| **Lei violada** | Lei 9.065/95 art. 15 |
| **Status** | Corrigido no motor BLOCO 3G |

Empresas com prejuizo historico nao recuperam nada. Compensacao limitada a 30% do lucro
real nao implementada. Prejuizo simplesmente zerado via max(0, ...).

---

## ALTO-LR-3 -- float em toda aritmetica do Lucro Real

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Descoberto em** | BLOCO 3G |
| **Status** | Corrigido via Decimal + money_fiscal |

---

## MEDIO-LR-4 -- Creditos PIS/COFINS sem detalhamento

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Descoberto em** | BLOCO 3G |
| **Status** | Corrigido com CreditoPISCofins detalhado por tipo |

---

## MEDIO-LR-5 -- CSLL sem base propria no Lucro Real

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Descoberto em** | BLOCO 3G |
| **Status** | Corrigido com parametro base_csll opcional |

---

## ~~MEDIO-1~~ -- Branch inalcancavel em score_saude.py -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Descoberto em** | Auditoria v2.0 |
| **Resolvido em** | BLOCO 3J -- 2026-04-12 |

Branch `quedas_consecutivas >= 3` inalcancavel porque `ultimos` tinha max 3 elementos
(max 2 comparacoes). Motor novo usa ate 6 meses, permitindo ate 5 quedas consecutivas.

---

## ALTO-SCORE-1 -- Float em saida do score legado

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Resolvido em** | BLOCO 3J -- motor novo com Decimal |

---

## MEDIO-SCORE-2 -- Pesos sem referencia bibliografica

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | BLOCO 3J -- pesos documentados conforme Adendo A.5.3 |

---

## MEDIO-SCORE-3 -- Sem componente Cobertura de Juros

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | BLOCO 3J -- adicionado como 9o componente (peso 5) |

---

## MEDIO-IND-1 -- 12 indicadores FP&A canonicos ausentes

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | BLOCO 3J -- 22 indicadores implementados em indicadores.py |

---

## NOVO-3I-1 -- Retencoes, DIFAL e ICMS-ST ausentes

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Descoberto em** | BLOCO 3I -- diagnostico |
| **Status** | Funcionalidade nova implementada no BLOCO 3I (3 modulos) |

Retencoes na fonte (IRRF, CSRF, INSS), DIFAL e ICMS-ST completamente ausentes
do sistema. Empresas que operam com servicos profissionais, cessao de mao de obra
ou operacoes interestaduais nao tinham suporte. Severidade MEDIO porque retencoes
sao responsabilidade do tomador e BPOs usam sistemas contabeis oficiais para isso.

---

## ALTO-RT-1 -- Cronograma 2026-2033 ausente na Reforma Tributaria

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Descoberto em** | BLOCO 3H -- diagnostico |
| **Status** | Corrigido no motor BLOCO 3H com tabela versionada por ano |

Aliquotas hardcoded: CBS 8.8% + IBS 17.7% (regime pleno 2033+) para todos os anos.
Em 2026 deveria ser CBS 0.9% + IBS 0.1% (fase teste). Erro de 25.5 pontos percentuais.

---

## ALTO-RT-2 -- Float em aritmetica da Reforma Tributaria

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Status** | Corrigido via Decimal + money_fiscal |

---

## MEDIO-RT-3 -- Sem regimes especificos na Reforma

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Status** | Corrigido com 6 regimes (geral, saude, educacao, transporte, agropecuaria, combustiveis) |

---

## MEDIO-RT-4 -- Referencia normativa desatualizada

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Status** | Corrigido: PLP 68/2024 -> EC 132/2023 + LC 214/2025 + LC 215/2025 |

---

## ALTO-LP-3 -- float em toda aritmetica do Lucro Presumido

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Descoberto em** | BLOCO 3F -- diagnostico |
| **Status** | Corrigido no motor BLOCO 3F via Decimal + money_fiscal |

Toda aritmetica tributaria em float (viola R3). Compoe com CRITICO-LP-1 e LP-2.

---

## DEBITO-DEPLOY-1 -- NEXT_PUBLIC_API_URL absoluta no frontend

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Descoberto em** | Leitura previa dos 9 arquivos para deploy |
| **Status** | MITIGADO via build-arg no Docker |

### Descricao

~30 arquivos TSX usam `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`.
Next.js embute variaveis `NEXT_PUBLIC_*` no bundle JavaScript durante o build (compile-time),
nao em runtime. Mudanca de dominio em producao exige rebuild do frontend via CI.

### Mitigacao

`frontend/Dockerfile.prod` declara `ARG NEXT_PUBLIC_API_URL` e o workflow GitHub Actions
passa o dominio via secret `DOMAIN_PRODUCAO` durante o build.

### Refactor futuro (BLOCO 3K ou posterior)

Migrar chamadas para URL relativa (`/api/*`) e deixar o reverse proxy (Caddy) rotear.
Elimina dependencia de build-arg e permite mudanca de dominio sem rebuild.

---

---

## ~~ALTO-PARSER-1~~ -- Santander Empresarial retorna 0 transacoes -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | ALTO |
| **Resolvido em** | 2026-04-12 |

Causa: formato App (datas por extenso + CREDITO/DEBITO R$) nao reconhecido.
Correcao: adicionado `_extrair_formato_app()` em santander_empresarial.py.
3 PDFs agora extraem 27, 24, 24 transacoes respectivamente.

---

## ~~MEDIO-PARSER-2~~ -- BS2 marca todas tx como saida -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | 2026-04-12 |

Causa tripla: (1) "-" na descricao interpretado como sinal negativo,
(2) "credito"/"debito" no _IGNORAR filtrava Pix Recebido,
(3) Remuneracao filtrada como interna quando e rendimento real.
Correcao: keywords refinadas, _IGNORAR corrigido, Remuneracao permitida.
Saldo agora bate exatamente: SI 72,500.88 + 69,571.07 - 60,124.93 = SF 81,947.02.

---

## ~~MEDIO-PARSER-3~~ -- Itau Mensal saidas infladas -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | 2026-04-12 |

Causa tripla: (1) regex _RE_LINHA faltava `-?` no grupo opcional de saldo —
quando saldo tinha sufixo negativo (ex: `142.677,53-`), regex backtrackava e
capturava saldo como valor da transacao (inflando saidas em ~R$ 2M).
(2) "Juros Limite da Conta" filtrada por 'limite da conta' em _IGNORAR.
(3) "IOF" (3 chars) filtrada por len(desc) < 4.
Correcao: regex corrigido com `-?`; 'limite da conta' -> 'limite da conta garantida';
len < 4 -> len < 3. Saldo agora exato: ent=1,057,532.72, said=1,033,211.71, SF=-107,561.07.

---

## ~~MEDIO-PARSER-4~~ -- Itau Empresas divergencia saidas -- RESOLVIDO

| Campo | Valor |
|---|---|
| **Severidade** | MEDIO |
| **Resolvido em** | 2026-04-12 |

Causa: (1) "JUROS LIMITE DA CONTA" filtrada por 'limite da conta' em _IGNORAR,
(2) "IOF" (3 chars) filtrada por len(desc) < 4 e len(desc) < 5.
Correcao: 'limite da conta' -> 'limite da conta garantida'; len < 4 -> len < 3.
Saldo agora bate exatamente: entradas=1,057,532.72, saidas=1,033,211.71, SF=-107,561.07.

---

*Arquivo criado em: 2026-04-10. Atualizado em: 2026-04-12 (validacao parsers + deploy AWS + registro debitos pre-cutover LP).*
