# Comunicado -- Ajuste Metodologico na DRE

**De:** Controllo BPO Analytics — Equipe Tecnica
**Para:** Escritorios de contabilidade e clientes PME
**Data prevista de envio:** [a definir apos aprovacao do mandato]

---

## O que aconteceu

Durante uma auditoria tecnica de conformidade normativa, identificamos que o calculo
da Demonstracao do Resultado do Exercicio (DRE) no Controllo precisava de dois ajustes
para ficar em total aderencia ao CPC 26 (R2) e a Lei 6.404/76 art. 187:

1. **Reclassificacao das despesas financeiras:** As despesas financeiras estavam sendo
   tratadas como despesas operacionais. Pela norma, devem aparecer em linha propria
   entre o EBIT (Resultado Operacional) e o LAIR (Lucro Antes do IR/CSLL).

2. **Inclusao da depreciacao e amortizacao como despesa operacional:** A depreciacao
   e amortizacao (D&A) mensal nao estava sendo computada como despesa operacional na
   DRE. Pela norma (CPC 26 par. 102), D&A e despesa do periodo e deve reduzir o
   resultado.

## Quem e afetado

- **Empresas SEM depreciacao/amortizacao** (ex: prestadores de servico puros, MEIs):
  impacto apenas visual — reclassificacao de linhas entre EBIT e LAIR.
  **O Resultado Liquido permanece inalterado.**

- **Empresas COM depreciacao/amortizacao** (industria, comercio com ativos imobilizados,
  transportes, construcao civil): o Resultado Liquido apurado sera menor do que o valor
  apresentado anteriormente. A reducao corresponde ao valor da D&A mensal.

## Magnitude do impacto

| D&A mensal da empresa | Reducao anual no Resultado Liquido |
|---|---|
| R$ 500/mes | ~R$ 6.000/ano |
| R$ 2.000/mes | ~R$ 24.000/ano |
| R$ 5.000/mes | ~R$ 60.000/ano |
| R$ 20.000/mes | ~R$ 240.000/ano |

O valor exato depende da D&A lancada para cada empresa no sistema. Seu contador pode
consultar o campo "Depreciacao e Amortizacao" na DRE para ver o valor mensal.

## O que voce precisa fazer

### Se sua empresa distribuiu lucros ou dividendos com base no Resultado Liquido do Controllo

O valor distribuivel pode ter sido superestimado. Recomendamos que o contador responsavel
(CRC) revise os calculos de distribuicao a luz dos valores corrigidos e avalie se ha
necessidade de ajuste contabil.

### Se usou o Resultado Liquido para declaracoes fiscais (LALUR, ECF, ECD)

A apuracao fiscal feita diretamente no SPED nao e afetada por este sistema. Porem, se
o Controllo foi usado como fonte de dados para o LALUR ou ECF, recomendamos conferencia
com os valores oficiais apurados no SPED.

### Se reportou indicadores financeiros a instituicoes financeiras (covenants, credito)

Caso o EBITDA ou Resultado Liquido do Controllo tenha sido utilizado em reportes bancarios,
notifique a instituicao financeira sobre o ajuste metodologico e reapresente os valores
corrigidos. O novo EBITDA pode diferir do anterior: a diferenca corresponde ao valor das
despesas financeiras deslocadas para sua posicao correta.

### Se nenhuma das situacoes acima se aplica

Nenhuma acao necessaria. Os novos relatorios ja refletirao os valores corretos
automaticamente.

## Compromisso de recalculo historico

Os relatorios de periodos anteriores serao recalculados com a nova metodologia e
disponibilizados com uma nota explicativa indicando a data e o motivo da correcao.
Previsao: proximo ciclo de atualizacao do sistema.

## Fundamentacao normativa

- **CPC 26 (R2) par. 82:** Despesas financeiras devem ser apresentadas em linha propria,
  separadas das despesas operacionais.
- **CPC 26 (R2) par. 102:** Depreciacao e amortizacao sao despesas do periodo.
- **Lei 6.404/76 art. 187 inciso IV:** As despesas com vendas, gerais e administrativas
  — incluindo depreciacao — devem ser discriminadas na demonstracao de resultado.

## Compromisso do Controllo

Este ajuste faz parte de um programa de conformidade normativa integral (engine 3.0.0)
que esta sendo aplicado a todos os modulos financeiros do sistema. Nosso compromisso e
que todo calculo do Controllo reflita fielmente as normas contabeis brasileiras vigentes.

Duvidas: entre em contato com o administrador do seu escritorio ou com o suporte tecnico.

---

*Versao 1.0 — draft para revisao pelo mandato.*
