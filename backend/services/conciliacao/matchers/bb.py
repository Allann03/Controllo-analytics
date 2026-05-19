from decimal import Decimal
from .base import MatcherBase

class BBMatcher(MatcherBase):
    """Banco do Brasil — TEDs podem postar com 1 dia."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 1
