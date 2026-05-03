from .base import MatcherBase

class BradescoMatcher(MatcherBase):
    """Bradesco — TED/DOC pode postar com 1 dia de diferença."""
    TOLERANCIA_DIAS  = 1
