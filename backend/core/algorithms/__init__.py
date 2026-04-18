from .base import AbstractMatcher, MatchResult, PatternSpec
from .ccoeff import CCoeffNormedMatcher
from .ccoeff_edge import CCoeffEdgeMatcher
from .registry import get, list_all, register

register(CCoeffNormedMatcher())
register(CCoeffEdgeMatcher())

__all__ = [
    "AbstractMatcher",
    "MatchResult",
    "PatternSpec",
    "CCoeffNormedMatcher",
    "CCoeffEdgeMatcher",
    "get",
    "list_all",
    "register",
]
