"""
constantes.py – Alíquotas e constantes tributárias vigentes (2024/2025).

Fonte: Receita Federal do Brasil, LC 123/2006 (Simples Nacional), Lei 9.249/1995
(Lucro Presumido), e estimativas da Reforma Tributária (PLP 68/2024).

Simples Nacional — Anexos I a V (LC 123/2006):
  Anexo I   — Comércio (varejista e atacadista)
  Anexo II  — Indústria (fabricação de produtos)
  Anexo III — Serviços em geral (mais comum: TI, consultoria, contabilidade, saúde)
  Anexo IV  — Serviços com recolhimento separado de CPP (construção civil, limpeza,
               vigilância, advocacia, serviços de engenharia contratados)
  Anexo V   — Serviços com fator R (quando folha < 28% da receita cai no Anexo V;
               se folha >= 28% migra para Anexo III)

Fórmula: alíquota efetiva = (RBT12 × alíquota_nominal − parcela_deduzir) / RBT12
"""

# ─── SIMPLES NACIONAL — Anexo I (Comércio) ───────────────────────────────────
SIMPLES_ANEXO_I = [
    # (limite_superior, alíquota_nominal, parcela_deduzir, label)
    (180_000.00,      0.040,       0.00,      'Faixa 1 — até R$ 180 mil/ano'),
    (360_000.00,      0.073,   5_940.00,      'Faixa 2 — até R$ 360 mil/ano'),
    (720_000.00,      0.095,  13_860.00,      'Faixa 3 — até R$ 720 mil/ano'),
    (1_800_000.00,    0.107,  22_500.00,      'Faixa 4 — até R$ 1,8 mi/ano'),
    (3_600_000.00,    0.143, 87_300.00,       'Faixa 5 — até R$ 3,6 mi/ano'),
    (4_800_000.00,    0.190, 378_000.00,      'Faixa 6 — até R$ 4,8 mi/ano'),
]

# ─── SIMPLES NACIONAL — Anexo II (Indústria) ─────────────────────────────────
SIMPLES_ANEXO_II = [
    (180_000.00,      0.045,       0.00,      'Faixa 1 — até R$ 180 mil/ano'),
    (360_000.00,      0.078,   5_940.00,      'Faixa 2 — até R$ 360 mil/ano'),
    (720_000.00,      0.100,  13_860.00,      'Faixa 3 — até R$ 720 mil/ano'),
    (1_800_000.00,    0.113,  22_500.00,      'Faixa 4 — até R$ 1,8 mi/ano'),
    (3_600_000.00,    0.147, 85_500.00,       'Faixa 5 — até R$ 3,6 mi/ano'),
    (4_800_000.00,    0.300, 720_000.00,      'Faixa 6 — até R$ 4,8 mi/ano'),
]

# ─── SIMPLES NACIONAL — Anexo III (Serviços em geral) ────────────────────────
# Faixas de Receita Bruta Acumulada 12 meses (RBT12) → alíquota nominal e dedução
SIMPLES_ANEXO_III = [
    # (limite_superior, alíquota_nominal, parcela_deduzir, label)
    (180_000.00,          0.060,      0.00,       'Faixa 1 — até R$ 180 mil/ano'),
    (360_000.00,          0.112,      9_360.00,   'Faixa 2 — até R$ 360 mil/ano'),
    (720_000.00,          0.135,     17_640.00,   'Faixa 3 — até R$ 720 mil/ano'),
    (1_800_000.00,        0.160,     35_640.00,   'Faixa 4 — até R$ 1,8 mi/ano'),
    (3_600_000.00,        0.210,     125_640.00,  'Faixa 5 — até R$ 3,6 mi/ano'),
    (4_800_000.00,        0.330,     648_000.00,  'Faixa 6 — até R$ 4,8 mi/ano'),
]

# ─── SIMPLES NACIONAL — Anexo IV (Serviços c/ CPP separada) ──────────────────
# ISS + demais tributos federais; CPP (INSS patronal) é recolhida separadamente
SIMPLES_ANEXO_IV = [
    (180_000.00,      0.045,       0.00,      'Faixa 1 — até R$ 180 mil/ano'),
    (360_000.00,      0.090,   8_100.00,      'Faixa 2 — até R$ 360 mil/ano'),
    (720_000.00,      0.102,  12_420.00,      'Faixa 3 — até R$ 720 mil/ano'),
    (1_800_000.00,    0.114,  21_060.00,      'Faixa 4 — até R$ 1,8 mi/ano'),
    (3_600_000.00,    0.162, 101_340.00,      'Faixa 5 — até R$ 3,6 mi/ano'),
    (4_800_000.00,    0.280, 540_000.00,      'Faixa 6 — até R$ 4,8 mi/ano'),
]

