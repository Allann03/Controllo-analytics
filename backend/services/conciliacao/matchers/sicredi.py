from decimal import Decimal
from .base import MatcherBase

class SicrediMatcher(MatcherBase):
    """Sicredi — cooperativa, datas exatas."""
    TOLERANCIA_VALOR = Decimal('0.05')
    TOLERANCIA_DIAS  = 0
