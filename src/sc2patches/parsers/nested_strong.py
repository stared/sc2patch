"""Parser for nested strong tags pattern (e.g., 4.x patches)."""

from bs4 import BeautifulSoup

from ..models import Race, SourceSection
from ..parse import PatchMetadata, RawChange, detect_entity_from_text, detect_section_type, load_units_database
from .base import PatternParser


class NestedStrongParser(PatternParser):
    """Parser for patches with nested strong tags.

    Pattern 1 (with H3 race headers):
        <h3>TERRAN</h3>
        <ul>
          <li><strong>Widow Mine</strong>
            <ul>
              <li>Change 1</li>
              <li>Change 2</li>
            </ul>
          </li>
        </ul>

    Pattern 2 (without race headers):
        <ul>
          <li><strong>Section or Entity</strong>
            <ul>
              <li>TerranEntity nameChange text</li>
              <li>Change text</li>
            </ul>
          </li>
        </ul>
    """

    def __init__(self):
        self.units_db = load_units_database()

    @property
    def name(self) -> str:
        return "nested_strong"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if HTML has nested strong structure."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return False

        # Look for <li><strong>...</strong><ul> pattern
        for ul in blog.find_all("ul"):
            for li in ul.find_all("li", recursive=False):
                strong = li.find("strong")
                nested_ul = li.find("ul")
                if strong and nested_ul:
                    return True
        return False

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse HTML with nested strong structure."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return []

        changes = []
        current_race = None
        current_section = SourceSection.UNKNOWN

        race_names = {"Zerg": Race.ZERG, "Protoss": Race.PROTOSS, "Terran": Race.TERRAN,
                      "ZERG": Race.ZERG, "PROTOSS": Race.PROTOSS, "TERRAN": Race.TERRAN}

        for element in blog.children:
            if not element.name:
                continue

            # Check for H2 section headers
            if element.name == "h2":
                text = element.get_text(strip=True)
                current_section = detect_section_type(text)
                # Also check if it's a race name
                if text in race_names:
                    current_race = race_names[text]

            # Check for H3 race headers
            elif element.name == "h3":
                text = element.get_text(strip=True)
                if text in race_names:
                    current_race = race_names[text]
                    if current_section == SourceSection.UNKNOWN:
                        current_section = SourceSection.VERSUS_BALANCE

            # Process UL elements
            elif element.name == "ul":
                # Look for nested structure: <li><strong>...</strong><ul>...</ul></li>
                for li in element.find_all("li", recursive=False):
                    strong = li.find("strong")
                    nested_ul = li.find("ul")

                    if strong and nested_ul:
                        # strong tag contains entity or section name
                        strong_text = strong.get_text(strip=True)

                        # Process nested changes
                        for nested_li in nested_ul.find_all("li", recursive=False):
                            change_text = nested_li.get_text(strip=True)
                            if not change_text:
                                continue

                            # Try to extract race from text if not set
                            # Pattern: "TerranEntityChange" or "ProtossEntityChange"
                            detected_race = current_race
                            clean_text = change_text

                            if not detected_race:
                                for race_name, race_enum in race_names.items():
                                    if change_text.startswith(race_name):
                                        detected_race = race_enum
                                        # Remove race prefix from text
                                        clean_text = change_text[len(race_name):]
                                        break

                            # If still no race, try to detect from entity name in strong tag
                            if not detected_race:
                                # Look up strong_text in units database
                                for race_str, entities in self.units_db.items():
                                    if strong_text in entities:
                                        detected_race = Race(race_str)
                                        break

                            # Default to neutral if we still can't determine race
                            if not detected_race:
                                detected_race = Race.NEUTRAL

                            # Detect entity from text
                            entity_id = detect_entity_from_text(clean_text, detected_race, self.units_db)

                            # If entity detection failed, try using strong_text
                            if entity_id.endswith("-unknown") and detected_race != Race.NEUTRAL:
                                entity_from_strong = detect_entity_from_text(strong_text, detected_race, self.units_db)
                                if not entity_from_strong.endswith("-unknown"):
                                    entity_id = entity_from_strong

                            changes.append(
                                RawChange(
                                    entity_id=entity_id,
                                    raw_text=clean_text,
                                    section=current_section,
                                )
                            )

        return changes