# ─── SIMPLES NACIONAL — Anexo V (Serviços c/ fator R — folha < 28% receita) ──
# Quando folha de pagamento dos últimos 12 meses / RBT12 >= 28%: aplica Anexo III
SIMPLES_ANEXO_V = [
    (180_000.00,      0.155,      0.00,       'Faixa 1 — até R$ 180 mil/ano'),
    (360_000.00,      0.180,   4_500.00,      'Faixa 2 — até R$ 360 mil/ano'),
    (720_000.00,      0.195,   9_900.00,      'Faixa 3 — até R$ 720 mil/ano'),
    (1_800_000.00,    0.205,  17_100.00,      'Faixa 4 — até R$ 1,8 mi/ano'),
    (3_600_000.00,    0.230,  62_100.00,      'Faixa 5 — até R$ 3,6 mi/ano'),
    (4_800_000.00,    0.305, 540_000.00,      'Faixa 6 — até R$ 4,8 mi/ano'),
]

# Mapa de consulta rápida por nome de anexo
SIMPLES_ANEXOS = {
    'I':   SIMPLES_ANEXO_I,
    'II':  SIMPLES_ANEXO_II,
    'III': SIMPLES_ANEXO_III,
    'IV':  SIMPLES_ANEXO_IV,
    'V':   SIMPLES_ANEXO_V,
}

# Descrições dos anexos para exibição
SIMPLES_ANEXOS_DESC = {
    'I':   'Comércio (varejista / atacadista)',
    'II':  'Indústria (fabricação)',
    'III': 'Serviços em geral (TI, saúde, contabilidade)',
    'IV':  'Serviços com CPP separada (construção, limpeza, advocacia)',
    'V':   'Serviços com fator R (folha < 28% da receita)',
}

# ─── LUCRO PRESUMIDO — Serviços ───────────────────────────────────────────────
# Base de presunção para IRPJ: 32% da receita bruta (serviços em geral)
# Base de presunção para CSLL: 32% da receita bruta
LUCRO_PRESUMIDO = {
    'presuncao_irpj':  0.32,    # base de cálculo do IRPJ
    'presuncao_csll':  0.32,    # base de cálculo da CSLL
    'irpj':            0.15,    # alíquota IRPJ sobre o lucro presumido
    'adicional_irpj':  0.10,    # adicional IRPJ sobre lucro mensal > R$20.000
    'limite_adicional_mensal': 20_000.00,
    'csll':            0.09,    # CSLL
    'pis':             0.0065,  # PIS cumulativo
    'cofins':          0.030,   # COFINS cumulativo
}

# ─── LUCRO REAL ───────────────────────────────────────────────────────────────
LUCRO_REAL = {
    'irpj':            0.15,    # sobre o lucro real
    'adicional_irpj':  0.10,    # adicional sobre lucro mensal > R$20.000
    'limite_adicional_mensal': 20_000.00,
    'csll':            0.09,
    'pis':             0.0165,  # PIS não-cumulativo
    'cofins':          0.076,   # COFINS não-cumulativo
}

# ─── REFORMA TRIBUTÁRIA — estimativas PLP 68/2024 ────────────────────────────
# Alíquotas de referência para transição (2026-2033).
# Valores finais previstos para o regime pleno após 2033.
REFORMA_TRIBUTARIA = {
    'cbs': {
        'nome':      'CBS — Contribuição sobre Bens e Serviços (federal)',
        'aliquota':  0.088,     # estimativa 8,8% (substitui PIS/COFINS)
        'credito':   True,      # não-cumulativo: gera crédito na cadeia
    },
    'ibs': {
        'nome':      'IBS — Imposto sobre Bens e Serviços (estadual/municipal)',
        'aliquota':  0.177,     # estimativa 17,7% (substitui ICMS/ISS)
        'credito':   True,
    },
    'is': {
        'nome':      'IS — Imposto Seletivo (sobre bens prejudiciais)',
        'aliquota':  0.0,       # aplicável apenas a setores específicos
        'credito':   False,
    },
}

# Alíquota total estimada CBS + IBS (sem IS, para serviços gerais)
REFORMA_ALIQUOTA_TOTAL = (
    REFORMA_TRIBUTARIA['cbs']['aliquota'] + REFORMA_TRIBUTARIA['ibs']['aliquota']
)  # ≈ 26,5%

# ─── LABELS DE REGIME ────────────────────────────────────────────────────────
LABEL_REGIME = {
    'simples':   'Simples Nacional',
    'presumido': 'Lucro Presumido',
    'real':      'Lucro Real',
}
