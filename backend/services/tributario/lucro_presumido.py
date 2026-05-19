"""
lucro_presumido.py – Cálculo do Lucro Presumido (Lei 9.430/1996 / Lei 9.249/1995).

Metodologia para empresas de SERVIÇOS (presunção 32%):
  1. Lucro presumido IRPJ = Receita Bruta × 32%
  2. IRPJ = Lucro presumido × 15%
  3. Adicional IRPJ = max(0, (Lucro presumido/mês − R$20.000)) × 10%
  4. Lucro presumido CSLL = Receita Bruta × 32%
  5. CSLL = Lucro presumido CSLL × 9%
  6. PIS = Receita Bruta × 0,65% (regime cumulativo)
  7. COFINS = Receita Bruta × 3,00% (regime cumulativo)
  8. ISS = Receita Bruta × aliquota_iss (variável 2%–5%, default 5% para serviços)

Carga tributária total = IRPJ + CSLL + PIS + COFINS + ISS
(Não inclui FGTS e CPP, que são calculados sobre a folha de pagamento)

Obs.:
  - No Lucro Presumido NÃO há aproveitamento de créditos de PIS/COFINS.
  - O IRPJ e a CSLL são apurados trimestralmente; aqui calculamos mensal
    dividindo os limites de adicional por 3 meses do trimestre.
"""

from .constantes import LUCRO_PRESUMIDO as _LP, LABEL_REGIME


def calcular(
    receita_bruta: float,
    custo_servicos: float = 0.0,
    aliquota_iss: float = 0.05,
) -> dict:
    """
    Calcula a carga tributária mensal no Lucro Presumido (serviços).

    Args:
        receita_bruta: Receita bruta do mês (R$).
        custo_servicos: Custos/despesas (não usado no cálculo — só para referência).
        aliquota_iss: Alíquota do ISS (padrão 5%, mínimo legal 2%).

    Returns:
        Dict com detalhamento tributário completo.
    """
    # 1 — Base de presunção
    base_irpj = receita_bruta * _LP['presuncao_irpj']
    base_csll = receita_bruta * _LP['presuncao_csll']

    # 2 — IRPJ (15% sobre o lucro presumido)
    irpj = base_irpj * _LP['irpj']

    # 3 — Adicional IRPJ (10% sobre lucro presumido > R$20.000/mês)
    #     Tecnicamente é trimestral (> R$60.000/trimestre), mas convertemos para mensal
    excedente = max(0.0, base_irpj - _LP['limite_adicional_mensal'])
    adicional_irpj = excedente * _LP['adicional_irpj']

    irpj_total = irpj + adicional_irpj

    # 4 — CSLL (9% sobre 32% da receita)
    csll = base_csll * _LP['csll']

    # 5 — PIS cumulativo (0,65%)
    pis = receita_bruta * _LP['pis']

    # 6 — COFINS cumulativo (3%)
    cofins = receita_bruta * _LP['cofins']

    # 7 — ISS (variável por município, aqui usamos o informado)
    iss = receita_bruta * aliquota_iss

    total = irpj_total + csll + pis + cofins + iss

    detalhes = [
        {
            'tributo': 'IRPJ (15%)',
            'base': 'lucro_presumido (32% da RB)',
            'aliquota_pct': round(_LP['irpj'] * 100, 2),
            'base_valor': round(base_irpj, 2),
            'valor': round(irpj, 2),
        },
        {
            'tributo': 'Adicional IRPJ (10%)',
            'base': f'lucro > R$ {_LP["limite_adicional_mensal"]:,.0f}/mês',
            'aliquota_pct': round(_LP['adicional_irpj'] * 100, 2),
            'base_valor': round(excedente, 2),
            'valor': round(adicional_irpj, 2),
        },
        {
            'tributo': 'CSLL (9%)',
            'base': 'lucro_presumido (32% da RB)',
            'aliquota_pct': round(_LP['csll'] * 100, 2),
            'base_valor': round(base_csll, 2),
            'valor': round(csll, 2),
        },
        {
            'tributo': 'PIS (0,65%)',
            'base': 'receita_bruta',
            'aliquota_pct': round(_LP['pis'] * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'valor': round(pis, 2),
        },
        {
            'tributo': 'COFINS (3%)',
            'base': 'receita_bruta',
            'aliquota_pct': round(_LP['cofins'] * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'valor': round(cofins, 2),
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
        'regime': 'presumido',
        'label': LABEL_REGIME['presumido'],
        'receita_bruta': receita_bruta,
        'custo_servicos': custo_servicos,
        'base_irpj': round(base_irpj, 2),
        'base_csll': round(base_csll, 2),
        'irpj': round(irpj_total, 2),
        'csll': round(csll, 2),
        'pis': round(pis, 2),
        'cofins': round(cofins, 2),
        'iss': round(iss, 2),
        'total': round(total, 2),
        'pct_receita': round((total / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        'detalhes': detalhes,
    }
