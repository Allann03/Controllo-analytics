from .base import MatcherBase

class PagBankMatcher(MatcherBase):
    """PagBank — pode ter 1 dia de diferença em liquidações."""
    TOLERANCIA_DIAS  = 1
