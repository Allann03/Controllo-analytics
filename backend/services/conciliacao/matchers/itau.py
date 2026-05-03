from .base import MatcherBase

class ItauMatcher(MatcherBase):
    """Itaú — datas exatas, sem tolerância."""
    TOLERANCIA_DIAS  = 0
