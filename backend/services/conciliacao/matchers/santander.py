from decimal import Decimal
from .base import MatcherBase

class SantanderMatcher(MatcherBase):
    """Santander — datas exatas."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
