"""
simples_nacional.py – Cálculo do Simples Nacional (LC 123/2006).

Metodologia:
  1. Determina a faixa conforme a RBT12 (Receita Bruta Acumulada 12 meses).
  2. Calcula a alíquota efetiva: (RBT12 × nominal − dedução) / RBT12.
  3. Aplica a alíquota efetiva sobre a receita do mês corrente.

Obs.:
  - O Anexo III é o mais utilizado por empresas de serviços.
  - Para receita mensal, extrapola para anual (× 12) para fins de faixa quando
    a RBT12 real não for informada.
  - O adicional de IRPJ (10% sobre lucro > R$20 mil/mês) NÃO se aplica ao
    Simples Nacional — o DAS é o único tributo.
"""

from .constantes import SIMPLES_ANEXOS, SIMPLES_ANEXOS_DESC, LABEL_REGIME


def calcular_aliquota_efetiva(rbt12: float, anexo: str = 'III') -> tuple[float, str]:
    """
    Retorna (aliquota_efetiva, label_faixa) para uma RBT12 e Anexo informados.

    Args:
        rbt12:  Receita Bruta Acumulada nos últimos 12 meses (R$).
        anexo:  Anexo do Simples Nacional: 'I', 'II', 'III', 'IV' ou 'V'.

    Returns:
        Tupla (alíquota efetiva em decimal, descrição da faixa).
    """
    if rbt12 <= 0:
        return 0.0, 'Sem receita'

    tabela = SIMPLES_ANEXOS.get(anexo.upper(), SIMPLES_ANEXOS['III'])

    for limite, nominal, deducao, label in tabela:
        if rbt12 <= limite:
            efetiva = (rbt12 * nominal - deducao) / rbt12
            return max(0.0, efetiva), label

    # Acima do teto do Simples (R$ 4,8 mi): não optante
    return 0.0, 'Acima do limite do Simples Nacional (> R$ 4,8 mi/ano)'


def calcular(
    receita_mensal: float,
    rbt12: float | None = None,
    anexo: str = 'III',
) -> dict:
    """
    Calcula o DAS do Simples Nacional para o mês.

    Args:
        receita_mensal: Receita bruta do mês corrente (R$).
        rbt12: Receita Bruta Acumulada 12 meses (R$).
                Se None, extrapola a partir de receita_mensal × 12.
        anexo: Anexo do Simples Nacional ('I', 'II', 'III', 'IV' ou 'V').
               Padrão: 'III' (Serviços em geral).

    Returns:
        Dict com detalhamento completo do cálculo.
    """
    if rbt12 is None:
        rbt12_calc = receita_mensal * 12
    else:
        rbt12_calc = rbt12

    anexo_upper = (anexo or 'III').upper()
    aliquota_efetiva, label_faixa = calcular_aliquota_efetiva(rbt12_calc, anexo_upper)

    das = receita_mensal * aliquota_efetiva

    # Composição estimada do DAS por anexo
    _composicao = _distribuicao_das(aliquota_efetiva, anexo_upper)

    detalhes = []
    for nome, pct in _composicao.items():
        valor_tributo = das * pct
        detalhes.append({
            'tributo': nome,
            'aliquota_pct': round(aliquota_efetiva * pct * 100, 4),
            'base': 'receita_bruta',
            'valor': round(valor_tributo, 2),
        })

    return {
        'regime': 'simples',
        'label': LABEL_REGIME['simples'],
        'anexo': anexo_upper,
        'anexo_descricao': SIMPLES_ANEXOS_DESC.get(anexo_upper, ''),
        'faixa': label_faixa,
        'rbt12': rbt12_calc,
        'receita_mensal': receita_mensal,
        'aliquota_efetiva_pct': round(aliquota_efetiva * 100, 4),
        'das': round(das, 2),
        'total': round(das, 2),
        'pct_receita': round(aliquota_efetiva * 100, 2),
        'detalhes': detalhes,
    }


def _distribuicao_das(aliquota: float, anexo: str = 'III') -> dict:
    """
    Distribuição estimada do DAS entre os tributos por Anexo.
    Percentuais sobre o total do DAS.

    Fonte: LC 123/2006 Tabelas I-V (distribuição média ponderada por faixa).
    Obs.: Anexo IV não inclui CPP (recolhida separado pelo empregador).
    """
    _composicoes = {
        'I': {   # Comércio (LC 123/2006, Anexo I — distribuição média)
            'IRPJ':   0.055, 'CSLL':   0.035, 'COFINS': 0.1274,
            'PIS':    0.0276, 'CPP':   0.4150, 'ICMS':   0.3400,
        },
        'II': {  # Indústria
            'IRPJ':   0.050, 'CSLL':   0.035, 'COFINS': 0.275,
            'PIS':    0.059, 'CPP':    0.430, 'IPI':    0.025, 'ICMS': 0.126,
        },
        'III': { # Serviços em geral
            'IRPJ':   0.045, 'CSLL':   0.090, 'COFINS': 0.287,
            'PIS':    0.062, 'CPP':    0.434, 'ISS':    0.082,
        },
        'IV': {  # Serviços c/ CPP separada (sem CPP no DAS)
            'IRPJ':   0.180, 'CSLL':   0.150, 'COFINS': 0.347,
            'PIS':    0.075, 'ISS':    0.248,
        },
        'V': {   # Serviços fator R
            'IRPJ':   0.150, 'CSLL':   0.090, 'COFINS': 0.287,
            'PIS':    0.062, 'CPP':    0.257, 'ISS':    0.154,
        },
    }
    return _composicoes.get(anexo, _composicoes['III'])
