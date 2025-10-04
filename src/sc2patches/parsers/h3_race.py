"""Parser for H3 race headers pattern (e.g., 5.0.12-14)."""

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


class H3RaceParser(PatternParser):
    """Parser for patches with H3 race headers.

    Pattern 1 (with P/B entity headers):
        <h2>Balance Update</h2>
        <h3>Zerg</h3>
        <p><b>Zergling</b></p>
        <ul>
          <li>Change 1</li>
          <li>Change 2</li>
        </ul>

    Pattern 2 (with H4 entity headers):
        <h3>Protoss</h3>
        <h4>Stalker</h4>
        <ul>
          <li>Change 1</li>
        </ul>
    """

    def __init__(self):
        self.units_db = load_units_database()

    @property
    def name(self) -> str:
        return "h3_race"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if HTML has H3 race headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return False

        h3_headers = blog.find_all("h3")
        h3_race_headers = [
            h3 for h3 in h3_headers if h3.get_text(strip=True) in ["Terran", "Protoss", "Zerg"]
        ]
        return len(h3_race_headers) > 0

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse HTML with H3 race headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return []

        changes = []
        current_race = None
        current_section = SourceSection.UNKNOWN
        current_entity_id = None

        race_names = {"Zerg": Race.ZERG, "Protoss": Race.PROTOSS, "Terran": Race.TERRAN}

        for element in blog.children:
            if not element.name:
                continue

            # Check for H2 section headers
            if element.name == "h2":
                text = element.get_text(strip=True)
                current_section = detect_section_type(text)
                # Reset race when entering new section
                if current_section != SourceSection.VERSUS_BALANCE:
                    current_race = None

            # Check for H3 race headers
            elif element.name == "h3":
                text = element.get_text(strip=True)
                if text in race_names:
                    current_race = race_names[text]
                    # Default to balance if not set
                    if current_section == SourceSection.UNKNOWN:
                        current_section = SourceSection.VERSUS_BALANCE
                    current_entity_id = None  # Reset entity

            # Check for H4 entity headers: <h4>Entity</h4>
            elif element.name == "h4" and current_race:
                entity_name = element.get_text(strip=True)
                # Try to detect entity from name
                entity_id = detect_entity_from_text(entity_name, current_race, self.units_db)
                current_entity_id = entity_id

            # Check for P entity headers: <p><b>Entity</b></p>
            elif element.name == "p" and current_race:
                # Look for <b> tag inside <p>
                b_tag = element.find("b")
                if b_tag:
                    entity_name = b_tag.get_text(strip=True)
                    # Try to detect entity from name
                    entity_id = detect_entity_from_text(entity_name, current_race, self.units_db)
                    current_entity_id = entity_id

            # Extract changes from lists
            elif element.name == "ul" and current_race:
                # Only include if in balance/versus section
                if current_section not in [SourceSection.VERSUS_BALANCE, SourceSection.UNKNOWN]:
                    continue

                for li in element.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        # Use current_entity_id if set, otherwise detect from text
                        if current_entity_id:
                            entity_id = current_entity_id
                        else:
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
