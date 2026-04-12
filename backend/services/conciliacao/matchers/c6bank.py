from decimal import Decimal
from .base import MatcherBase

class C6BankMatcher(MatcherBase):
    """C6 Bank — datas exatas."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
