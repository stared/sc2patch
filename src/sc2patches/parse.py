"""Parse balance changes from StarCraft 2 patch HTML files."""

import json
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from .models import Race, SourceSection


class ParseError(Exception):
    """Raised when HTML parsing fails."""


@dataclass
class RawChange:
    """Unparsed change extracted from HTML."""

    entity_id: str
    raw_text: str
    section: SourceSection


@dataclass
class PatchMetadata:
    """Metadata extracted from Markdown frontmatter."""

    version: str
    date: str
    title: str
    url: str


def extract_markdown_metadata(md_path: Path) -> PatchMetadata:
    """Extract metadata from Markdown frontmatter.

    Args:
        md_path: Path to Markdown file

    Returns:
        PatchMetadata

    Raises:
        ParseError: If metadata extraction fails
    """
    if not md_path.exists():
        raise ParseError(f"Markdown file not found: {md_path}")

    content = md_path.read_text(encoding="utf-8")

    # Parse frontmatter
    if not content.startswith("---"):
        raise ParseError("No frontmatter found in Markdown")

    lines = content.split("\n")
    metadata = {}

    # Extract key-value pairs from frontmatter
    for line in lines[1:]:  # Skip first ---
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    # Validate required fields
    required = ["version", "date", "title", "url"]
    for field in required:
        if field not in metadata:
            raise ParseError(f"Missing required metadata field: {field}")

    return PatchMetadata(
        version=metadata["version"],
        date=metadata["date"],
        title=metadata["title"],
        url=metadata["url"],
    )


def detect_section_type(header_text: str) -> SourceSection:
    """Determine section type from header text.

    Args:
        header_text: Text from H2/H3 header

    Returns:
        SourceSection enum value
    """
    text_upper = header_text.upper()

    if "BUG" in text_upper or "FIX" in text_upper:
        return SourceSection.BUG_FIXES
    if "CO-OP" in text_upper or "COOP" in text_upper:
        return SourceSection.COOP
    if "VERSUS" in text_upper or "BALANCE" in text_upper:
        return SourceSection.VERSUS_BALANCE
    if "GENERAL" in text_upper:
        return SourceSection.GENERAL

    return SourceSection.UNKNOWN


def load_units_database() -> dict[str, dict[str, str]]:
    """Load units database and build lookup dictionary.

    Returns:
        Dict mapping race to dict of {name: entity_id}
    """
    units_path = Path("data/units.json")
    if not units_path.exists():
        raise ParseError(f"Units database not found: {units_path}")

    with units_path.open() as f:
        units_list = json.load(f)

    # Build lookup by race: {race: {name: id}}
    race_entities = {"terran": {}, "protoss": {}, "zerg": {}}

    for entity in units_list:
        race = entity["race"]
        name = entity["name"]
        entity_id = entity["id"]
        if race in race_entities:
            race_entities[race][name] = entity_id

    return race_entities


def detect_entity_from_text(text: str, race: Race, units_db: dict[str, dict[str, str]]) -> str:
    """Detect entity ID from change text.

    Args:
        text: Change text (e.g., "Spire cost reduced from 200/200 to 150/150.")
        race: Current race context
        units_db: Units database from load_units_database()

    Returns:
        Entity ID if detected (e.g., "zerg-spire"), otherwise "{race}-unknown"
    """
    race_key = race.value
    known_entities = units_db.get(race_key, {})

    # Check each known entity - longest match first (e.g., "Widow Mine" before "Mine")
    sorted_names = sorted(known_entities.keys(), key=len, reverse=True)

    for entity_name in sorted_names:
        if entity_name.lower() in text.lower():
            return known_entities[entity_name]

    return f"{race_key}-unknown"


def normalize_entity_name(name: str) -> str:
    """Normalize entity name to snake_case ID format.

    Args:
        name: Entity name (e.g., "Widow Mine", "High Templar")

    Returns:
        Normalized name (e.g., "widow_mine", "high_templar")
    """
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def extract_changes_from_list(ul_element, race: Race, section: SourceSection, units_db: dict[str, dict[str, str]]) -> list[RawChange]:
    """Extract changes from a <ul> list element.

    This handles flat lists where each <li> is a single change.

    Args:
        ul_element: BeautifulSoup <ul> element
        race: Current race context
        section: Current section type
        units_db: Units database for entity detection

    Returns:
        List of RawChange objects
    """
    changes = []

    for li in ul_element.find_all("li", recursive=False):
        text = li.get_text(strip=True)
        if text:
            # Detect entity ID from text
            entity_id = detect_entity_from_text(text, race, units_db)

            changes.append(
                RawChange(
                    entity_id=entity_id,
                    raw_text=text,
                    section=section,
                )
            )

    return changes


def parse_patch_html(html_path: Path, md_path: Path) -> tuple[PatchMetadata, list[RawChange]]:
    """Parse patch HTML file to extract balance changes.

    This is a simplified first version that handles the most common pattern.
    Will be expanded to handle all patterns in subsequent iterations.

    Args:
        html_path: Path to HTML file
        md_path: Path to corresponding Markdown file

    Returns:
        Tuple of (metadata, list of changes)

    Raises:
        ParseError: If parsing fails
    """
    # Extract metadata from Markdown
    metadata = extract_markdown_metadata(md_path)

    # Load units database for entity detection
    units_db = load_units_database()

    # Parse HTML
    if not html_path.exists():
        raise ParseError(f"HTML file not found: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog_section = soup.find("section", class_="blog")
    if not blog_section:
        raise ParseError("No <section class='blog'> found in HTML")

    changes = []
    current_race = None
    current_section = SourceSection.UNKNOWN

    # Pattern 1: Direct H2 headers with race names (5.0.15 style)
    race_names = {"Zerg": Race.ZERG, "Protoss": Race.PROTOSS, "Terran": Race.TERRAN}

    for element in blog_section.children:
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
            for li in element.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text:
                    # Detect entity ID from text
                    entity_id = detect_entity_from_text(text, current_race, units_db)

                    changes.append(
                        RawChange(
                            entity_id=entity_id,
                            raw_text=text,
                            section=current_section,
                        )
                    )

    return metadata, changes
