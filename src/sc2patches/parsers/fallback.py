"""Fallback parser for patches with no balance changes."""

from bs4 import BeautifulSoup

from ..parse import PatchMetadata, RawChange
from .base import PatternParser


class FallbackParser(PatternParser):
    """Fallback parser that handles any structure.

    This parser always succeeds but may return an empty list if no
    balance changes are found. Used for patches that are primarily
    bug fixes, editor changes, or co-op updates.
    """

    @property
    def name(self) -> str:
        return "fallback"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Always return True - this is the fallback."""
        return True

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Return empty list - no balance changes to extract."""
        return []
