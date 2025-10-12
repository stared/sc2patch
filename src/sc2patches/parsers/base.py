"""Base parser interface and pattern detection."""

from abc import ABC, abstractmethod
from pathlib import Path

from bs4 import BeautifulSoup

from ..parse import PatchMetadata, RawChange


class PatternParser(ABC):
    """Base class for HTML pattern parsers."""

    @abstractmethod
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the HTML structure.

        Args:
            soup: BeautifulSoup object of the HTML

        Returns:
            True if this parser can handle the structure
        """

    @abstractmethod
    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse the HTML to extract changes.

        Args:
            soup: BeautifulSoup object of the HTML
            metadata: Patch metadata

        Returns:
            List of RawChange objects
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Parser name for debugging."""


def detect_pattern(html_path: Path) -> str:
    """Detect which pattern a patch uses.

    Args:
        html_path: Path to HTML file

    Returns:
        Pattern name (direct_h2, h3_race, nested_strong, p_entity, or unknown)
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        return "no_blog"

    # Check for direct H2 race headers (5.0.15)
    h2_headers = blog.find_all("h2")
    h2_race_headers = [
        h2 for h2 in h2_headers if h2.get_text(strip=True) in ["Terran", "Protoss", "Zerg"]
    ]
    if h2_race_headers:
        return "direct_h2"

    # Check for H3 race headers (5.0.12-14)
    h3_headers = blog.find_all("h3")
    h3_race_headers = [
        h3 for h3 in h3_headers if h3.get_text(strip=True) in ["Terran", "Protoss", "Zerg"]
    ]
    if h3_race_headers:
        return "h3_race"

    # Check for P entity headers (3.14.0)
    # Pattern: <p>EntityName</p> followed by <ul>
    for p in blog.find_all("p"):
        text = p.get_text(strip=True)
        # Short text that's just a name (likely an entity)
        if text and len(text) < 30 and not text.startswith("We"):
            next_elem = p.find_next_sibling()
            if next_elem and next_elem.name == "ul":
                return "p_entity"

    # Default to nested_strong (most 3.x and 4.x patches)
    strong_tags = blog.find_all("strong")
    if strong_tags:
        return "nested_strong"

    return "unknown"
