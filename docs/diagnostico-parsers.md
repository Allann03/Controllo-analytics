# DIAGNÓSTICO TÉCNICO DOS PARSERS DE EXTRATO — CONTROLLO
## + Prompt de Execução Blindado para Claude Code

> **Este documento tem 2 partes.**
> - **Parte 1 (DIAGNÓSTICO):** Achados técnicos por banco. Serve de referência para a engenharia e de contexto para o Claude Code. Coloque no repositório em `docs/diagnostico-parsers.md`.
> - **Parte 2 (PROMPT):** Prompt blindado para executar os fixes no Claude Code, um banco por vez.

> **Amostras de texto cru:** junto deste documento há uma pasta `samples/` com o texto extraído via `pdfplumber` de 1 PDF representativo de cada padrão identificado. **Essa pasta é o ground truth.** O Claude Code deve cruzar cada regra de parser com o conteúdo destes arquivos.

---

# PARTE 1 — DIAGNÓSTICO TÉCNICO

## Sumário dos problemas

30 PDFs analisados. **8 padrões distintos** de extrato identificados, **5 com bugs confirmados**, **1 com bug já conhecido do usuário (Bradesco Net Empresas)**, **3 PDFs escaneados que precisam OCR**. Detalhe por banco:

| # | Banco/Formato | Status | Amostra de referência |
|---|---------------|--------|-----------------------|
| 1 | Bradesco Net Empresas | **BUG: descrição sanduíche 3 linhas** | `samples/bradesco_net_empresas_A.txt` + `_B.txt` |
| 2 | Itaú Empresas moderno (N2/N3) | **BUG: "SALDO TOTAL DISPONÍVEL DIA" virando transação + descrição sanduíche** | `samples/itau_empresas_n2_sanduiche.txt` |
| 3 | Itaú Empresas "Validação de saldos" | **BUG: razão social quebrada em 2 linhas** | `samples/itau_empresas_validacao_saldos.txt` |
| 4 | Itaú Empresas antigo (40KB) | **LAYOUT NÃO SUPORTADO: data DD/MM sem ano** | `samples/itau_empresas_antigo.txt` |
| 5 | Itaú mensal (PF/PJ tradicional) | **LAYOUT NÃO SUPORTADO: extrato mensal com sumário** | `samples/itau_mensal_sumario.txt` |
| 6 | Itaú escaneado (3 PDFs) | **SEM TEXTO: precisa OCR** | n/a |
| 7 | Santander IB Empresarial antigo (DLS) | OK aparente (revalidar) | `samples/santander_ib_antigo.txt` |
| 8 | Santander IB Empresarial **novo** | **BUG: datas descendentes, sinal `- R$` com espaço, bullet `•` no início** | `samples/santander_ib_novo_desc.txt` |
| 9 | Santander Extrato Consolidado Inteligente | **BUG: 1ª pág. toda de marketing, transações começam depois** | `samples/santander_consolidado.txt` |
| 10 | Santander por dia da semana | **LAYOUT NÃO SUPORTADO: sem data por linha, só header do dia** | `samples/santander_por_dia.txt` |
| 11 | C6 Bank | **BUG: duas colunas de data (lançamento vs contábil), ano implícito no header da seção** | `samples/c6_duas_datas.txt` |
| 12 | Stone | **BUG: contraparte em linha separada (acima OU abaixo da linha de dados)** | `samples/stone_contraparte.txt` |
| 13 | SumUp | **BUG: descrição sanduíche 2-3 linhas** | `samples/sumup_sanduiche.txt` |
| 14 | Sicredi N2 | OK aparente, atenção a "SALDO" sem data no topo | `samples/sicredi_n2.txt` |

---

## 1. Bradesco Net Empresas — descrição em 3 linhas (sanduíche)

**Sintoma reportado:** "valor sai certo, nome da transação errado."

**Causa-raiz confirmada:** Cada lançamento ocupa **3 linhas distintas** e o parser provavelmente pega apenas uma delas.

### Estrutura real:

```
Linha N-1:  TRANSFERENCIA PIX                          ← TIPO (descrição principal)
Linha N  :  01/12/2025 7079482 2.146,58 80.165,90      ← DADOS (data | doc | valor | saldo)
Linha N+1:  REM: RENATA VELASCO WICHMA 01/12           ← DETALHE (contraparte/complemento)
```

### Variantes existentes no MESMO extrato:

**Variante A — Sanduíche (maioria):** 3 linhas conforme acima.

**Variante B — Inline:** tudo na mesma linha. Exemplo em `samples/bradesco_net_empresas_B.txt` linha 27:
```
RENTAB.INVEST FACILCRED* 5913274 5,61 95.775,77
```

