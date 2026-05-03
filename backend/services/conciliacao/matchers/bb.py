from .base import MatcherBase

class BBMatcher(MatcherBase):
    """Banco do Brasil — TEDs podem postar com 1 dia."""
    TOLERANCIA_DIAS  = 1
