"""Parser for direct H2 race headers pattern (e.g., 5.0.15)."""

from bs4 import BeautifulSoup

from ..models import Race, SourceSection
from ..parse import (
    PatchMetadata,
    RawChange,
    detect_entity_from_text,
    detect_section_type,
    load_units_database,
)
from .base import PatternParser


class DirectH2Parser(PatternParser):
    """Parser for patches with direct H2 race headers.

    Pattern:
        <h2>Zerg</h2>
        <ul>
          <li>Change 1</li>
          <li>Change 2</li>
        </ul>
        <h2>Protoss</h2>
        ...
    """

    def __init__(self):
        self.units_db = load_units_database()

    @property
    def name(self) -> str:
        return "direct_h2"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if HTML has H2 race headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return False

        h2_headers = blog.find_all("h2")
        h2_race_headers = [
            h2 for h2 in h2_headers if h2.get_text(strip=True) in ["Terran", "Protoss", "Zerg"]
        ]
        return len(h2_race_headers) > 0

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse HTML with H2 race headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return []

        changes = []
        current_race = None
        current_section = SourceSection.UNKNOWN

        race_names = {"Zerg": Race.ZERG, "Protoss": Race.PROTOSS, "Terran": Race.TERRAN}

        for element in blog.children:
            if not element.name:
                continue

            # Check for H2 headers (section type or race)
            if element.name == "h2":
                text = element.get_text(strip=True)
                # Is it a race header?
                if text in race_names:
                    current_race = race_names[text]
                    current_section = SourceSection.VERSUS_BALANCE
                else:
                    # Is it a section header?
                    current_section = detect_section_type(text)

            # Extract changes from lists
            elif element.name == "ul" and current_race:
                # Skip non-balance sections
                if current_section not in [SourceSection.VERSUS_BALANCE, SourceSection.UNKNOWN]:
                    continue

                for li in element.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        # Detect entity ID from text
                        entity_id = detect_entity_from_text(text, current_race, self.units_db)

                        # Skip neutral entities (co-op commanders, etc.)
                        if entity_id.startswith("neutral-"):
                            continue

                        changes.append(
                            RawChange(
                                entity_id=entity_id,
                                raw_text=text,
                                section=current_section,
                            )
                        )

        return changes
