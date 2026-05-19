"""
reforma.py – Simulação da Reforma Tributária (PLP 68/2024).

Tributos substituídos:
  • CBS (Contribuição sobre Bens e Serviços) — federal
    Substitui: PIS (0,65%/1,65%) + COFINS (3%/7,6%)
    Alíquota estimada: 8,8%

  • IBS (Imposto sobre Bens e Serviços) — estadual/municipal
    Substitui: ICMS + ISS
    Alíquota estimada: 17,7%

  • IS (Imposto Seletivo) — federal, setorial
    Incide sobre: cigarros, bebidas alcoólicas, veículos, armas, etc.
    Alíquota: variável; 0% para serviços gerais

Modelo não-cumulativo:
  - CBS e IBS geram créditos sobre custos de insumos adquiridos de PJ.
  - Crédito calculado como: custo × alíquota_tributo.
  - Valor líquido = (receita × alíquota) − crédito_sobre_custos.

Cronograma de transição (estimado):
  2026: CBS 0,9% + IBS 0,1%
  2027: CBS 8,8% (pleno) + IBS aumenta gradualmente
  2029-2032: CBS plena + IBS crescente
  2033: regime pleno CBS + IBS (ICMS/ISS zerados)
"""

from .constantes import REFORMA_TRIBUTARIA, LABEL_REGIME


def calcular(
    receita_bruta: float,
    custo_servicos: float = 0.0,
    incluir_is: bool = False,
    aliquota_is: float = 0.0,
) -> dict:
    """
    Calcula a carga estimada no novo regime da Reforma Tributária.

    Args:
        receita_bruta: Receita bruta do período (R$).
        custo_servicos: Custos de insumos/serviços de terceiros (base de crédito).
        incluir_is: Se True, inclui o Imposto Seletivo no cálculo.
        aliquota_is: Alíquota do IS (0,0 para serviços gerais).

    Returns:
        Dict com simulação completa da carga pós-reforma.
    """
    detalhes = []
    total = 0.0

    for chave, tributo in REFORMA_TRIBUTARIA.items():
        if chave == 'is' and not incluir_is:
            continue

        aliq = tributo['aliquota'] if chave != 'is' else aliquota_is
        if aliq == 0:
            continue

        valor_bruto = receita_bruta * aliq
        credito = (custo_servicos * aliq) if tributo.get('credito') else 0.0
        valor_liq = max(0.0, valor_bruto - credito)

        total += valor_liq

        detalhes.append({
            'tributo': tributo['nome'],
            'aliquota_pct': round(aliq * 100, 2),
            'base_valor': round(receita_bruta, 2),
            'credito': round(credito, 2),
            'valor_bruto': round(valor_bruto, 2),
            'valor_liquido': round(valor_liq, 2),
        })

    return {
        'regime': 'reforma_tributaria',
        'label': 'Reforma Tributária (CBS + IBS)',
        'receita_bruta': receita_bruta,
        'custo_servicos': custo_servicos,
        'total': round(total, 2),
        'pct_receita': round((total / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        'detalhes': detalhes,
    }


def comparar_com_regime_atual(
    regime_atual_resultado: dict,
    receita_bruta: float,
    custo_servicos: float = 0.0,
) -> dict:
    """
    Gera comparativo entre o regime atual e a Reforma Tributária.

    Args:
        regime_atual_resultado: Resultado de calcular() de simples/presumido/real.
        receita_bruta: Receita bruta do período (R$).
        custo_servicos: Custos de insumos/serviços.

    Returns:
        Dict com comparativo completo (regime atual × reforma).
    """
    reforma = calcular(receita_bruta, custo_servicos)

    carga_atual = regime_atual_resultado.get('total', 0.0)
    carga_nova = reforma['total']

    diferenca = carga_nova - carga_atual
    variacao_pct = (diferenca / carga_atual * 100) if carga_atual > 0 else 0.0

    return {
        'regime_atual': regime_atual_resultado,
        'regime_novo': reforma,
        'comparativo': {
            'diferenca_rs': round(diferenca, 2),
            'variacao_pct': round(variacao_pct, 2),
            'impacto_lucro_rs': round(-diferenca, 2),
            'impacto': 'aumento' if diferenca > 0 else 'reducao',
            'alerta_forte': abs(variacao_pct) > 5,
            'recomendacao': (
                f'Sua carga tributária tende a '
                f'{"aumentar" if diferenca > 0 else "diminuir"} '
                f'em {abs(variacao_pct):.1f}% com a Reforma Tributária.'
            ),
        },
        'inputs': {
            'receita_bruta': receita_bruta,
            'custo_servicos': custo_servicos,
        },
    }
