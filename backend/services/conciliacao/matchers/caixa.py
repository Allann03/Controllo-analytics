from decimal import Decimal
from .base import MatcherBase

class CaixaMatcher(MatcherBase):
    """Caixa Econômica Federal — TEDs podem postar com 1 dia de diferença."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 1