**Variante C — Data inline + tipo na mesma linha:** `samples/bradesco_net_empresas_B.txt` linha 49:
```
05/12/2025 VENDA CARTAO DE CREDITO 8300189 2.569,75 94.121,33
```

### Heurística de parsing correta:

```
Regex para LINHA DE DADOS:
  ^(\d{2}/\d{2}/\d{4})?\s*.*?\s+(-?[\d.]+,\d{2})\s+(-?[\d.]+,\d{2})$

Se a linha atual bate na regex:
  - tipo  = linha anterior (se for texto puro em MAIÚSCULAS, sem data)
  - data  = grupo 1 (pode estar ausente = herdar da anterior)
  - valor = grupo 2 (penúltimo número)
  - saldo = grupo 3 (último número)
  - detalhe = linha seguinte (se for texto puro)
  - descrição_final = f"{tipo} — {detalhe}" ou {tipo} somente se detalhe não existir
```

### Validação de acerto:

Contando lançamentos em `samples/bradesco_net_empresas_A.txt` manualmente: **10 lançamentos** na seção principal (entre 26/12/2025 e 30/01/2026). Parser deve retornar 10 com descrição completa. Exemplos esperados:

| Data | Descrição esperada | Valor | Saldo |
|------|-------------------|-------|-------|
| 05/01/2026 | ENCARGOS LIMITE DE CRED — ENCARGO - 16,49% | -45,20 | -963,58 |
| 05/01/2026 | IOF S/ UTILIZACAO LIMITE | -4,12 | -967,70 |
| 07/01/2026 | TRANSFERENCIA PIX — REM: CW TOUR LTDA 07/01 | 1.000,00 | 32,30 |
| 12/01/2026 | PAGTO ELETRON COBRANCA — 070548543401100503BRADESCO ADMIN | -595,43 | -563,13 |
| 12/01/2026 | CARTAO CREDITO ANUIDADE | -38,00 | -601,13 |
| 15/01/2026 | TARIFA BANCARIA — CESTA PJ FACIL 1 | -168,50 | -769,63 |
| 30/01/2026 | TRANSFERENCIA PIX — REM: CW TOUR LTDA 30/01 | 1.500,00 | 730,37 |
| 30/01/2026 | TITULO DE CAPITALIZACAO — CAPITALIZACAO 1235 0050170217-0 | -500,00 | 230,37 |
| 30/01/2026 | APLIC.INVEST FACIL | -229,37 | 1,00 |

**Linhas a IGNORAR:** "SALDO ANTERIOR", "Total", "Os dados acima têm como base", "Últimos Lançamentos", cabeçalhos "Data Lançamento...".

---

## 2. Itaú Empresas moderno (N2/N3) — SALDO virando transação + descrição sanduíche

**Sintoma reportado:** "está lendo informações irrelevantes como detalhes ou explicações de sigla."

**Causa-raiz confirmada:** Dois bugs distintos no mesmo parser:

### BUG 2a: "SALDO TOTAL DISPONÍVEL DIA" sendo tratado como transação

Em `samples/itau_empresas_n2_sanduiche.txt` aparecem linhas como:
```
26/06/2025 SALDO TOTAL DISPONÍVEL DIA 20.456,40
02/07/2025 SALDO TOTAL DISPONÍVEL DIA 20.177,41
15/07/2025 SALDO TOTAL DISPONÍVEL DIA 457,84
```

Formato idêntico ao de uma transação (data + descrição + valor) **mas é um saldo intermediário, não um lançamento**. Se o parser não filtrar, cada dia vira um "lançamento" falso de valor = saldo do dia.

**Fix:** adicionar "SALDO TOTAL DISPONÍVEL DIA" à lista de descrições a filtrar (provavelmente em `ParserBase._is_linha_saldo()` ou equivalente). Regra sugerida:
```python
PADROES_SALDO = [
    r"SALDO\s+TOTAL\s+DISPON[IÍ]VEL\s+DIA",
    r"SALDO\s+DO\s+DIA",
    r"SALDO\s+ANTERIOR",
    r"^SALDO$",  # Sicredi N2 tem só "SALDO 548,77" no topo
    r"S\s*A\s*L\s*D\s*O",  # Itaú antigo tem "S A L D O" espaçado (ver item 4)
]
```

### BUG 2b: Descrição em 3 linhas (sanduíche)

Várias transações têm a descrição quebrada em até 3 linhas. Exemplos em `samples/itau_empresas_n2_sanduiche.txt`:

