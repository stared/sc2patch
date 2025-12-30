"""Parse patch notes with LLM via OpenRouter."""

import json
from pathlib import Path
from typing import Literal

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from sc2patches.extraction import extract_body_html, extract_date_from_jsonld

ChangeType = Literal["buff", "nerf", "mixed"]
Race = Literal["terran", "zerg", "protoss", "neutral"]

# Model to use for parsing
OPENROUTER_MODEL = "google/gemini-3-pro-preview"

# Path to units database
UNITS_JSON_PATH = Path(__file__).parent.parent.parent / "data" / "units.json"


def load_valid_entity_ids() -> dict[str, list[str]]:
    """Load valid entity_ids from units.json, grouped by race."""
    with UNITS_JSON_PATH.open() as f:
        units = json.load(f)

    by_race: dict[str, list[str]] = {"terran": [], "zerg": [], "protoss": [], "neutral": []}
    for unit in units:
        by_race[unit["race"]].append(unit["id"])

    for _race, ids in by_race.items():
        ids.sort()

    return by_race


class ParseError(Exception):
    """Raised when parsing fails."""


class Change(BaseModel):
    """A single balance change with classification."""

    text: str = Field(description="Description of the change")
    change_type: ChangeType = Field(description="Type: buff, nerf, or mixed")


class BalanceChange(BaseModel):
    """A single balance change for an entity."""

    entity_id: str = Field(description="Entity ID in format: race-unit_name (e.g., 'terran-marine')")
    entity_name: str = Field(description="Display name of the entity (e.g., 'Marine')")
    race: Race = Field(description="Race: 'terran', 'protoss', 'zerg', or 'neutral'")
    changes: list[Change] = Field(description="List of specific changes with classification")


class PatchChanges(BaseModel):
    """All balance changes in a patch."""

    version: str = Field(description="Patch version (e.g., '4.0', '3.8.0')")
    date: str | None = Field(default=None, description="Patch date in ISO format YYYY-MM-DD (if available)")
    changes: list[BalanceChange] = Field(description="List of all balance changes")


def flatten_changes(patch_data: PatchChanges) -> list[dict]:
    """Flatten entity changes into list of change dicts.

    Validation is handled by Pydantic models (ChangeType, Race are Literal types).

    Args:
        patch_data: Parsed patch data from LLM (already validated by Pydantic)

    Returns:
        List of flattened change dicts
    """
    changes = []
    for entity in patch_data.changes:
        for change in entity.changes:
            changes.append(
                {
                    "id": f"{entity.entity_id}_{len(changes)}",
                    "patch_version": patch_data.version,
                    "entity_id": entity.entity_id,
                    "raw_text": change.text,
                    "change_type": change.change_type,
                }
            )
    return changes


