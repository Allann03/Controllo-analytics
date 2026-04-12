from decimal import Decimal
from .base import MatcherBase

class MercadoPagoMatcher(MatcherBase):
    """Mercado Pago — datas exatas."""
    TOLERANCIA_VALOR = Decimal('0.02')
    TOLERANCIA_DIAS  = 0