```
Linhas 9-11:
   RENDIMENTO APLICAÇÃO                    ← descrição parte 1
   02/07/2025 AUTOMÁTICA REND PAGO APLIC 0,01   ← data + desc parte 2 + valor
   AUT MAIS                                ← descrição parte 3

Descrição correta: "RENDIMENTO APLICAÇÃO AUTOMÁTICA REND PAGO APLIC AUT MAIS"
```

```
Linhas 26-28:
   SISPAG FORNECEDORES PIX QR-             ← desc parte 1 (terminou em hífen!)
   30/07/2025 -47,41                       ← data + valor (sem descrição inline)
   CODE                                    ← desc parte 2

Descrição correta: "SISPAG FORNECEDORES PIX QR-CODE"
Nota: o "QR-" seguido de "CODE" indica junção SEM espaço (hifenização).
```

```
Linhas 33-35:
   SISPAG FORNECEDORES                     ← desc parte 1
   06/08/2025 -54,83                       ← data + valor
   VIVOFIXONA                              ← desc parte 2

Descrição correta: "SISPAG FORNECEDORES VIVOFIXONA"
```

### Heurística de parsing correta:

```
Regex linha de dados (formato com CNPJ opcional):
  ^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d.]+,\d{2})(?:\s+(-?[\d.]+,\d{2}))?$

Fluxo:
  1. Quando achar linha de dados que bate na regex:
     - Olhar linha_anterior — se for texto puro UPPERCASE (sem data, sem valor numérico) → é parte da descrição (TIPO)
     - Olhar linha_seguinte — se for texto puro (sem data, sem valor) → é parte da descrição (complemento)
  2. Filtrar linhas que contenham "SALDO TOTAL DISPONÍVEL DIA" — são saldos, não transações.
  3. Descrição final = concatenar [tipo, meio, complemento] removendo quebras de hífen ("QR-" + "CODE" = "QR-CODE" sem espaço).
```

### Validação de acerto para Itaú Empresas N2:

Contando no `samples/itau_empresas_n2_sanduiche.txt` (somente página 1, linhas 6-40):
- **Transações reais:** 10 (desconsiderando "SALDO ANTERIOR" e 6 "SALDO TOTAL DISPONÍVEL DIA")
- Se parser retorna >10 na página 1, está criando transações falsas.
- Se retorna <10 ou descrições truncadas (ex.: "AUTOMÁTICA REND PAGO APLIC" sem "RENDIMENTO APLICAÇÃO AUT MAIS"), parser está perdendo contexto.

---

## 3. Itaú Empresas "Validação de saldos" — razão social quebrada

**Arquivo:** `samples/itau_empresas_validacao_saldos.txt`

Este layout é o **mesmo do item 2 (Itaú Empresas moderno)** com um agravante: a **razão social também está quebrada** em 2-3 linhas.

Exemplo (linhas 9-11 do arquivo):
```
RECEBIMENTO REDE MAST REDECARD INSTITUICAO DE
01/12/2025 01.425.787/0001-04 1.038,00
CD0045543844 PAGAMENTO S.A.
```

- **Tipo/operação:** "RECEBIMENTO REDE MAST" (linha 1)
- **Data:** 01/12/2025 (linha 2)
- **CNPJ:** 01.425.787/0001-04 (linha 2)
- **Valor:** 1.038,00 (linha 2)
- **Razão social (parte 1):** "REDECARD INSTITUICAO DE" (linha 1, continuação)
- **Código operação:** CD0045543844 (linha 3)
- **Razão social (parte 2):** "PAGAMENTO S.A." (linha 3, complemento)
- **Razão social FINAL:** "REDECARD INSTITUICAO DE PAGAMENTO S.A."

Parser precisa reconhecer que a razão social pode se estender para a linha seguinte.

---

## 4. Itaú Empresas antigo (40KB) — formato compacto legado

**Arquivo:** `samples/itau_empresas_antigo.txt` (layout diferente do N2/N3)

```
Cabeçalho: Data Lançamento Ag./Origem Valor (R$) Saldo (R$)
Formato:   01/04 SISPAG FORNECEDORES 9028 -10.000,00
           01/04 TAR/CUSTAS COBRANCA -21,00
           01/04 S A L D O -142.677,53
```

### Características únicas:
- **Data DD/MM sem ano:** o ano vem do cabeçalho "Extrato de 01/04/2025 até 30/04/2025" (linha 4 do PDF)
- **"S A L D O" com espaços:** marcador de saldo do dia, não transação. Precisa ser filtrado.
- **Último campo:** número de página ("1", "2"...) aparece como linha solta — deve ser ignorado
- **"Ag./Origem"** é um código (ex.: "9028", "9773") que fica entre a descrição e o valor

