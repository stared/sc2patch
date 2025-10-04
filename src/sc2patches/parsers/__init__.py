"""HTML pattern parsers for different patch formats."""

from .base import PatternParser, detect_pattern
from .direct_h2 import DirectH2Parser
from .fallback import FallbackParser
from .h3_race import H3RaceParser
from .nested_strong import NestedStrongParser
from .p_entity import PEntityParser

__all__ = [
    "PatternParser",
    "detect_pattern",
    "DirectH2Parser",
    "H3RaceParser",
    "NestedStrongParser",
    "PEntityParser",
    "FallbackParser",
]
