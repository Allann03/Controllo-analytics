"""
Tabela versionada de aliquotas da Reforma Tributaria (EC 132/2023, LC 214/2025).

Aliquotas parametrizadas por ano do cronograma de transicao 2026-2033+.
Atualizavel sem tocar no motor — quando Senado/Comite Gestor publicar resolucao
com aliquotas finais, basta atualizar esta tabela.

Valores de CBS e IBS sao estimativas de referencia para manter neutralidade de
carga. Aliquotas exatas serao definidas por resolucao do Senado (CBS) e pelo
Comite Gestor do IBS.
"""

from decimal import Decimal
from services.contabil.core import rate


# -- Aliquotas por ano do cronograma de transicao (EC 132/2023 art. 124-133) ---

ALIQUOTAS_POR_ANO: dict[int, dict] = {
    2026: {
        "cbs": rate("0.009"),     # 0,9% — teste, compensavel contra PIS/COFINS
        "ibs": rate("0.001"),     # 0,1% — teste
        "fase": "teste",
        "norma": "EC 132/2023 art. 125-126",
    },
    2027: {
        "cbs": rate("0.088"),     # CBS plena — substitui PIS/COFINS
        "ibs": rate("0.001"),     # IBS ainda em teste
        "fase": "cbs_plena",
        "norma": "EC 132/2023 art. 127",
    },
    2028: {
        "cbs": rate("0.088"),
        "ibs": rate("0.088"),     # referencia ajustada pelo Comite Gestor
        "fase": "referencia",
        "norma": "EC 132/2023 art. 128",
    },
    2029: {
        "cbs": rate("0.088"),
        "ibs": rate("0.110"),     # IBS crescente, ICMS/ISS reduzem 10%
        "fase": "transicao_1",
        "norma": "EC 132/2023 art. 129",
    },
    2030: {
        "cbs": rate("0.088"),
        "ibs": rate("0.125"),     # ICMS/ISS reduzem 20%
        "fase": "transicao_2",
        "norma": "EC 132/2023 art. 129",
    },
    2031: {
        "cbs": rate("0.088"),
        "ibs": rate("0.140"),     # ICMS/ISS reduzem 30%
        "fase": "transicao_3",
        "norma": "EC 132/2023 art. 129",
    },
    2032: {
        "cbs": rate("0.088"),
        "ibs": rate("0.155"),     # ICMS/ISS reduzem 40%
        "fase": "transicao_4",
        "norma": "EC 132/2023 art. 129",
    },
    2033: {
        "cbs": rate("0.088"),     # ~8,8% (estimativa de referencia)
        "ibs": rate("0.177"),     # ~17,7% (estimativa de referencia)
        "fase": "pleno",
        "norma": "EC 132/2023 art. 130 + LC 214/2025",
    },
}

# Regime pleno usado para anos >= 2033
_REGIME_PLENO = ALIQUOTAS_POR_ANO[2033]


def get_aliquotas(ano: int) -> dict:
    """Retorna aliquotas CBS, IBS e metadata para o ano informado.

    Para anos >= 2033: retorna regime pleno.
    Para anos < 2026: ValueError (reforma nao vigente).
    """
    if ano < 2026:
        raise ValueError(
            f"Ano {ano} anterior ao inicio da Reforma Tributaria (2026). "
            "EC 132/2023 entra em vigor em 2026."
        )
    if ano > 2033:
        return _REGIME_PLENO
    return ALIQUOTAS_POR_ANO[ano]


# -- Regimes especificos (LC 214/2025) ----------------------------------------
# Fator multiplicador sobre a aliquota de referencia.
# 1.0 = aliquota cheia; 0.4 = 60% de reducao.

REGIMES_ESPECIFICOS: dict[str, dict] = {
    "geral": {
        "fator": Decimal("1.0"),
        "descricao": "Regime geral — aliquota cheia",
        "norma": "LC 214/2025 art. 12",
    },
    "saude": {
        "fator": Decimal("0.4"),
        "descricao": "Saude — 60% de reducao",
        "norma": "LC 214/2025 art. 274-285",
    },
    "educacao": {
        "fator": Decimal("0.4"),
        "descricao": "Educacao — 60% de reducao",
        "norma": "LC 214/2025 art. 260-273",
    },
    "transporte_publico": {
        "fator": Decimal("0.4"),
        "descricao": "Transporte publico — 60% de reducao",
        "norma": "LC 214/2025 art. 250",
    },
    "agropecuaria": {
        "fator": Decimal("0.4"),
        "descricao": "Agropecuaria — 60% de reducao",
        "norma": "LC 214/2025 art. 224-249",
    },
    "combustiveis": {
        "fator": Decimal("1.0"),  # regime monofasico — aliquota especifica, aqui placeholder
        "descricao": "Combustiveis — regime monofasico (aliquota especifica por unidade)",
        "norma": "LC 214/2025 art. 172-184",
    },
}

REGIMES_VALIDOS = frozenset(REGIMES_ESPECIFICOS.keys())