### Ação recomendada:
Se o Controllo **não tem parser** para este layout (provável — o briefing só cita `parser_itau_mensal` e `itau_empresas_n2`), criar `parser_itau_empresas_legado.py`. Detecção pela presença do cabeçalho "Ag./Origem" + datas DD/MM sem ano + "Itaú Empresas" no título.

---

## 5. Itaú mensal — extrato com sumário de categorias

**Arquivo:** `samples/itau_mensal_sumario.txt`

Este é o extrato **mensal tradicional** do Itaú (PF/PJ), com layout completamente diferente:

### Estrutura:
- **Páginas iniciais:** endereço do cliente, sumário do mês com entradas/saídas categorizadas em % ("Outras entradas 94% 1.001.704,76")
- **Cabeçalho de transações:** "A =agendamento | data descrição entradas R$ saídas R$ saldo R$"
- **Transações:** `01/04 Sispag Fornecedores 10.000,00-` (DD/MM sem ano, valor com sinal NO FINAL `-`)
- **Ano:** implícito no cabeçalho ("abr 2025 Minha conta...")

### Características problemáticas:
- Legenda de siglas misturada com transações: "B = ações movimentadas", "C = crédito a compensar", "D = débito a compensar" — **se o parser incluir essas linhas, vira o "lixo" reportado pelo usuário.**
- Sumário com percentuais tem valores que **não são transações**: "Transferências, DOCs e TEDs 5% 48.827,96" — isto é **total agregado do mês**, não lançamento individual.

### Ação recomendada:
Verificar se `parser_itau_mensal` existe e cobre este layout. Se existir, validar que filtra:
1. Legenda (linhas começadas por letra maiúscula + `=`)
2. Sumário de categorias com % (linhas contendo `\d+%`)
3. "saldo em DD/MM/YY" (informativo, não transação)

---

## 6. Itaú escaneados — precisa OCR

**3 arquivos:** `Itaú 07828-5.pdf`, `Itaú 07828-5_1.pdf`, `Itaú 09089-2.pdf`.

`pdfplumber` retorna string vazia. São PDFs compostos por imagens (foto do extrato).

### Opções:
- **(a)** Integrar `easyocr` ou `pytesseract` no pipeline (a auditoria menciona `easyocr` como dependência opcional comentada no `requirements.txt`).
- **(b)** Rejeitar explicitamente com mensagem clara: "PDF parece escaneado. Re-exporte do Itaú em formato texto ou use OCR externo."

Recomendação: **(b)** é o fix seguro de curto prazo. **(a)** fica para sprint futura.

---

## 7. Santander IB Empresarial antigo (DLS) — OK aparente

**Arquivo:** `samples/santander_ib_antigo.txt`

Layout limpo:
```
Cabeçalho: Data Histórico Documento Valor (R$) Saldo (R$)
Linha:     02/12/2025 PIX ENVIADO ENIVALDO CARLIN 000000 -1.000,00
```

Não identifiquei bug óbvio. Validar que o parser atual acerta (revalidar após fixes dos itens 8/9/10 para não regredir).

---

## 8. Santander IB Empresarial NOVO — datas descendentes + sinal peculiar

**Arquivo:** `samples/santander_ib_novo_desc.txt`

### Características que quebram parsers convencionais:

**1. Datas em ordem DESCENDENTE** (31/01 → 30/01 → 29/01 → ...):
```
31/01/2025 Saldo do dia R$ 0,00
• 31/01/2025 Resgate contamax automatico R$ 217,40
• 31/01/2025 Pix enviado Joice roberta alves - R$ 862,40
30/01/2025 Saldo do dia R$ 0,00
• 30/01/2025 Aplicacao contamax - R$ 480,00
```

**2. Bullet unicode `•` (caractere especial) no início das linhas de transação**, mas NÃO nas linhas de "Saldo do dia".

**3. Sinal de débito é `- R$` com espaço entre sinal e "R$"** (incomum!):
- Crédito: `R$ 217,40`
- Débito: `- R$ 862,40`

**4. "Saldo do dia" antecede os lançamentos daquele dia** (não sucede).

### Heurística correta:

```
Para cada linha:
  - Começa com bullet '•'? → é transação. Parsear: data + descrição + valor (com sinal via "- R$").
  - Não começa com bullet e tem "Saldo do dia"? → filtrar (é saldo).
  - Caso contrário: provavelmente cabeçalho/footer, ignorar.

Para o valor: detectar "- R$" (com espaço) como negativo antes de aplicar conversão.

Após parsear, reordenar transações por data ASCENDENTE antes de calcular saldos progressivos.
```

---

## 9. Santander Extrato Consolidado Inteligente — página 1 é marketing

**Arquivos:** `Santander N1/N2/N3.pdf` e `pdf_gerado (1).pdf`. Amostra: `samples/santander_consolidado.txt`.

