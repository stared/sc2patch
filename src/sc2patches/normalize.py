"""Normalize HTML patch notes into a clean nested structure."""

from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, NavigableString


@dataclass
class NormalizedItem:
    """A single item in the normalized structure."""

    type: str  # "section", "race", "entity", "change"
    text: str
    children: list["NormalizedItem"]
    level: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for debugging."""
        return {
            "type": self.type,
            "text": self.text,
            "children": [c.to_dict() for c in self.children],
        }


def normalize_html_to_tree(soup: BeautifulSoup) -> list[NormalizedItem]:
    """Normalize HTML into a clean tree structure.

    Converts various HTML patterns into a consistent format:
    - Section (H2 section headers like "Balance Update", "Bug Fixes")
    - Race (H2/H3 race headers like "Terran", "Protoss", "Zerg")
    - Entity (H4 or <p><b> entity names like "Cyclone", "Marine")
    - Change (LI items with actual balance changes)

    Args:
        soup: BeautifulSoup object of patch HTML

    Returns:
        List of normalized items representing the document structure
    """
    blog = soup.find("section", class_="blog")
    if not blog:
        return []

    root_items: list[NormalizedItem] = []
    current_section: NormalizedItem | None = None
    current_race: NormalizedItem | None = None
    current_entity: NormalizedItem | None = None

    # Track what we're currently inside
    race_names = {"Terran", "Protoss", "Zerg", "TERRAN", "PROTOSS", "ZERG"}

    for element in blog.children:
        if isinstance(element, NavigableString):
            continue

        if not element.name:
            continue

        # H2 headers: Could be section OR race
        if element.name == "h2":
            text = element.get_text(strip=True)

            # Is it a race?
            if text in race_names:
                race_item = NormalizedItem(type="race", text=text, children=[], level=1)
                root_items.append(race_item)
                current_race = race_item
                current_entity = None
                # Don't reset section
            else:
                # It's a section header
                section_item = NormalizedItem(type="section", text=text, children=[], level=0)
                root_items.append(section_item)
                current_section = section_item
                current_race = None
                current_entity = None

        # H3 headers: Could be race OR section OR entity
        elif element.name == "h3":
            text = element.get_text(strip=True)
            text_upper = text.upper()

            if text in race_names:
                # It's a race
                race_item = NormalizedItem(type="race", text=text, children=[], level=1)
                if current_section:
                    current_section.children.append(race_item)
                else:
                    root_items.append(race_item)
                current_race = race_item
                current_entity = None
            elif any(
                keyword in text_upper
                for keyword in ["BUG", "FIX", "CO-OP", "COOP", "GENERAL", "QUALITY OF LIFE", "BALANCE"]
            ):
                # It's a section header (not race, not short entity name)
                section_item = NormalizedItem(type="section", text=text, children=[], level=0)
                root_items.append(section_item)
                current_section = section_item
                current_race = None
                current_entity = None
            else:
                # Treat as entity
                entity_item = NormalizedItem(type="entity", text=text, children=[], level=2)
                if current_race:
                    current_race.children.append(entity_item)
                elif current_section:
                    current_section.children.append(entity_item)
                else:
                    root_items.append(entity_item)
                current_entity = entity_item

        # H4 headers: Always entity names
        elif element.name == "h4":
            text = element.get_text(strip=True)
            entity_item = NormalizedItem(type="entity", text=text, children=[], level=2)

            if current_race:
                current_race.children.append(entity_item)
            elif current_section:
                current_section.children.append(entity_item)
            else:
                root_items.append(entity_item)
            current_entity = entity_item

        # P with B/STRONG tag: Could be race or entity name (legacy pattern)
        elif element.name == "p":
            b_tag = element.find("b")
            strong_tag = element.find("strong")
            tag = b_tag or strong_tag

            if tag:
                text = tag.get_text(strip=True)
                # Short text is likely entity or race name
                if text and len(text) < 50:
                    # Check if it's a race name
                    if text in race_names:
                        # It's a race
                        race_item = NormalizedItem(type="race", text=text, children=[], level=1)

                        if current_section:
                            current_section.children.append(race_item)
                        else:
                            root_items.append(race_item)
                        current_race = race_item
                        current_entity = None
                    else:
                        # It's an entity
                        entity_item = NormalizedItem(type="entity", text=text, children=[], level=2)

                        if current_race:
                            current_race.children.append(entity_item)
                        elif current_section:
                            current_section.children.append(entity_item)
                        else:
                            root_items.append(entity_item)
                        current_entity = entity_item

        # UL: Extract all LI items as changes
        elif element.name == "ul":
            for li in element.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if not text:
                    continue

                # Check if this LI has nested structure (entity > changes pattern)
                strong = li.find("strong")
                nested_ul = li.find("ul")

                if strong and nested_ul:
                    # Pattern: <li><strong>Entity/Race/Section</strong><ul><li>change</li></ul></li>
                    item_text = strong.get_text(strip=True)
                    item_text_upper = item_text.upper()

                    # Check if this is a section keyword
                    if any(
                        keyword in item_text_upper
                        for keyword in [
                            "BUG",
                            "FIX",
                            "CO-OP",
                            "COOP",
                            "GENERAL",
                            "QUALITY OF LIFE",
                            "BALANCE UPDATE",
                            "BALANCE",
                            "MAPS",
                        ]
                    ):
                        # It's a sub-section
                        section_item = NormalizedItem(
                            type="section", text=item_text, children=[], level=0
                        )
                        if current_section:
                            current_section.children.append(section_item)
                        else:
                            root_items.append(section_item)

                        # Recurse into nested UL to process its contents
                        for nested_li in nested_ul.find_all("li", recursive=False):
                            nested_strong = nested_li.find("strong")
                            nested_nested_ul = nested_li.find("ul")

                            if nested_strong and nested_nested_ul:
                                nested_text = nested_strong.get_text(strip=True)

                                # Check if it's a race
                                if nested_text in race_names:
                                    race_item = NormalizedItem(
                                        type="race", text=nested_text, children=[], level=1
                                    )
                                    section_item.children.append(race_item)

                                    # Process entities under this race
                                    for entity_li in nested_nested_ul.find_all("li", recursive=False):
                                        entity_strong = entity_li.find("strong")
                                        entity_ul = entity_li.find("ul")

                                        if entity_strong and entity_ul:
                                            entity_text = entity_strong.get_text(strip=True)
                                            entity_item = NormalizedItem(
                                                type="entity", text=entity_text, children=[], level=2
                                            )
                                            race_item.children.append(entity_item)

                                            # Process changes under entity
                                            for change_li in entity_ul.find_all("li", recursive=False):
                                                change_text = change_li.get_text(strip=True)
                                                if change_text:
                                                    change_item = NormalizedItem(
                                                        type="change",
                                                        text=change_text,
                                                        children=[],
                                                        level=3,
                                                    )
                                                    entity_item.children.append(change_item)

                    # Check if this is a race name
                    elif item_text in race_names:
                        # It's a race
                        race_item = NormalizedItem(
                            type="race", text=item_text, children=[], level=1
                        )

                        # Add race to current section or root
                        if current_section:
                            current_section.children.append(race_item)
                        else:
                            root_items.append(race_item)
                        current_race = race_item
                        current_entity = None

                        # Extract nested items (which will be entities)
                        for nested_li in nested_ul.find_all("li", recursive=False):
                            nested_strong = nested_li.find("strong")
                            nested_nested_ul = nested_li.find("ul")

                            if nested_strong and nested_nested_ul:
                                # Entity under race
                                entity_text = nested_strong.get_text(strip=True)
                                entity_item = NormalizedItem(
                                    type="entity", text=entity_text, children=[], level=2
                                )
                                race_item.children.append(entity_item)

                                # Extract changes under entity
                                for change_li in nested_nested_ul.find_all("li", recursive=False):
                                    change_text = change_li.get_text(strip=True)
                                    if change_text:
                                        change_item = NormalizedItem(
                                            type="change", text=change_text, children=[], level=3
                                        )
                                        entity_item.children.append(change_item)
                    else:
                        # It's an entity
                        entity_item = NormalizedItem(
                            type="entity", text=item_text, children=[], level=2
                        )

                        # Add entity to current parent
                        if current_race:
                            current_race.children.append(entity_item)
                        elif current_section:
                            current_section.children.append(entity_item)
                        else:
                            root_items.append(entity_item)

                        # Extract nested changes
                        for nested_li in nested_ul.find_all("li", recursive=False):
                            change_text = nested_li.get_text(strip=True)
                            if change_text:
                                change_item = NormalizedItem(
                                    type="change", text=change_text, children=[], level=3
                                )
                                entity_item.children.append(change_item)

                elif nested_ul:
                    # Pattern: <li>Entity<ul><li>change</li></ul></li> (no <strong> tag)
                    # Get only the direct text of this LI, not nested text
                    entity_text = li.find(text=True, recursive=False)
                    if entity_text:
                        entity_text = entity_text.strip()
                        if entity_text:
                            entity_item = NormalizedItem(
                                type="entity", text=entity_text, children=[], level=2
                            )

                            # Add entity to current parent
                            if current_race:
                                current_race.children.append(entity_item)
                            elif current_section:
                                current_section.children.append(entity_item)
                            else:
                                root_items.append(entity_item)

                            # Extract nested changes
                            for nested_li in nested_ul.find_all("li", recursive=False):
                                change_text = nested_li.get_text(strip=True)
                                if change_text:
                                    change_item = NormalizedItem(
                                        type="change", text=change_text, children=[], level=3
                                    )
                                    entity_item.children.append(change_item)

                else:
                    # Regular change item
                    change_item = NormalizedItem(type="change", text=text, children=[], level=3)

                    if current_entity:
                        current_entity.children.append(change_item)
                    elif current_race:
                        current_race.children.append(change_item)
                    elif current_section:
                        current_section.children.append(change_item)
                    else:
                        root_items.append(change_item)

    return root_items
