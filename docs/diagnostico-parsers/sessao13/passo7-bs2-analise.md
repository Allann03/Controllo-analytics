# Passo 7 — BS2: análise da detecção e do parser

## Metadados de execução

```json
{
  "executado_com": {
    "python": "3.14.4",
    "pikepdf": "10.5.1",
    "pdfplumber": "0.11.9",
    "pdfminer.six": "20251230",
    "pymupdf": "1.27.2"
  },
  "ambiente": "local-allan-windows",
  "obs": "ATENÇÃO: requirements.txt pina pikepdf==9.7.0; produção pode ter versão diferente."
}
```

---

## 7.1 Parser e registro

| Item | Status | Localização |
|---|---|---|
| Arquivo do parser | **Existe** (160 linhas — auditoria diz 153, divergência menor) | [backend/services/parsers/bs2.py](backend/services/parsers/bs2.py) |
| Classe importada | **Sim** (`ParserBS2`) | [extrator_pdf.py:487](backend/services/extrator_pdf.py#L487) |
| Entrada em `PARSERS` dict | **Sim** (`'bs2': ParserBS2`) | [extrator_pdf.py:521](backend/services/extrator_pdf.py#L521) |
| Entrada em `_NOME_BANCO_EXIBICAO` | **Sim** (`'bs2': 'BS2'`) | [extrator_pdf.py:1164](backend/services/extrator_pdf.py#L1164) |
| Assinaturas em `_ASSINATURAS` | **Sim** (6 conjuntos) | [extrator_pdf.py:638-639](backend/services/extrator_pdf.py#L638-L639) |
| Filename hint para fallback | **Sim** (`'bs2': 'bs2'`) | [extrator_pdf.py:726](backend/services/extrator_pdf.py#L726) |

Assinaturas BS2 declaradas:

```python
('bs2', [['bs2 banco'], ['banco bs2'], ['bs2.com.br'], ['empresas.bs2'],
         ['bs2 s.a'], ['bs2 dtvm']]),
```

---

## 7.2 Fixture testado

- **Arquivo:** `backend/tests/fixtures/pdfs_reais/diag-2026-04-30/B2S.pdf`
- **SHA-256:** `cf781b936d6c1e827cbfe26cfed3a2ff1c03daa0cab8770bd58d8a69c0a6014b`
- **Cliente:** PROMOVE BRASIL DESENVOLVIMENTO E NEGOCIOS LTDA
- **CNPJ:** 10.175.617/0001-00
- **Período:** 01/01/2025 a 31/01/2025
- **Saldo Inicial:** R$ 72.500,88 / **Saldo Final:** R$ 81.947,02
- **Layout:** "Extrato Bancário - Empresas" do BS2 (cabeçalho `Data | Tipo | Descrição | Valor`)
- **Producer (pikepdf):** *(ver `passo4-catalogo.json`)*

---

## 7.3 Resultado do pipeline

| Métrica | Valor |
|---|---|
| `banco_detectado` | **`santander`** ❌ |
| `banco_detectado_pre_pipeline` | `santander` |
| `parser_class` (escolhido) | `ParserSantander` |
| `n_transacoes` | 46 |
| `saldo_final_informado` | R$ 81.947,02 (correto) |
| `saldo_inicial` | None (parser Santander não conseguiu extrair SI) |
| Avisos | "Santander: formato ContaMax não detectado — tentando parser Internet Banking Empresarial (N2)." |

**Observação importante:** o parser Santander (errado) retornou 46 transações que parecem coerentes com o saldo final. Isso é mais perigoso que retornar zero — a tabela final fica plausível e o usuário pode não notar que está consumindo dados de um parser errado, sem checagens específicas BS2 (saldos intermediários, sinal R$ negativo embutido na string `- R$`, etc.).

---

## 7.4 Por que a detecção foi para `santander` em vez de `bs2`?

### Causa raiz: assinatura `'santander'` solta + ordem das `_ASSINATURAS`

O algoritmo `detectar_banco()` ([extrator_pdf.py:702-705](backend/services/extrator_pdf.py#L702-L705)) itera `_ASSINATURAS` na ordem da lista e retorna o **primeiro** match. Cada match exige TODOS os termos do conjunto presentes (substring `in texto`).

Ordem relevante na lista (linha → assinatura):
- Linha 614: `('santander', [['contamax'], ['santander']])` ← **santander vem aqui**
- Linha 638: `('bs2', [['bs2 banco'], ['banco bs2'], ['bs2.com.br'], ['empresas.bs2'], ['bs2 s.a'], ['bs2 dtvm']])` ← **BS2 vem 24 linhas depois**

### Verificação concreta no texto do `B2S.pdf`

| Substring testada | Aparece no texto? | Onde |
|---|---|---|
| `'santander'` (assinatura legacy) | **SIM (1×)** | `'09/01/2025 ted enviada outra tit ib bco santander sa - karla pinto varasquim - r$ 3.811,97'` (descrição de uma TED enviada) |
| `'bs2 banco'` | NÃO | — |
| `'banco bs2'` | NÃO | — |
| `'bs2.com.br'` | **SIM** | via substring de `'e-mail: empresas@bancobs2.com.br'` (não exatamente "bs2.com.br" como token, mas substring) |
| `'empresas.bs2'` | **SIM (2×)** | `'empresas.bs2.com'` no rodapé das duas páginas |
| `'bs2 s.a'` | NÃO | — |
| `'bs2 dtvm'` | NÃO | — |

A assinatura BS2 é **válida e seria suficiente** (`'empresas.bs2'` daria match limpo), mas santander resolve primeiro porque vem antes na lista E porque a string `santander` solta é demasiado fraca: ela bate com qualquer descrição de transação que mencione "Bco Santander" (TED para terceiros com conta Santander).

---

## 7.5 Sugestão de fix (NÃO IMPLEMENTAR NESTA SESSÃO)

Duas opções viáveis, em ordem de preferência:

### Fix A — mover BS2 para ANTES de santander legacy (mínimo)

Recolocar o tuple `('bs2', [...])` na lista `_ASSINATURAS` antes do tuple `('santander', ...)`. Como as assinaturas BS2 são compostas/específicas (`'empresas.bs2'`, `'bs2 banco'`, etc.), não há risco de falso positivo BS2 em PDFs Santander.

**Risco:** baixo. Validar revertendo em testes Santander existentes.

### Fix B — refinar assinatura legacy do Santander (estrutural)

Substituir `['santander']` solto por algo composto, ex.:

```python
('santander', [
    ['contamax'],
    ['banco santander'],                  # mais restritivo
    ['santander', 'extrato'],             # exige "santander" + "extrato"
    ['santander', 'agência'],             # ou "santander" + "agência"
]),
```

A motivação é a mesma do fix de mercado_pago já aplicado na Sessão 6 (descrito em [AUDITORIA_TECNICA_CONTROLLO.md §7.6](AUDITORIA_TECNICA_CONTROLLO.md)): "termo único" da assinatura precisa ser específico do banco emissor, não algo que pode aparecer em descrições de transações de terceiros.

**Risco:** médio. PDFs Santander DLS / "santander pf" / outros formatos podem falhar a detecção se nenhum dos novos termos aparecer no texto. Precisa validar contra todos os fixtures `santander*` existentes.

### Recomendação

Aplicar **Fix A primeiro** (cirúrgico, baixo risco). Considerar **Fix B** numa sprint dedicada de "endurecer assinaturas fracas" (também afetaria possivelmente `dcto.` para Bradesco, etc.).

---

## 7.6 BS2 parser: foi avaliado nesta sessão?

**Não.** Como o pipeline nunca chegou a invocar o `ParserBS2` (devido ao mis-route para Santander), não há sinal de qualidade do parser BS2 nesta sessão. Para validar a qualidade do parser BS2 em si:

1. Aplicar Fix A ou B (não nesta sessão)
2. Re-rodar pipeline contra `B2S.pdf`
3. Confirmar que `banco_detectado = 'bs2'` e contagem de tx + saldos
4. Checar se as 46 tx (que o parser Santander conseguiu extrair "por sorte") batem com as tx que o parser BS2 produziria

**Pendência registrada para próxima sprint.**
