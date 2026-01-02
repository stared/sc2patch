"""Parse SC2 patch notes HTML with LLM via OpenRouter."""

import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from sc2patches.core.extraction import extract_body_html, extract_date_from_jsonld
from sc2patches.core.llm_config import DEFAULT_MODEL
from sc2patches.core.models import ChangeType, ParsedChange, ParsedPatch, Race

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


# LLM response models (Field descriptions are used in LLM prompt)
class LLMChange(BaseModel):
    text: str = Field(description="Exact change text with all numeric values preserved verbatim from source")
    change_type: ChangeType = Field(description="Type: buff, nerf, or mixed")


class LLMEntityChanges(BaseModel):
    entity_id: str = Field(description="Entity ID: race-unit_name (e.g., 'terran-marine')")
    entity_name: str = Field(description="Display name (e.g., 'Marine')")
    race: Race = Field(description="Race: terran, protoss, zerg, or neutral")
    changes: list[LLMChange] = Field(description="List of changes with classification")


class LLMPatchResponse(BaseModel):
    version: str = Field(description="Patch version (e.g., '4.0')")
    date: str | None = Field(default=None, description="Patch date YYYY-MM-DD")
    changes: list[LLMEntityChanges] = Field(description="All balance changes")


def flatten_llm_response(llm_response: LLMPatchResponse) -> list[ParsedChange]:
    """Flatten LLM grouped response to flat ParsedChange list."""
    return [
        ParsedChange(entity_id=entity.entity_id, raw_text=change.text, change_type=change.change_type)
        for entity in llm_response.changes
        for change in entity.changes
    ]


def extract_body_from_html(html_path: Path) -> str:
    """Extract article body text from HTML file."""
    body_html = extract_body_html(html_path.read_text(encoding="utf-8"))
    return BeautifulSoup(body_html, "html.parser").get_text(separator="\n", strip=True)


def extract_bodies_from_html_files(html_paths: list[Path]) -> str:
    """Combine bodies from multiple HTML files with section markers."""
    sections = []
    for i, path in enumerate(html_paths):
        header = "PRIMARY PATCH NOTES" if i == 0 else "ADDITIONAL PATCH NOTES (Balance Update)"
        sections.append(f"=== {header} ===\n\n{extract_body_from_html(path)}")
    return "\n\n" + "=" * 50 + "\n\n".join(sections)


def extract_date_from_html(html_path: Path) -> str | None:
    """Extract date from HTML JSON-LD metadata."""
    return extract_date_from_jsonld(html_path.read_text(encoding="utf-8"))


def parse_with_llm(
    body_text: str,
    version: str,
    api_key: str,
    is_multi_source: bool = False,
    parse_hint: str | None = None,
    model: str | None = None,
) -> LLMPatchResponse:
    """Call OpenRouter LLM to extract balance changes from patch text."""
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

CRITICAL: Preserve ALL numeric values EXACTLY as written in the source text.
- WRONG: "Armor upgrade cost reduced" (missing values!)
- RIGHT: "Armor upgrade cost reduced from 150/150, 225/225, 300/300 to 150/150, 200/200, 250/250"

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
                "model": model or DEFAULT_MODEL,
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
        return LLMPatchResponse(**parsed_data)

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ParseError(f"Failed to parse LLM response: {e}") from e


def parse_patch(html_path: Path, version: str, api_key: str, parse_hint: str | None = None) -> ParsedPatch:
    """Parse single HTML file, return ParsedPatch."""
    body_text = extract_body_from_html(html_path)
    html_date = extract_date_from_html(html_path)
    llm_response = parse_with_llm(body_text, version, api_key, parse_hint=parse_hint)
    changes = flatten_llm_response(llm_response)

    if not changes:
        raise ParseError(f"No balance changes from {html_path.name}")

    return ParsedPatch(
        version=llm_response.version,
        date=html_date or llm_response.date or "unknown",
        url="",
        changes=changes,
    )


def parse_patches_combined(html_paths: list[Path], version: str, api_key: str, parse_hint: str | None = None) -> ParsedPatch:
    """Parse multiple HTML files together (main + BU), return merged ParsedPatch."""
    if not html_paths:
        raise ParseError("No HTML files provided")

    body_text = extract_bodies_from_html_files(html_paths)

    # Use date from last file (Balance Update is later)
    html_date = next((extract_date_from_html(p) for p in reversed(html_paths) if extract_date_from_html(p)), None)

    llm_response = parse_with_llm(body_text, version, api_key, is_multi_source=True, parse_hint=parse_hint)
    changes = flatten_llm_response(llm_response)

    if not changes:
        raise ParseError(f"No balance changes from {[p.name for p in html_paths]}")

    return ParsedPatch(
        version=llm_response.version,
        date=html_date or llm_response.date or "unknown",
        url="",
        changes=changes,
    )
