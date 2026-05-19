from decimal import Decimal
from .base import MatcherBase

class ItauMatcher(MatcherBase):
    """Itaú — datas exatas, sem tolerância."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
