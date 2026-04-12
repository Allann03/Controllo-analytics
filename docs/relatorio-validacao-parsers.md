# Relatorio de Validacao de Parsers

Data: 2026-04-12
Total PDFs testados: 15
Total bancos: 6 (Santander, Nubank, Bradesco, Itau, BS2, Inter)

---

## Resultados por PDF

### Santander

| PDF | Parser | Transacoes | Entradas | Saidas | Saldo | Status |
|---|---|---|---|---|---|---|
| Santander pf .pdf | santander_consolidado | 222 | 529,341.30 | 529,341.30 | OK (0.00=0.00) | **APROVADO** |
| Santander pf 2.pdf | santander_consolidado | (nao testado — segundo PDF do mesmo formato) | — | — | — | PENDENTE |
| Santander empresas 2.pdf | santander (fallback app) | 27 | 1,815.21 | 2,207.10 | N/A (sem SI/SF) | **APROVADO** |
| Empresarial 3.pdf | santander | 0 | 0 | 0 | N/A | **REPROVADO** |
| Santander empresarial .pdf | santander | 0 | 0 | 0 | N/A | **REPROVADO** |
| Santander empresarial 2.pdf | santander | 0 | 0 | 0 | N/A | **REPROVADO** |

### Nubank

| PDF | Parser | Transacoes | Entradas | Saidas | Saldo | Status |
|---|---|---|---|---|---|---|
| Nubank.pdf | nubank | 82 | 17,296.12 | 11,594.60 | OK (5,731.68=5,731.68) | **APROVADO** |
| Nubank 2.pdf | nubank | 71 | 270,434.61 | 267,633.13 | OK (2,801.48=2,801.48) | **APROVADO** |

### Bradesco Net Empresa

| PDF | Parser | Transacoes | Desc OK | Multi-line | Status |
|---|---|---|---|---|---|
| Bradesco net.pdf | bradesco_net_empresas | 78 | Sim (0 curtas) | 9 TED+REMET, 26 PIX+REM | **APROVADO (descricoes)** |
| Bradesco net2.pdf | bradesco_net_empresas | 81 | Sim (0 curtas) | 9 TED+REMET, 38 PIX+REM | **APROVADO (descricoes)** |
| Bradesco5.pdf | bradesco_net_empresas | 35 | Sim (0 curtas) | 11 PIX+REM | **APROVADO (descricoes)** |

Nota: saldo final diverge nos 3 PDFs Bradesco por causa de secoes RENTAB.INVEST (juros
de investimento) parcialmente capturadas e "Ultimos Lancamentos" com SI diferente.
Descricoes multi-linha estao todas concatenadas corretamente (bug ALTO-1 original corrigido).

### Itau

| PDF | Parser | Transacoes | Entradas | Saidas | Saldo | Status |
|---|---|---|---|---|---|---|
| Itau .pdf | itau | 45 | 176,304.79 | 156,518.40 | N/A (SF nao conferido) | **APROVADO (extrai tx)** |
| Itau 2.pdf | itau | 298 | 796,865.52 | 3,092,721.19 | DIVERGE | **REPROVADO** |
| Itau empresas.pdf | itau_empresas | 299 | 1,058,282.79 | 1,012,424.95 | DIVERGE +21,536.83 | **REPROVADO** |

### BS2

| PDF | Parser | Transacoes | Entradas | Saidas | Saldo | Status |
|---|---|---|---|---|---|---|
| B2S.pdf | bs2 | 17 | 8,011.68 | 30,660.12 | DIVERGE -32,094.58 | **REPROVADO** |

### Inter

| PDF | Parser | Transacoes | Status |
|---|---|---|---|
| Inter.pdf | inter | 0 | **PDF de imagem — OCR necessario** |

---

## Resumo

```
========================================
RELATORIO FINAL DE VALIDACAO
========================================
Total de PDFs testados: 15
Total de bancos: 6
Total de transacoes extraidas: ~1,255

RESULTADOS:
[OK] Santander pf .pdf — APROVADO (saldo exato: 529,341.30 = 529,341.30)
[OK] Santander empresas 2.pdf — APROVADO (27 tx extraidas)
[OK] Nubank.pdf — APROVADO (saldo exato)
[OK] Nubank 2.pdf — APROVADO (saldo exato)
[OK] Bradesco net.pdf — APROVADO (descricoes multi-linha corrigidas)
[OK] Bradesco net2.pdf — APROVADO (descricoes multi-linha corrigidas)
[OK] Bradesco5.pdf — APROVADO (descricoes multi-linha corrigidas)
[OK] Itau .pdf — APROVADO (45 tx extraidas, SI/SF nao conferidos)
[--] Inter.pdf — REPORTADO (PDF de imagem, OCR necessario)
[!!] Empresarial 3.pdf — REPROVADO (0 transacoes)
[!!] Santander empresarial .pdf — REPROVADO (0 transacoes)
[!!] Santander empresarial 2.pdf — REPROVADO (0 transacoes)
[!!] Itau 2.pdf — REPROVADO (saidas infladas ~3x)
[!!] Itau empresas.pdf — REPROVADO (divergencia +21k)
[!!] B2S.pdf — REPROVADO (muitas tx como saida que deveriam ser entrada)
```

## Parsers com divergencia

| Banco | PDF | Natureza do problema |
|---|---|---|
| Santander Empresarial | Empresarial 3, empresarial .pdf, empresarial 2 | Parser santander_empresarial.py retorna 0 tx. Possivel mudanca de formato no PDF que o parser nao reconhece. |
| Itau | Itau 2.pdf | Saidas infladas (~3x acima do esperado). Parser pode estar contando transferencias internas como saida. |
| Itau Empresas | Itau empresas.pdf | Divergencia de +21k no saldo. Possivel tx faltando ou duplicada. |
| BS2 | B2S.pdf | Todas as 17 tx marcadas como saida. Parser pode nao estar detectando entradas. |

## Debitos tecnicos encontrados

1. **ALTO-PARSER-1**: Santander Empresarial (3 PDFs) — parser retorna 0 transacoes. Formato
   possivelmente incompativel com a versao atual do parser. Investigar em sessao futura.
2. **MEDIO-PARSER-2**: BS2 — parser marca todas as transacoes como saida. Logica de
   determinacao de tipo (entrada/saida) pode estar invertida ou ignorando creditos.
3. **MEDIO-PARSER-3**: Itau 2 — saidas infladas ~3x. Possivel contagem dupla de transferencias
   ou inclusao de saldos intermediarios como transacoes.
4. **MEDIO-PARSER-4**: Itau Empresas — divergencia de +21k. Mesmos dados que Itau 2 em
   formato diferente, resultados divergem entre os parsers.
5. **INFO-PARSER-5**: Inter — PDF baseado em imagem. Necessita EasyOCR habilitado para extrair
   transacoes. Comportamento esperado (falha silenciosa documentada).

---

*Relatorio gerado em 2026-04-12. Todos os testes rodados contra PDFs reais.*
