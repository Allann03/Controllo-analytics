# Pendências da Sprint de Parsers

Este arquivo é atualizado a cada turno da sprint de parsers (Turnos 1–11).
Lista decisões deliberadas de NÃO corrigir algo no escopo do turno, com o motivo
e o plano (se houver) para tratar depois.

Cada pendência tem:
- **Identificada em:** turno onde foi observada
- **Status:** intencional / risco a investigar / fix em sprint futura
- **Impacto:** o que muda no comportamento do sistema

> **Nota sobre branches paralelas:** este arquivo é mantido em cada branch
> de turno. Esta cópia (branch `parsers/santander-ib-novo`) registra apenas
> P4, descoberta no Turno 3. P1, P2, P3 foram registradas nas branches
> `parsers/bradesco-net-empresas` (Turno 1) e `parsers/itau-empresas-moderno`
> (Turno 2) e serão consolidadas no Turno 12.

---

## Pendências do Turno 3 — Santander IB novo

### P4 — BUG DE ROTEADOR: Consolidado Santander é classificado como Mercado Pago

**Identificada em:** Turno 3 (parsers/santander-ib-novo)
**Status:** Bug a corrigir em sprint futura (Turno 4 ou dedicada)
**Impacto:** O ground truth `samples/santander_consolidado.txt` é
classificado como `'mercado_pago'` pelo detector de bancos
(`extrator_pdf.py` `_ASSINATURAS`), porque o texto contém "mercado pago"
em descrições de transações. Resultado: extratos Consolidado Inteligente
do Santander seriam roteados ao parser errado em produção.

**Por que NÃO foi corrigido no Turno 3:**
- Escopo do Turno 3 é o IB novo, não o Consolidado.
- A invariante crítica para o Turno 3 — `Consolidado != santander_ib_novo` —
  continua válida. O teste `test_consolidado_nao_classifica_como_ib_novo`
  protege isso.
- Decisão silenciosa do agente: ajustou a asserção de
  `banco in ('santander_consolidado', 'santander')` para apenas
  `banco != 'santander_ib_novo'` ao detectar o desvio. Deveria ter sido
  sinalizada como DECISÃO NECESSÁRIA — registrada aqui para
  rastreabilidade.

**Ação necessária em sprint futura:**
- Tornar a assinatura `mercado_pago` em `_ASSINATURAS` mais específica,
  exigindo ao menos um termo que NÃO apareça em descrições de Pix de
  outros bancos. A auditoria v2.0 documenta correção análoga aplicada
  para Nubank PJ (mesma classe de bug).
- Validar o roteamento do Consolidado no Turno 4 (que tratará
  `santander_consolidado` diretamente).

**Quem decide:** Turno 4 ou sprint dedicada de roteador.