def extract_body_from_html(html_path: Path) -> str:
    """Extract article body text from HTML.

    Thin wrapper around extraction.extract_body_html.

    Args:
        html_path: Path to HTML file

    Returns:
        Body text content

    Raises:
        ExtractionError: If section.blog not found
    """
    html_content = html_path.read_text(encoding="utf-8")
    body_html = extract_body_html(html_content)
    soup = BeautifulSoup(body_html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def extract_bodies_from_html_files(html_paths: list[Path]) -> str:
    """Extract and combine article bodies from multiple HTML files.

    This is used for parsing main patch + BU patch together.

    Args:
        html_paths: List of HTML file paths

    Returns:
        Combined body text with clear section markers

    Raises:
        ParseError: If any body cannot be extracted
    """
    sections = []
    for i, path in enumerate(html_paths):
        body = extract_body_from_html(path)
        if i == 0:
            sections.append(f"=== PRIMARY PATCH NOTES ===\n\n{body}")
        else:
            sections.append(f"=== ADDITIONAL PATCH NOTES (Balance Update) ===\n\n{body}")

    return "\n\n" + "=" * 50 + "\n\n".join(sections)


def extract_date_from_html(html_path: Path) -> str | None:
    """Extract date from HTML JSON-LD metadata.

    Thin wrapper around extraction.extract_date_from_jsonld.

    Args:
        html_path: Path to HTML file

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    html_content = html_path.read_text(encoding="utf-8")
    return extract_date_from_jsonld(html_content)


def parse_with_llm(
    body_text: str,
    version: str,
    api_key: str,
    is_multi_source: bool = False,
    parse_hint: str | None = None,
) -> PatchChanges:
    """Extract balance changes using LLM via OpenRouter.

    Args:
        body_text: Text content to parse
        version: Patch version (hint to model)
        api_key: OpenRouter API key
        is_multi_source: If True, content contains multiple sources (main + BU) to merge
        parse_hint: Optional patch-specific instructions for the LLM

    Returns:
        Parsed patch changes

    Raises:
        ParseError: If parsing fails
    """

    # Load valid entity IDs and format for prompt
    valid_ids = load_valid_entity_ids()
    valid_ids_text = "\n".join(f"  {race.upper()}: {', '.join(ids)}" for race, ids in valid_ids.items())

    # Format patch-specific hint if provided
    patch_exception = f"\n\nPATCH-SPECIFIC: {parse_hint}\n" if parse_hint else ""

    # Add multi-source instructions if combining multiple HTML files
    multi_source_header = ""
    if is_multi_source:
        multi_source_header = """
IMPORTANT: You are parsing MULTIPLE patch notes for the SAME version:
1. PRIMARY PATCH NOTES: Main client patch (may include balance changes + bug fixes)
2. ADDITIONAL PATCH NOTES: Balance Update (server-side balance changes)

Combine ALL balance changes into ONE unified list. DEDUPLICATE:
- If the SAME entity has the SAME change in both sources, include it ONLY ONCE
- If sources have DIFFERENT values for same stat, use the LATER (Balance Update) value
- Use the LATER date (from Balance Update section) as the patch date

"""

    system_prompt = f"""You are a StarCraft II Balance Patch Analyst. Extract and classify VERSUS (multiplayer) balance changes.
{multi_source_header}{patch_exception}
=== 1. SCOPE: VERSUS ONLY ===

INCLUDE sections labeled: "Versus", "Multiplayer", "Balance", or race headers (Terran/Zerg/Protoss).

EXCLUDE completely:
- Co-op Missions: Commanders, Mutators, Prestige, Mastery, hero units (Alarak, Nova, Zagara, etc.)
- Co-op units: Infested Terrans, Mecha Zerg, Hercules, War Prism, etc.
- Campaign/Nova Covert Ops content
- Bug fixes (unless explicitly a balance adjustment)
- Map-specific changes (e.g., "Rocks added to [Map Name]")

=== 2. ENTITY IDENTIFICATION ===

Format: `race-unit_name` (lowercase, underscores). Example: `terran-marine`, `protoss-stalker`

ASSIGNMENT RULES:
1. MORPHS/MODES → assign to BASE unit:
   - Siege Tank (Sieged) → terran-siege_tank
   - Lurker (Burrowed) → zerg-lurker
   - Viking modes → terran-viking
   - EXCEPTION: Hellion/Hellbat are separate units

2. SUMMONED UNITS → assign to PARENT:
   - Interceptor → protoss-carrier
   - M.U.L.E. → terran-orbital_command
   - Broodling → zerg-brood_lord
   - Locust → zerg-swarm_host
   - Auto-Turret → terran-raven

3. UPGRADES:
   - Affects 1-2 units → assign to the UNIT (Stimpack → terran-marine)
   - General/shared (3+ units) → assign to RESEARCH BUILDING (terran-engineering_bay)

4. NEUTRAL ENTITIES: neutral-rocks, neutral-ramp, neutral-mineral_field, etc.
   Global changes (e.g., "vision up ramps") → ONE neutral entry, not per-race duplicates.

VALID ENTITY IDS (use ONLY these):
{valid_ids_text}

=== 3. CLASSIFICATION LOGIC ===

Classify from the ENTITY's perspective: does this make it stronger or weaker?
- "buff": Entity stronger, cheaper, faster, more reliable
- "nerf": Entity weaker, more expensive, slower, easier to counter
- "mixed": Both positive and negative mathematical impacts

SPECIFIC RULES:

A) DAMAGE SPECIALIZATION = NERF:
   "Damage 50 → 35 (+15 vs Armored)" = NERF (reduced effectiveness vs non-armored)

B) RELIABILITY IMPROVEMENTS = BUFF:
   - "No longer detonates on contact" = BUFF (enemy can't trigger early with cheap unit)
   - "Won't trigger on structures/changelings" = BUFF (prevents wasting on low-value targets)
   - "Removed random delay" = BUFF (more consistent)

C) NEUTRAL ENTITIES (Rocks/Debris):
   - Armor/HP increased → BUFF (rock is stronger)
   - Armor/HP decreased → NERF (rock is weaker)

D) VISUAL/UI CHANGES - "Who Sees It?" Rule:
   - OPPONENT sees it → NERF (reveals info to enemy)
     Examples: upgrade indicators visible to enemy, larger model easier to spot, targeting lines
   - ONLY YOU see it → BUFF (helps your play)
     Examples: placement range helpers, your own ability radius displays
   - Pure cosmetic (icons, portraits, textures) → EXCLUDE