### Características:
- **Página 1 e 2 inteiras** = texto institucional/marketing ("Getnet: receba suas vendas...", "Cobranças: emita boletos...").
- Transações começam apenas a partir da **página 3 em diante** (total do arquivo: 14-17 páginas).
- Se o parser processa página por página e abandona na primeira com 0 transações, retorna vazio.

### Ação recomendada:
- Parser deve **percorrer todas as páginas** antes de decidir se o PDF está vazio.
- Adicionar regex de detecção da tabela real de lançamentos (buscar cabeçalho "Data Histórico..." ou "Movimentação...") e pular tudo antes dele.

---

## 10. Santander "por dia da semana" — layout novo sem data por linha

**Arquivos:** `Empresarial 3.pdf`, `junho 2025.pdf`. Amostra: `samples/santander_por_dia.txt`.

```
? Sexta, 31 de outubro de 2025                       ← header do dia
RESGATE CONTAMAX AUTOMATICO CREDITO R$ 2.534,53       ← transação sem data própria
PIX ENVIADO DEBITO R$ 600,00                          ← transação sem data própria
...
? Quinta, 30 de outubro de 2025                       ← novo dia
...
```

### Características:
- Data aparece **apenas no cabeçalho do dia** em formato textual ("Sexta, 31 de outubro de 2025").
- Cada transação tem só: DESCRIÇÃO + CREDITO/DEBITO + R$ VALOR.
- Prefixo `?` (bullet renderizado como `?` por encoding) nos headers de dia.

### Ação recomendada:
- Novo parser ou variante do parser Santander.
- Converter data textual em português ("31 de outubro de 2025" → "31/10/2025") — tabela de meses em PT.
- Sinal do valor vem da palavra "CREDITO"/"DEBITO" explícita.

---

## 11. C6 Bank — duas colunas de data + seção por mês

**Arquivo:** `samples/c6_duas_datas.txt` (nome do PDF alerta: "Atenção ao ano").

### Bugs confirmados:

**1. Duas colunas de data:**
```
04/04 04/04 Entrada PIX Pix recebido de POUSADA NANAI LTDA R$ 628,00
      ↑     ↑
      data lanç.   data contábil  (podem divergir)

20/04 22/04 Saída PIX Pix enviado para GUILHERME FRANCA REIS -R$ 1.500,00
```

Parser precisa saber qual data usar (geralmente "data lançamento" = a primeira).

**2. Ano implícito no header da seção:**
```
Abril 2025 ( 03/04/2025 - 30/04/2025 ) Entradas: R$ 9.529,75 ● Saídas: R$ 6.350,89
```

Datas "04/04" dentro desta seção são 04/04/2025. Parser precisa **trackear a seção ativa** ao descer as linhas.

**3. "Saldo do dia DD/MM/YY R$ ..." entre transações:**
```
Saldo do dia 04/04/25 R$ 631,42
```
Precisa ser filtrado.

### Heurística correta:

```
Estado: secao_ano = None, secao_mes = None

Para cada linha:
  - Match "^(Abril|Maio|...)(?:\s+de\s+)?\s*(\d{4})\s*\(" → atualizar estado
  - Match "Saldo do dia" → filtrar
  - Match "^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(Entrada|Saída)\s+..." → transação:
      - data_lancamento = grupo 1 + "/" + secao_ano
      - data_contabil = grupo 2 + "/" + secao_ano
      - tipo_operacao = grupo 3
      - valor_sinal = "-R$" → negativo, "R$" → positivo
```

---

## 12. Stone — contraparte em linha separada

**Arquivo:** `samples/stone_contraparte.txt`

### Estrutura (6 colunas no layout): DATA | TIPO | DESCRIÇÃO | VALOR | SALDO | CONTRAPARTE

Mas a extração do `pdfplumber` serializa de forma irregular. Contraparte aparece em linha **separada**, **acima OU abaixo** da linha de dados:

**Variante A — Contraparte ABAIXO:**
```
30/09/25 Sa?da Tarifa - R$ 0,07 R$ 62,85          ← linha de dados
ALLAN ALCANTARA B OLIVEIRA                         ← contraparte
30/09/25 Entrada R$ 10,00 R$ 62,85                ← nova linha de dados (sem descrição inline!)
Pix | Maquininha                                   ← descrição na próxima linha
```

**Variante B — Contraparte ACIMA:**
```
CHATELET PARTICIPACOES LTDA                        ← contraparte
30/09/25 Sa?da - R$ 5.500,00 R$ 2,40              ← linha de dados
Transferência | Pix                                ← descrição
```

