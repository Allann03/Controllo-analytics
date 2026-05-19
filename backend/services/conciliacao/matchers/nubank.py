from decimal import Decimal
from .base import MatcherBase

class NubankMatcher(MatcherBase):
    """Nubank — datas exatas, sem tolerância de dias."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
