"""
Tabela de servicos sujeitos a retencao na fonte.

Fontes:
  - IRRF 1,5%: RIR/2018 art. 714 (ex-647), Lei 7.713/88 art. 53
  - CSRF 4,65%: Lei 10.833/03 art. 30
  - Dispensa CSRF: Lei 10.833/03 art. 31 par. 3 (pagamento <= R$ 215,05)
"""

from decimal import Decimal

# Limite de dispensa CSRF (Lei 10.833/03 art. 31 par. 3)
DISPENSA_CSRF_LIMITE = Decimal("215.05")

# Aliquotas de retencao
ALIQUOTA_IRRF = Decimal("0.015")        # 1,5% — RIR/2018 art. 714
ALIQUOTA_CSLL_RET = Decimal("0.01")     # 1,0% — Lei 10.833/03 art. 30
ALIQUOTA_COFINS_RET = Decimal("0.03")   # 3,0% — Lei 10.833/03 art. 30
ALIQUOTA_PIS_RET = Decimal("0.0065")    # 0,65% — Lei 10.833/03 art. 30
ALIQUOTA_CSRF_TOTAL = Decimal("0.0465") # 4,65% = 1% + 3% + 0,65%
ALIQUOTA_INSS_RET = Decimal("0.11")     # 11% — Lei 8.212/91 art. 31

# Tipos de servico sujeitos a IRRF 1,5% (RIR/2018 art. 714)
# Servicos profissionais prestados por PJ
SERVICOS_IRRF_15 = frozenset({
    "profissional_liberal",       # advocacia, contabilidade, engenharia, medicina, etc.
    "consultoria",                # consultoria tecnica, empresarial, financeira
    "assessoria",                 # assessoria tecnica, administrativa
    "auditoria",
    "publicidade_propaganda",     # agencias
    "limpeza_conservacao",
    "vigilancia_seguranca",
    "locacao_mao_obra",
    "manutencao_equipamentos",
    "intermediacao_negocios",     # corretagem, representacao comercial
    "desenvolvimento_software",   # programacao, TI
    "servicos_tecnicos",          # laudos, pareceres, projetos
    "treinamento_ensino",
})

# Tipos de servico sujeitos a CSRF 4,65% (Lei 10.833/03 art. 30)
SERVICOS_CSRF_465 = frozenset({
    "profissional_liberal",
    "consultoria",
    "assessoria",
    "limpeza_conservacao",
    "vigilancia_seguranca",
    "locacao_mao_obra",
    "manutencao_equipamentos",
    "intermediacao_negocios",
    "desenvolvimento_software",
    "servicos_tecnicos",
})

# Todos os tipos validos
TIPOS_SERVICO_VALIDOS = frozenset({
    "profissional_liberal", "consultoria", "assessoria", "auditoria",
    "publicidade_propaganda", "limpeza_conservacao", "vigilancia_seguranca",
    "locacao_mao_obra", "manutencao_equipamentos", "intermediacao_negocios",
    "desenvolvimento_software", "servicos_tecnicos", "treinamento_ensino",
    "cessao_mao_obra",   # INSS 11% — Lei 8.212/91 art. 31
    "outros",            # sem retencao federal
})