**Variante C — Contraparte 2 linhas:**
```
MARTINS COM DE PROD E                              ← contraparte parte 1
30/09/25 Entrada ACESSORIOS VETERINARIOS LTDA R$ 5,00 R$ 5.502,40    ← dados + contraparte parte 2 (!)
Transferência | Pix                                ← descrição
```

Aqui a contraparte "MARTINS COM DE PROD E ACESSORIOS VETERINARIOS LTDA" foi partida: parte 1 na linha acima, parte 2 **dentro** da linha de dados (!).

### Heurística correta:

O parser Stone é o mais complexo do diagnóstico. Precisa **olhar 2 linhas antes + 2 linhas depois** da linha de dados e decidir qual é descrição e qual é contraparte.

Recomendação: **não usar `extract_text()` — usar `extract_tables()` do pdfplumber**, que respeita as colunas visuais do PDF. O Stone provavelmente emite PDF com tabela nativa.

---

## 13. SumUp — descrição sanduíche

**Arquivo:** `samples/sumup_sanduiche.txt`

```
Transferência Pix enviada                           ← descrição parte 1
01-02-2026 143668952229 R$ -233,56 R$ 0,00        ← data + doc + valor + saldo
Dukka Suplementos Ltda                              ← descrição parte 2 (contraparte)
```

Mesmo padrão sanduíche do Bradesco Net Empresas. Aplicar mesma heurística.

Peculiaridade: **data com hífen** `01-02-2026` (não `/`). Parser precisa aceitar ambos os separadores.

Arquivo nomeado `account_statement-UUID.pdf` — padrão de nomenclatura do SumUp Brasil.

---

## 14. Sicredi N2 — OK com atenção

**Arquivo:** `samples/sicredi_n2.txt`

Layout limpo. Único ponto de atenção:
```
Linha 7: SALDO 548,77
```

"SALDO" sem data, sem valor de saldo anterior marcado explicitamente. Parser precisa reconhecer isso como **saldo anterior** (valor inicial), não como transação.

---

## 15. Detecção automática de banco

**Bug potencial:** a auditoria menciona assinaturas em `_ASSINATURAS` (extrator_pdf.py) para detectar banco. Dado o número de **layouts dentro do mesmo banco** (Santander: 4 layouts; Itaú: 5 layouts), a detecção provavelmente está **colapsando layouts diferentes num parser único**.

**Solução:** a função de detecção precisa retornar não só o banco, mas o **layout específico**:

```python
# Exemplo de detecção refinada para Santander
def detectar_santander_layout(texto):
    if "EXTRATO CONSOLIDADO INTELIGENTE" in texto:
        return "santander_consolidado"
    if "Internet Banking Empresarial" in texto:
        if "Saldo do dia" in texto and "•" in texto:
            return "santander_ib_novo"
        return "santander_ib_antigo"
    if re.search(r"(Segunda|Ter[çc]a|Quarta|Quinta|Sexta|S[aá]bado|Domingo),\s+\d+\s+de\s+\w+", texto):
        return "santander_por_dia"
    return "santander_desconhecido"
```

---

# PARTE 2 — PROMPT BLINDADO PARA CLAUDE CODE

> **Instruções de uso:** execute **1 item por sessão**. Recomenda-se a ordem abaixo (mais impacto, menor risco primeiro). Para cada item, cole o prompt inteiro e troque apenas a seção `<BANCO_DO_ITEM>`.

## Ordem recomendada de execução:

| Ordem | Item | Por quê primeiro |
|-------|------|------------------|
| 1 | **Bradesco Net Empresas** | Bug mais simples (sanduíche 3 linhas), usuário já confirmou sintoma, heurística clara, padrão que se replica em outros bancos |
| 2 | **Itaú Empresas moderno (N2/N3)** | Bug de "SALDO DISPONÍVEL DIA" é trivial; sanduíche reaproveita lógica do item 1 |
| 3 | **Itaú Empresas "Validação de saldos"** | Mesmo parser do item 2, adiciona razão social quebrada |
| 4 | **Santander IB Novo (datas descendentes)** | Fechamento da família Santander IB |
| 5 | **Santander Consolidado Inteligente** | Alto volume (14-17 páginas), mas fix é localizado (pular marketing) |
| 6 | **SumUp** | Reaproveita heurística do item 1 |
| 7 | **C6 — duas datas + seção por mês** | Bug importante mas complexo |
| 8 | **Santander por dia da semana** | Layout radicalmente diferente, pode exigir novo parser |
| 9 | **Itaú Empresas antigo (40KB)** | Novo parser, baixa prioridade |
| 10 | **Itaú mensal (sumário)** | Novo parser, baixa prioridade |
| 11 | **Stone — contraparte** | Bug complexo, possivelmente migrar para `extract_tables` |
| 12 | **Itaú escaneados (3 PDFs)** | Decisão: rejeitar com mensagem ou integrar OCR (sprint futura) |

