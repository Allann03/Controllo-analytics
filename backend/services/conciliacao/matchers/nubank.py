from .base import MatcherBase

class NubankMatcher(MatcherBase):
    """Nubank — datas exatas, sem tolerância de dias."""
    TOLERANCIA_DIAS  = 0
