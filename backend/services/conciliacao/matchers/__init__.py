from .nubank import NubankMatcher
from .bradesco import BradescoMatcher
from .itau import ItauMatcher
from .inter import InterMatcher
from .sicredi import SicrediMatcher
from .c6bank import C6BankMatcher
from .pagbank import PagBankMatcher
from .mercado_pago import MercadoPagoMatcher
from .caixa import CaixaMatcher
from .santander import SantanderMatcher
from .stone import StoneMatcher
from .bb import BBMatcher
from .universal import UniversalMatcher

__all__ = [
    "NubankMatcher", "BradescoMatcher", "ItauMatcher", "InterMatcher",
    "SicrediMatcher", "C6BankMatcher", "PagBankMatcher", "MercadoPagoMatcher",
    "CaixaMatcher", "SantanderMatcher", "StoneMatcher", "BBMatcher",
    "UniversalMatcher",
]