---

## PROMPT (cole no Claude Code)

```
<BANCO_DO_ITEM>
Item desta sessão: Bradesco Net Empresas

Documento-fonte: docs/diagnostico-parsers.md, Parte 1, seção 1
(trocar para outra seção quando for executar outro item — NÃO executar múltiplos na mesma sessão)
</BANCO_DO_ITEM>

=================================================================
CONTEXTO CRÍTICO — LEIA ANTES DE QUALQUER COISA
=================================================================

Você é engenheiro(a) sênior trabalhando no Controllo SaaS. Este repositório
tem parsers de extrato bancário em backend/services/parsers/ que funcionam
para a maioria dos casos. Sua tarefa é corrigir UM parser específico, com
base no diagnóstico em docs/diagnostico-parsers.md.

Já aconteceu de um agente apagar código funcional neste repositório.
As regras abaixo são absolutas.

=================================================================
REGRAS ABSOLUTAS (violação = falha da sessão)
=================================================================

R1 — ESCOPO CIRÚRGICO
- Você pode criar arquivos NOVOS de teste.
- Você pode editar o arquivo do parser específico do item (ex.: bradesco_net_empresas.py).
- Você pode editar o arquivo extrator_pdf.py SE E SOMENTE SE a mudança
  for adicionar detecção/mapeamento do layout do item atual.
- Você NÃO PODE tocar:
  * Nenhum outro parser que não é o do item atual.
  * services/motor_classificacao.py
  * services/gerador_excel*.py
  * Qualquer coisa em routers/, models.py, main.py, frontend/*.
  * requirements.txt, package.json, Dockerfile, .env*.
- Se ver bug em parser vizinho durante a leitura, anote em comentário
  "# TODO-DIAGNOSTICO" e siga em frente. NÃO corrija.

R2 — NÃO DESTRUTIVO
- Proibido: rm -rf, git reset --hard, git clean -fd, truncar arquivo
  existente (reescrever do zero um arquivo que tem conteúdo).
- Edite o parser por str_replace/patch localizado, preservando estilo
  existente (indentação, aspas, convenções de nome).
- Se precisar reestruturar o parser inteiro, PARE E PERGUNTE.

R3 — CHECKPOINT GIT OBRIGATÓRIO ANTES DE QUALQUER EDIÇÃO
Execute e mostre output:
  git status
  git rev-parse HEAD
  git checkout -b parsers/<nome-slug-do-banco>

Se git status mostrar sujeira prévia, PARE E PERGUNTE.

R4 — USE AS AMOSTRAS COMO GROUND TRUTH
Em docs/diagnostico-parsers/samples/ existe um arquivo .txt com o texto
extraído (via pdfplumber, mesma lib do Controllo) do PDF representativo
do layout. Este arquivo É A VERDADE. Seu parser corrigido deve produzir
transações consistentes com o que está nesse arquivo.

Se não existir um PDF real de teste no repositório para este banco, use
o .txt de ground truth como entrada de teste simulada: salve um fixture
tests/fixtures/<banco>_raw.txt e escreva um teste que:
  1. Lê o fixture.
  2. Passa pelo método interno do parser que faz parsing a partir de
     texto (não do PDF).
  3. Valida transações contra lista esperada hardcoded no teste.

Se o parser só aceita path de PDF, crie um wrapper interno
`_parse_texto(texto: str) -> list[dict]` que o método `extrair()` chama
depois de extrair texto. Isso é refactor mínimo aceitável.

R5 — TESTES OBRIGATÓRIOS ANTES E DEPOIS
ANTES de editar:
  cd backend && pytest tests/ -x --tb=short
  (se a suíte já quebra, PARE E PERGUNTE — não é seu escopo consertar)

DEPOIS de cada commit:
  pytest tests/ -x --tb=short
  (TUDO que passava antes deve continuar passando)

No FINAL:
  pytest tests/ --tb=short
  (suíte completa verde)

R6 — SERVIDOR SOBE NO FINAL
Rode o backend local:
  cd backend && uvicorn main:app --reload --port 8001 &
Aguarde 15s, faça curl http://localhost:8001/api/health, confirme JSON
de saúde OK. Mate o processo.

R7 — PLANO ANTES DE CÓDIGO (OBRIGATÓRIO)
Antes de editar qualquer arquivo, publique:

=== PLANO — Parser <banco> ===
Arquivo do parser: backend/services/parsers/<arquivo>.py
Tipo da mudança: [correção|novo parser]

Bugs identificados (do diagnóstico):
 - Bug X: <descrição curta>
 - Bug Y: <descrição curta>

Mudanças planejadas (diff conceitual):
 - adicionar padrão regex ... em _is_linha_saldo
 - reescrever método _parse_linha para olhar linha anterior/seguinte
 - adicionar wrapper _parse_texto(texto: str) para testabilidade

Testes a criar em backend/tests/test_parser_<banco>.py:
 - test_<caso>_descricao_sanduiche: valida concatenação 3 linhas
 - test_<caso>_filtra_saldo_diario: valida filtro
 - test_<caso>_transacoes_esperadas: valida N transações contra lista

Fixture de ground truth:
 - backend/tests/fixtures/<banco>_raw.txt (copiar de docs/diagnostico-parsers/samples/<arq>.txt)

Linhas estimadas tocadas: ~N

=== FIM DO PLANO ===

Espere 60s. Se eu não objetar, siga. Caso contrário, ajuste e republique.

R8 — PARE E PERGUNTE
Use "DECISÃO NECESSÁRIA:" no chat e espere resposta quando:
 - O parser precisar de dependência nova não listada em requirements.txt.
 - O fix exigir mudar assinatura pública de classe/função que outros
   parsers também usam (ex.: ParserBase._is_linha_saldo).
 - A amostra de ground truth não estiver disponível.
 - A suíte de testes já estiver quebrada antes de você começar.
 - O layout identificado for um caso realmente novo e exigir criar
   parser do zero (ver quando exigido pelo diagnóstico).

R9 — PROIBIDO "PARECE QUE FUNCIONA"
 - Proibido TODO, NotImplementedError, pass no caminho principal.
 - Proibido except Exception: pass.
 - Proibido # type: ignore novo sem comentário.
 - Cada teste precisa ter assert real contra valor esperado.

R10 — RELATÓRIO FINAL

=== RELATÓRIO — Parser <banco> ===
Branch: parsers/<slug>
Commits:
 - <hash> <mensagem>
Arquivos editados:
 - <lista>
Testes novos: N (todos passando)
Baseline antes: X/Y
Baseline depois: X'/Y'
Backend sobe e /api/health OK: SIM/NÃO

Bugs corrigidos:
 - <lista>

Bugs conhecidos pendentes (não-escopo):
 - <lista>

Regressões introduzidas: NENHUMA ou <lista + plano>

Pronto para PR: SIM/NÃO
=== FIM ===

NÃO rode git push. NÃO abra PR. NÃO avance para outro banco.

=================================================================
SEQUÊNCIA DE EXECUÇÃO
=================================================================

1. Leia docs/diagnostico-parsers.md (toda a Parte 1) para contexto geral.
2. Leia a seção específica do seu item (ex.: seção 1 para Bradesco Net).
3. Leia docs/diagnostico-parsers/samples/<arquivo>.txt para ground truth.
4. Execute R3 (checkpoint git). Mostre saída.
5. Rode baseline de testes.
6. Leia o arquivo do parser em backend/services/parsers/.
7. Publique plano (R7).
8. Aguarde 60s.
9. Execute em commits pequenos.
10. Testes a cada commit.
11. Smoke test final (R6).
12. Relatório (R10).
13. PARE.

Vá.
```

