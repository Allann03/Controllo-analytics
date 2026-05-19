"""
lucro_real.py – Cálculo do Lucro Real (Lei 9.430/1996 / RIR/2018).

Metodologia:
  1. Lucro Real = Receita Bruta − Custos − Despesas dedutíveis
  2. IRPJ = Lucro Real × 15%
  3. Adicional IRPJ = max(0, (Lucro Real/mês − R$20.000)) × 10%
  4. CSLL = Lucro Real × 9%
  5. PIS = Receita Bruta × 1,65% (não-cumulativo, menos créditos)
  6. COFINS = Receita Bruta × 7,6% (não-cumulativo, menos créditos)
  7. ISS = Receita Bruta × aliquota_iss (se for prestador de serviços)

No regime NÃO-CUMULATIVO:
  - PIS e COFINS geram créditos sobre custos com pessoas jurídicas.
  - crédito_pis   = custo_servicos × 1,65%
  - crédito_cofins = custo_servicos × 7,6%
  - PIS líquido = max(0, PIS bruto − crédito_pis)
  - COFINS líquido = max(0, COFINS bruto − crédito_cofins)

Obs.:
  - Mais vantajoso quando a margem de lucro real é < 32% (ponto de indiferença
    com o Lucro Presumido para serviços).
  - IR e CSLL só são devidos quando há lucro; prejuízo pode ser compensado
    em até 30% do lucro dos exercícios seguintes.
"""

from .constantes import LUCRO_REAL as _LR, LABEL_REGIME


def calcular(
    receita_bruta: float,
    custo_servicos: float = 0.0,
    aliquota_iss: float = 0.05,
) -> dict:
    """
    Calcula a carga tributária mensal no Lucro Real.

    Args:
        receita_bruta: Receita bruta do mês (R$).
        custo_servicos: Custos com serviços/insumos PJ (base para créditos PIS/COFINS).
        aliquota_iss: Alíquota do ISS (padrão 5%).

    Returns:
        Dict com detalhamento tributário completo.
    """
    # 1 — Lucro Real (simplificado: receita − custo)
    lucro_real = max(0.0, receita_bruta - custo_servicos)

    # 2 — IRPJ (15% sobre lucro real)
    irpj = lucro_real * _LR['irpj']

    # 3 — Adicional IRPJ
    excedente = max(0.0, lucro_real - _LR['limite_adicional_mensal'])
    adicional_irpj = excedente * _LR['adicional_irpj']
    irpj_total = irpj + adicional_irpj

    # 4 — CSLL
    csll = lucro_real * _LR['csll']

    # 5 — PIS não-cumulativo (crédito sobre compras PJ)
    pis_bruto = receita_bruta * _LR['pis']
    credito_pis = custo_servicos * _LR['pis']
    pis_liq = max(0.0, pis_bruto - credito_pis)

    # 6 — COFINS não-cumulativa
    cofins_bruto = receita_bruta * _LR['cofins']
    credito_cofins = custo_servicos * _LR['cofins']
    cofins_liq = max(0.0, cofins_bruto - credito_cofins)

    # 7 — ISS
    iss = receita_bruta * aliquota_iss

    total = irpj_total + csll + pis_liq + cofins_liq + iss

    detalhes = [
        {
            'tributo': 'IRPJ (15%)',
            'base': 'lucro_real',
            'aliquota_pct': round(_LR['irpj'] * 100, 2),
            'base_valor': round(lucro_real, 2),
            'valor': round(irpj, 2),
        },
        {
            'tributo': 'Adicional IRPJ (10%)',
            'base': f'lucro > R$ {_LR["limite_adicional_mensal"]:,.0f}/mês',
            'aliquota_pct': round(_LR['adicional_irpj'] * 100, 2),
            'base_valor': round(excedente, 2),
            'valor': round(adicional_irpj, 2),
        },
        {
            'tributo': 'CSLL (9%)',
            'base': 'lucro_real',
            'aliquota_pct': round(_LR['csll'] * 100, 2),
            'base_valor': round(lucro_real, 2),
            'valor': round(csll, 2),
        },
        {
            'tributo': 'PIS (1,65%) — não-cumulativo',
            'base': 'receita_bruta',
            'aliquota_pct': round(_LR['pis'] * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'credito': round(credito_pis, 2),
            'valor': round(pis_liq, 2),
        },
        {
            'tributo': 'COFINS (7,6%) — não-cumulativa',
            'base': 'receita_bruta',
            'aliquota_pct': round(_LR['cofins'] * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'credito': round(credito_cofins, 2),
            'valor': round(cofins_liq, 2),
        },
        {
            'tributo': f'ISS ({aliquota_iss*100:.1f}%)',
            'base': 'receita_bruta',
            'aliquota_pct': round(aliquota_iss * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'valor': round(iss, 2),
        },
    ]

    return {
        'regime': 'real',
        'label': LABEL_REGIME['real'],
        'receita_bruta': receita_bruta,
        'custo_servicos': custo_servicos,
        'lucro_real': round(lucro_real, 2),
        'margem_lucro_pct': round((lucro_real / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        'irpj': round(irpj_total, 2),
        'csll': round(csll, 2),
        'pis': round(pis_liq, 2),
        'pis_credito': round(credito_pis, 2),
        'cofins': round(cofins_liq, 2),
        'cofins_credito': round(credito_cofins, 2),
        'iss': round(iss, 2),
        'total': round(total, 2),
        'pct_receita': round((total / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        'detalhes': detalhes,
    }
