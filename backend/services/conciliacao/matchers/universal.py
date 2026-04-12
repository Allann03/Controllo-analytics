from decimal import Decimal
from .base import MatcherBase

class UniversalMatcher(MatcherBase):
    """Fallback genérico — aceita 1 dia de diferença e R$0,05 de tolerância."""
    TOLERANCIA_VALOR = Decimal('0.05')
    TOLERANCIA_DIAS  = 1
