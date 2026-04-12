"""
Tabela de aliquotas ICMS interestaduais e internas por UF.

Fontes:
  - Interestadual: Resolucao SF 22/1989, CF art. 155 par. 2 IV
  - Importados: Resolucao SF 13/2012 (aliquota unica 4%)
  - Internas: legislacao estadual vigente (valores de referencia)
  - FCP: EC 87/2015 art. 1 (Fundo de Combate a Pobreza, 0-2%)
"""

from decimal import Decimal
from services.contabil.core import rate

# UFs validas
UFS_VALIDAS = frozenset({
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
})

# UFs do Sul e Sudeste (exceto ES) — aplicam 7% para Norte/Nordeste/CO/ES
_SUL_SUDESTE = frozenset({"SP", "RJ", "MG", "PR", "SC", "RS"})
# Norte, Nordeste, Centro-Oeste e ES
_NORTE_NE_CO_ES = UFS_VALIDAS - _SUL_SUDESTE


def aliquota_interestadual(uf_origem: str, uf_destino: str, importado: bool = False) -> Decimal:
    """Retorna aliquota ICMS interestadual.

    Resolucao SF 22/1989:
      - Sul/Sudeste (exceto ES) -> Norte/NE/CO/ES: 7%
      - Demais: 12%
    Resolucao SF 13/2012:
      - Produtos importados: 4%
    """
    if importado:
        return rate("0.04")

    if uf_origem in _SUL_SUDESTE and uf_destino in _NORTE_NE_CO_ES:
        return rate("0.07")

    return rate("0.12")


# Aliquota interna padrao por UF (valores de referencia vigentes)
# Fonte: legislacao estadual consolidada. Podem variar por produto/NCM.
ALIQUOTA_INTERNA_PADRAO: dict[str, Decimal] = {
    "AC": rate("0.19"), "AL": rate("0.19"), "AP": rate("0.18"), "AM": rate("0.20"),
    "BA": rate("0.205"), "CE": rate("0.20"), "DF": rate("0.20"), "ES": rate("0.17"),
    "GO": rate("0.19"), "MA": rate("0.22"), "MT": rate("0.17"), "MS": rate("0.17"),
    "MG": rate("0.18"), "PA": rate("0.19"), "PB": rate("0.20"), "PR": rate("0.195"),
    "PE": rate("0.205"), "PI": rate("0.21"), "RJ": rate("0.22"), "RN": rate("0.20"),
    "RS": rate("0.17"), "RO": rate("0.195"), "RR": rate("0.20"), "SC": rate("0.17"),
    "SP": rate("0.18"), "SE": rate("0.19"), "TO": rate("0.20"),
}

# Fundo de Combate a Pobreza por UF (EC 87/2015)
# 0 = nao aplica ou nao regulamentado
FCP_POR_UF: dict[str, Decimal] = {
    "AC": rate("0.00"), "AL": rate("0.01"), "AP": rate("0.00"), "AM": rate("0.02"),
    "BA": rate("0.02"), "CE": rate("0.02"), "DF": rate("0.02"), "ES": rate("0.02"),
    "GO": rate("0.02"), "MA": rate("0.02"), "MT": rate("0.02"), "MS": rate("0.02"),
    "MG": rate("0.02"), "PA": rate("0.02"), "PB": rate("0.02"), "PR": rate("0.00"),
    "PE": rate("0.02"), "PI": rate("0.02"), "RJ": rate("0.02"), "RN": rate("0.02"),
    "RS": rate("0.00"), "RO": rate("0.02"), "RR": rate("0.00"), "SC": rate("0.00"),
    "SP": rate("0.02"), "SE": rate("0.02"), "TO": rate("0.02"),
}
