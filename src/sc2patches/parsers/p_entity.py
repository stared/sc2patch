"""Parser for P entity headers pattern (e.g., 3.14.0)."""

from bs4 import BeautifulSoup

from ..models import Race, SourceSection
from ..parse import PatchMetadata, RawChange, load_units_database
from .base import PatternParser


class PEntityParser(PatternParser):
    """Parser for patches with P entity headers.

    Pattern:
        <p>Thor</p>
        <ul>
          <li>Change 1</li>
          <li>Change 2</li>
        </ul>
        <p>Raven</p>
        ...
    """

    def __init__(self):
        self.units_db = load_units_database()
        # Build reverse lookup: entity_name -> (race, entity_id)
        self.entity_lookup = {}
        for race, entities in self.units_db.items():
            for name, entity_id in entities.items():
                self.entity_lookup[name.lower()] = (race, entity_id)

    @property
    def name(self) -> str:
        return "p_entity"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if HTML has P entity headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return False

        # Look for pattern: <p>Short text</p> followed by <ul>
        for p in blog.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) < 30:
                next_elem = p.find_next_sibling()
                if next_elem and next_elem.name == "ul":
                    return True
        return False

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse HTML with P entity headers."""
        blog = soup.find("section", class_="blog")
        if not blog:
            return []

        changes = []
        current_entity_id = None
        current_race = None

        for element in blog.children:
            if not element.name:
                continue

            # Check for P entity headers
            if element.name == "p":
                text = element.get_text(strip=True)
                # Short text is likely an entity name
                if text and len(text) < 30 and not text.startswith("We"):
                    # Look up entity
                    entity_lower = text.lower()
                    if entity_lower in self.entity_lookup:
                        race_str, entity_id = self.entity_lookup[entity_lower]
                        current_entity_id = entity_id
                        current_race = Race(race_str)
                    else:
                        # Unknown entity - try to guess race from context or use neutral
                        current_race = Race.NEUTRAL
                        current_entity_id = f"neutral-{text.lower().replace(' ', '_')}"

            # Extract changes from lists
            elif element.name == "ul" and current_entity_id:
                for li in element.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        # Skip neutral entities (co-op commanders, etc.)
                        if current_entity_id.startswith("neutral-"):
                            continue

                        changes.append(
                            RawChange(
                                entity_id=current_entity_id,
                                raw_text=text,
                                section=SourceSection.VERSUS_BALANCE,
                            )
                        )

        return changes
