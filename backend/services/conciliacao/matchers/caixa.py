from .base import MatcherBase

class CaixaMatcher(MatcherBase):
    """Caixa Econômica Federal — TEDs podem postar com 1 dia de diferença."""
    TOLERANCIA_DIAS  = 1