=== 4. OUTPUT FORMAT ===

Return JSON in this EXACT format:
{{
  "version": "4.0",
  "date": "2017-11-15",
  "changes": [
    {{
      "entity_id": "terran-marine",
      "entity_name": "Marine",
      "race": "terran",
      "changes": [
        {{"text": "Health increased from 45 to 55", "change_type": "buff"}},
        {{"text": "Attack damage reduced from 6 to 5", "change_type": "nerf"}}
      ]
    }}
  ]
}}

ALL fields (entity_id, entity_name, race, changes with text and change_type) are REQUIRED."""

    user_prompt = f"""Extract all balance changes from this StarCraft II patch:

{body_text}

Version: {version}

Return ONLY valid JSON matching the example format. Include ALL required fields."""

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/stared/sc2-balance-timeline",
                "X-Title": "SC2 Patch Parser",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 16000,
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise ParseError(f"HTTP request failed: {e}") from e

    try:
        result = response.json()

        # Check for API errors
        if "error" in result:
            raise ParseError(f"API error: {result['error']}")

        # Check for empty choices
        if not result.get("choices"):
            raise ParseError(f"Empty choices in API response: {result}")

        content = result["choices"][0]["message"]["content"]

        # Check for empty content
        if not content or not content.strip():
            raise ParseError(f"Empty content from API. Full response: {result}")

        # Parse JSON response
        parsed_data = json.loads(content)
        return PatchChanges(**parsed_data)

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ParseError(f"Failed to parse LLM response: {e}") from e


def parse_patch(html_path: Path, version: str, api_key: str, parse_hint: str | None = None) -> dict:
    """Parse a single patch file and return structured JSON.

    Args:
        html_path: Path to HTML file
        version: Patch version from config
        api_key: OpenRouter API key
        parse_hint: Optional patch-specific instructions for the LLM

    Returns:
        Dictionary with metadata and changes

    Raises:
        ParseError: If parsing fails
    """
    # Extract body text
    body_text = extract_body_from_html(html_path)

    # Extract date from HTML metadata (authoritative source)
    html_date = extract_date_from_html(html_path)

    # Parse with LLM
    patch_data = parse_with_llm(body_text, version, api_key, parse_hint=parse_hint)

    # Use HTML metadata date (authoritative), fallback to LLM date only if HTML has none
    authoritative_date = html_date or patch_data.date or "unknown"

    # Flatten changes (validation done by Pydantic)
    changes = flatten_changes(patch_data)

    if not changes:
        raise ParseError(
            f"No balance changes extracted from {html_path.name}\nThis patch may have no balance changes, or the parser failed."
        )

    return {
        "metadata": {
            "version": patch_data.version,
            "date": authoritative_date,
            "title": f"StarCraft II Patch {patch_data.version}",
            "url": "",  # Will be filled in by pipeline script
        },
        "changes": changes,
    }


def parse_patches_combined(html_paths: list[Path], version: str, api_key: str, parse_hint: str | None = None) -> dict:
    """Parse multiple patch files together (main + BU) and return merged JSON.

    This is used when a patch has both a main client update and a Balance Update.
    The LLM sees both sources together and intelligently deduplicates.

    Args:
        html_paths: List of HTML files to parse together (main first, then additional)
        version: Patch version from config
        api_key: OpenRouter API key
        parse_hint: Optional patch-specific instructions for the LLM

    Returns:
        Dictionary with metadata and merged changes

    Raises:
        ParseError: If parsing fails
    """
    if not html_paths:
        raise ParseError("No HTML files provided to parse_patches_combined")

    # Extract combined body text from all files
    body_text = extract_bodies_from_html_files(html_paths)

    # Extract date from LAST file (Balance Update has the later date)
    # This is when ALL changes were live
    html_date = None
    for path in reversed(html_paths):
        html_date = extract_date_from_html(path)
        if html_date:
            break

    # Parse with LLM in multi-source mode
    patch_data = parse_with_llm(body_text, version, api_key, is_multi_source=True, parse_hint=parse_hint)

    # Use HTML metadata date (authoritative), fallback to LLM date only if HTML has none
    authoritative_date = html_date or patch_data.date or "unknown"

    # Flatten changes (validation done by Pydantic)
    changes = flatten_changes(patch_data)

    if not changes:
        raise ParseError(f"No balance changes extracted from combined patches: {[p.name for p in html_paths]}")

    return {
        "metadata": {
            "version": patch_data.version,
            "date": authoritative_date,
            "title": f"StarCraft II Patch {patch_data.version}",
            "url": "",  # Will be filled in by pipeline script
        },
        "changes": changes,
    }
