from decimal import Decimal
from .base import MatcherBase

class PagBankMatcher(MatcherBase):
    """PagBank — pode ter 1 dia de diferença em liquidações."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 1
