# Modelo de Dados -- Balanco Patrimonial Futuro

## Versao atual (LancamentoMensal, BLOCO 3C gerencial)

13 colunas de saldo em `LancamentoMensal`, bucket unico para ANC e PNC,
sem partida dobrada, sem depreciacao acumulada, sem vinculo DRE->PL.

Invariante Ativo == Passivo + PL verificada em runtime mas NAO atendida
em 100% dos dados existentes (gap sistematico). BP classificado como gerencial.

## Modelo proposto (BLOCO 3K)

### Desdobramento do Ativo Nao Circulante

| Coluna nova | Tipo | Descricao |
|---|---|---|
| `imobilizado_bruto` | Numeric(15,2) | Custo historico de aquisicao |
| `depreciacao_acumulada` | Numeric(15,2) | Contra-conta redutora |
| `investimentos` | Numeric(15,2) | Participacoes societarias |
| `intangivel_bruto` | Numeric(15,2) | Software, marcas, patentes |
| `amortizacao_acumulada` | Numeric(15,2) | Contra-conta do intangivel |

Imobilizado liquido = imobilizado_bruto - depreciacao_acumulada
Intangivel liquido = intangivel_bruto - amortizacao_acumulada
ANC = imobilizado_liquido + investimentos + intangivel_liquido

### Nova tabela: `saldo_contabil_mensal`

| Campo | Tipo | Descricao |
|---|---|---|
| empresa_id | FK empresas.id | Empresa |
| conta_codigo | String | Codigo do plano de contas |
| ano | Integer | Ano do saldo |
| mes | Integer | Mes do saldo |
| saldo | Numeric(15,2) | Saldo acumulado no fim do mes |

UniqueConstraint: (empresa_id, conta_codigo, ano, mes).

### Encerramento automatico DRE -> PL

No fechamento mensal:
  `lucros_acumulados += resultado_liquido_do_periodo`

Elimina necessidade de digitacao manual. Motor DRE 3.0.0 fornece o valor.
Exige implementacao de rotina de "fechamento do exercicio" com:
- Zeramento de contas de resultado
- Transferencia para Lucros Acumulados
- Registro na tabela de saldo_contabil_mensal

### Validacao de partida dobrada na insercao

Todo lancamento contabil exige debito == credito.
Rejeitar insercao com diferenca > money("0.01").

## Plano de migracao (BLOCO 3K)

1. **Backup fisico obrigatorio** antes de qualquer ALTER TABLE.
2. Adicionar colunas novas com default 0 (nao-destrutivo).
3. Para empresas com historico de `depreciacao_amortizacao` mensal:
   `depreciacao_acumulada = sum(D&A de todos os meses anteriores)`.
   (Aproximacao — nao inclui D&A anterior a entrada no Controllo.)
4. `imobilizado_bruto = ativo_nao_circulante + depreciacao_acumulada`.
5. Validar: `imobilizado_bruto - depreciacao_acumulada == ativo_nao_circulante` original.
6. Recalcular `lucros_acumulados` a partir de soma de RL dos exercicios via motor DRE 3.0.0.
7. Executar validacao de invariante Ativo == Passivo + PL pos-migracao.
8. Gerar relatorio de divergencias por empresa.

## Riscos da Migracao

### 1. Perda de historico legado
Os valores originais de `ativo_nao_circulante` e `lucros_acumulados` informados pelo
usuario serao substituidos por valores derivados. Backup fisico obrigatorio. Manter
tabela `historico_valores_legados` com snapshot pre-migracao para auditoria.

### 2. Conciliacao com dados do contador oficial
Os dados no Controllo podem divergir dos livros oficiais mantidos pelo contador no
sistema contabil (Contmatic, Dominio, Prosoft). A migracao DEVE ser conferida contra
a escrituracao oficial de cada cliente. Sem essa conferencia, o BP pos-migracao pode
estar consistente internamente mas divergente da realidade contabil.

### 3. Imobilizado bruto desconhecido
Se a empresa entrou no Controllo com ANC = 100k e acumulou 20k de D&A em 12 meses,
podemos inferir imobilizado_bruto = 120k. Mas se a empresa adquiriu ativos ANTES de
entrar no Controllo, o bruto real pode ser 200k com depreciacao acumulada de 100k.
O resultado da migracao sera imobilizado_bruto = 120k (subestimado).

Mitigacao: solicitar ao contador de cada cliente o valor de imobilizado bruto e
depreciacao acumulada na data de entrada no sistema.

### 4. Exigencia de backup fisico antes de qualquer ALTER TABLE
Nenhuma migracao de schema pode ser executada sem:
- Backup fisico datado em diretorio fora do working tree
- Script de rollback testado
- Aprovacao explicita do mandato

---

*Documento criado em: 2026-04-11 (BLOCO 3C.2). Sera expandido no BLOCO 3K.*
