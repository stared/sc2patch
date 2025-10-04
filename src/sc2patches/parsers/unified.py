"""Unified parser that works on normalized tree structure."""

from bs4 import BeautifulSoup

from ..models import Race, SourceSection
from ..normalize import NormalizedItem, normalize_html_to_tree
from ..parse import PatchMetadata, RawChange, detect_entity_from_text, load_units_database
from .base import PatternParser


class UnifiedParser(PatternParser):
    """Parser that works on normalized tree structure.

    This parser accepts any HTML pattern because it works on the
    normalized intermediate representation.
    """

    def __init__(self):
        self.units_db = load_units_database()

    @property
    def name(self) -> str:
        return "unified"

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Always returns True - this parser handles all patterns."""
        return True

    def _detect_section_type(self, text: str) -> SourceSection:
        """Determine section type from header text."""
        text_upper = text.upper()

        if "BUG" in text_upper or "FIX" in text_upper:
            return SourceSection.BUG_FIXES
        if "CO-OP" in text_upper or "COOP" in text_upper:
            return SourceSection.COOP
        if "VERSUS" in text_upper or "BALANCE" in text_upper:
            return SourceSection.VERSUS_BALANCE
        if "GENERAL" in text_upper:
            return SourceSection.GENERAL

        return SourceSection.UNKNOWN

    def _extract_changes_from_tree(
        self,
        items: list[NormalizedItem],
        current_race: Race | None = None,
        current_section: SourceSection = SourceSection.UNKNOWN,
        current_entity: str | None = None,
    ) -> list[RawChange]:
        """Recursively extract changes from normalized tree.

        Args:
            items: List of normalized items to process
            current_race: Current race context
            current_section: Current section type
            current_entity: Current entity ID

        Returns:
            List of RawChange objects
        """
        changes = []
        race_map = {
            "Terran": Race.TERRAN,
            "TERRAN": Race.TERRAN,
            "Protoss": Race.PROTOSS,
            "PROTOSS": Race.PROTOSS,
            "Zerg": Race.ZERG,
            "ZERG": Race.ZERG,
        }

        for item in items:
            if item.type == "section":
                # Update section context
                section_type = self._detect_section_type(item.text)
                # Recurse with new section
                changes.extend(
                    self._extract_changes_from_tree(
                        item.children,
                        current_race=current_race,
                        current_section=section_type,
                        current_entity=current_entity,
                    )
                )

            elif item.type == "race":
                # Update race context
                race = race_map.get(item.text)
                if race:
                    # Default to balance section if not set
                    if current_section == SourceSection.UNKNOWN:
                        current_section = SourceSection.VERSUS_BALANCE

                    changes.extend(
                        self._extract_changes_from_tree(
                            item.children,
                            current_race=race,
                            current_section=current_section,
                            current_entity=None,
                        )
                    )

            elif item.type == "entity":
                # Update entity context
                if current_race:
                    entity_id = detect_entity_from_text(item.text, current_race, self.units_db)
                    changes.extend(
                        self._extract_changes_from_tree(
                            item.children,
                            current_race=current_race,
                            current_section=current_section,
                            current_entity=entity_id,
                        )
                    )
                else:
                    # No race context - might be from nested structure
                    # Try to detect race from entity name
                    for race_str, entities in self.units_db.items():
                        if item.text in entities:
                            race = Race(race_str)
                            entity_id = entities[item.text]
                            changes.extend(
                                self._extract_changes_from_tree(
                                    item.children,
                                    current_race=race,
                                    current_section=current_section,
                                    current_entity=entity_id,
                                )
                            )
                            break

            elif item.type == "change":
                # This is an actual balance change
                if not current_race:
                    # Try to detect race from text (for nested patterns without race headers)
                    for race_name, race_enum in race_map.items():
                        if item.text.startswith(race_name):
                            current_race = race_enum
                            # Remove race prefix
                            item.text = item.text[len(race_name) :].strip()
                            break

                if not current_race:
                    # Default to neutral
                    current_race = Race.NEUTRAL

                # Filter UI/visual changes (not balance)
                text_lower = item.text.lower()

                # Patterns that indicate UI/cosmetic changes (not balance)
                ui_patterns = [
                    "button",
                    "tab-select",
                    "icon",
                    "wireframe",
                    "tooltip",
                    "sound",
                    "graphic",
                    "particle effect",
                    "visual animation",
                    "cosmetic",
                ]

                # Only filter if it matches UI pattern
                # Note: "model size" affects hitbox (balance), so don't filter
                # Note: "animation" alone could affect timing (balance), so don't filter
                if any(pattern in text_lower for pattern in ui_patterns):
                    continue

                # Filter bug fixes and non-gameplay changes
                bug_fix_patterns = [
                    "fixed an issue",
                    "fixed a display issue",
                    "fixed a bug",
                    "fixed multiple",
                    "fixed various",
                ]
                if any(pattern in text_lower for pattern in bug_fix_patterns):
                    continue

                # Determine entity
                if current_entity:
                    entity_id = current_entity
                else:
                    entity_id = detect_entity_from_text(item.text, current_race, self.units_db)

                # Filter non-balance content
                # Only filter neutral entities if NOT in a balance section
                if entity_id.startswith("neutral-") and current_section not in [
                    SourceSection.VERSUS_BALANCE,
                    SourceSection.GENERAL,
                ]:
                    continue

                if current_section not in [
                    SourceSection.VERSUS_BALANCE,
                    SourceSection.UNKNOWN,
                    SourceSection.GENERAL,
                ]:
                    continue

                # Create change
                changes.append(
                    RawChange(
                        entity_id=entity_id,
                        raw_text=item.text,
                        section=current_section,
                    )
                )

        return changes

    def parse(self, soup: BeautifulSoup, metadata: PatchMetadata) -> list[RawChange]:
        """Parse HTML using normalized tree structure."""
        # Step 1: Normalize HTML to tree
        tree = normalize_html_to_tree(soup)

        # Step 2: Extract changes from tree
        changes = self._extract_changes_from_tree(tree)

        return changes
