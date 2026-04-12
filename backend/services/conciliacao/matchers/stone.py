from decimal import Decimal
from .base import MatcherBase

class StoneMatcher(MatcherBase):
    """Stone — datas exatas."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