---

# PARTE 3 — ORGANIZAÇÃO RECOMENDADA DO REPOSITÓRIO

Antes de rodar o prompt, organize o repositório assim:

```
controllo/
├── docs/
│   ├── diagnostico-parsers.md              ← este documento
│   └── diagnostico-parsers/
│       └── samples/
│           ├── bradesco_net_empresas_A.txt
│           ├── bradesco_net_empresas_B.txt
│           ├── itau_empresas_n2_sanduiche.txt
│           ├── itau_empresas_validacao_saldos.txt
│           ├── itau_empresas_antigo.txt
│           ├── itau_mensal_sumario.txt
│           ├── santander_ib_antigo.txt
│           ├── santander_ib_novo_desc.txt
│           ├── santander_consolidado.txt
│           ├── santander_por_dia.txt
│           ├── c6_duas_datas.txt
│           ├── stone_contraparte.txt
│           ├── sumup_sanduiche.txt
│           └── sicredi_n2.txt
```

Comando para preparar tudo (rodar na raiz do repo):
```bash
mkdir -p docs/diagnostico-parsers/samples
# Copiar este arquivo para docs/diagnostico-parsers.md
# Copiar as amostras .txt para docs/diagnostico-parsers/samples/
git add docs/
git commit -m "docs: diagnostico tecnico dos parsers problematicos com ground truth"
```

**Depois** abra o Claude Code, cole o prompt da Parte 2, escolha o primeiro banco (Bradesco Net Empresas), e deixe ele executar.
