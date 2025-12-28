"""Parse patch notes with LLM via OpenRouter."""

import json
import re
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Model to use for parsing
OPENROUTER_MODEL = "google/gemini-3-pro-preview"

# Path to units database
UNITS_JSON_PATH = Path(__file__).parent.parent.parent / "data" / "units.json"

# Path to parse exceptions (patch-specific prompt additions)
PARSE_EXCEPTIONS_PATH = Path(__file__).parent.parent.parent / "data" / "parse_exceptions.json"


def load_parse_exceptions() -> dict[str, str]:
    """Load patch-specific parsing exceptions.

    Returns a dict mapping patch version to additional prompt text.
    """
    if not PARSE_EXCEPTIONS_PATH.exists():
        return {}
    with PARSE_EXCEPTIONS_PATH.open() as f:
        return json.load(f)


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
    change_type: str = Field(description="Type: buff, nerf, or mixed")


class BalanceChange(BaseModel):
    """A single balance change for an entity."""

    entity_id: str = Field(
        description="Entity ID in format: race-unit_name (e.g., 'terran-marine')"
    )
    entity_name: str = Field(description="Display name of the entity (e.g., 'Marine')")
    race: str = Field(description="Race: 'terran', 'protoss', 'zerg', or 'neutral'")
    changes: list[Change] = Field(description="List of specific changes with classification")


class PatchChanges(BaseModel):
    """All balance changes in a patch."""

    version: str = Field(description="Patch version (e.g., '4.0', '3.8.0')")
    date: str | None = Field(
        default=None, description="Patch date in ISO format YYYY-MM-DD (if available)"
    )
    changes: list[BalanceChange] = Field(description="List of all balance changes")


def extract_body_from_html(html_path: Path) -> str:
    """Extract article body from HTML, removing HEAD and navigation.

    Args:
        html_path: Path to HTML file

    Returns:
        Body text content

    Raises:
        ParseError: If body cannot be extracted
    """
    with html_path.open(encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract article body - try multiple selectors
    body = None

    # Modern Blizzard pages
    if (
        (article := soup.find("section", class_="blog"))
        or (article := soup.find("article", class_="Content"))
        or (article := soup.find("div", id="content"))
        or (article := soup.find("div", class_="article-content"))
    ):
        body = article

    if not body:
        # Fallback: get everything after </head>
        if soup.body:
            body = soup.body
        else:
            raise ParseError(f"Could not find article body in {html_path}")

    # Get text content
    return body.get_text(separator="\n", strip=True)


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

    This is the authoritative source for patch dates, not LLM extraction.

    Args:
        html_path: Path to HTML file

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    with html_path.open(encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Find JSON-LD script tag
    script = soup.find("script", type="application/ld+json")
    if not script or not script.string:
        return None

    # Fix common JSON syntax error in Blizzard's JSON-LD
    json_str = script.string
    json_str = re.sub(r'(\])\s*("publisher")', r"\1,\2", json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or data.get("@type") != "NewsArticle":
        return None

    date_published = data.get("datePublished")
    if not date_published:
        return None

    # Parse ISO datetime to date
    try:
        dt = datetime.fromisoformat(date_published.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def parse_with_llm(
    body_text: str,
    version: str,
    api_key: str,
    is_multi_source: bool = False,
) -> PatchChanges:
    """Extract balance changes using LLM via OpenRouter.

    Args:
        body_text: Text content to parse
        version: Patch version (used for exception lookup and as hint to model)
        api_key: OpenRouter API key
        is_multi_source: If True, content contains multiple sources (main + BU) to merge

    Returns:
        Parsed patch changes

    Raises:
        ParseError: If parsing fails
    """

    # Load valid entity IDs and format for prompt
    valid_ids = load_valid_entity_ids()
    valid_ids_text = "\n".join(
        f"  {race.upper()}: {', '.join(ids)}" for race, ids in valid_ids.items()
    )

    # Load patch-specific exceptions
    exceptions = load_parse_exceptions()
    patch_exception = ""
    if version in exceptions:
        patch_exception = f"\n\n{exceptions[version]}\n"

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

    system_prompt = f"""You are a StarCraft II balance patch expert. Extract balance changes from patch notes.
{multi_source_header}{patch_exception}
CRITICAL: ONLY extract VERSUS (MULTIPLAYER) balance changes!

SECTION DETECTION - Patch notes have distinct sections separated by images/headers:
- MULTIPLAYER / VERSUS / BALANCE sections → INCLUDE these
- CO-OP MISSIONS / CO-OP COMMANDERS sections → EXCLUDE entirely
- CAMPAIGN / NOVA COVERT OPS sections → EXCLUDE entirely
- BUG FIXES / EDITOR sections → EXCLUDE entirely

HOW TO IDENTIFY VERSUS BALANCE CHANGES:
- Versus balance is usually under sections with race headers: "Terran", "Protoss", "Zerg"
- Changes listed directly under units (Marine, Stalker, Roach, etc.) are versus balance
- "General" subsections within race sections are versus balance

HOW TO IDENTIFY CO-OP CHANGES (EXCLUDE THESE):
- Sections followed by "Commanders", "Nova Covert Ops", "Campaign" are Co-op
- "General" sections NOT within the Multiplayer/Versus section are likely Co-op
- IMPORTANT: In patch notes, sections are separated by image tags (![...]). After the Zerg race
  section ends and before "Commanders"/"Campaign" sections, any changes are likely Co-op.
- If a "General" section appears AFTER all race-specific unit changes and BEFORE campaign/commander
  sections, those changes are Co-op, not versus

EXCLUDE these completely - DO NOT include them:
1. CO-OP COMMANDERS and their units/abilities:
   - Protoss: Alarak, Karax, Zeratul, Fenix, Artanis (commander abilities)
   - Terran: Swann, Mengsk, Nova, Tychus (and outlaws: Blaze, Nikara, Rattlesnake, Vega, etc.)
   - Zerg: Zagara, Stukov, Abathur, Dehaka, Stetmann (Gary, Mecha units), Kerrigan
   - Any mention of "Commander", "Mastery", "Talent", "Level unlock", "Prestige"

2. CO-OP SPECIFIC UNITS (not in Versus):
   - Infested units (Infested Marine, Infested Siege Tank, Infested Liberator, etc.)
   - Mecha units (Mecha Battlecarrier Lord, Mecha Infestor, etc.)
   - Hercules, Galleon, Sky Fury, Strike Fighter, Laser Drill
   - Aberration, Vile Roach, Bile Launcher
   - Automated Refinery, War Prism, etc.

3. CO-OP MUTATORS: Any mention of mutator names (e.g., "We Move Unseen")

4. CAMPAIGN-ONLY content

5. MAP-SPECIFIC changes (e.g., "Destructible Rocks added to Desert Oasis")

ONLY INCLUDE: Standard Versus/Multiplayer units, buildings, and upgrades!

For each changed entity (unit, building, upgrade, ability):
1. Create entity_id in format: race-entity_name (e.g., "terran-marine", "protoss-stalker")
2. Use lowercase with underscores for entity_id
3. Extract all specific changes as separate list items
4. Focus ONLY on balance changes (damage, cost, build time, etc.)
5. Ignore bug fixes, UI changes, and editor changes
6. Classify EACH change as (from the perspective of the ENTITY itself - stronger or weaker):
   - "buff": Entity becomes stronger (increased damage/health/armor, reduced cost, faster build time, etc.)
   - "nerf": Entity becomes weaker (decreased damage/health/armor, increased cost, slower build time, etc.)
   - "mixed": Has both positive and negative aspects

   IMPORTANT CLASSIFICATION EXAMPLES:
   - Rocks armor INCREASED → "buff" (rocks are stronger)
   - Rocks armor DECREASED → "nerf" (rocks are weaker)
   - Unit cost INCREASED → "nerf" (harder to build)
   - Unit cost DECREASED → "buff" (easier to build)

   DAMAGE TYPE RESTRICTION IS A NERF:
   - "Damage changed from 50 to 35 (+15 armored)" → "nerf" (NOT mixed!)
     Before: 50 to all. After: 50 to armored, 35 to non-armored = worse overall
   - "Upgrade damage changed from +5 to +3 (+2 armored)" → "nerf" (NOT mixed!)
     Before: +5 to all. After: +5 to armored, +3 to non-armored = worse overall
   - Adding a bonus type while reducing base is a NERF because effectiveness is restricted

UPGRADE PLACEMENT RULES:

1. GENERAL Upgrades (affects 3+ unit types) → attribute to RESEARCH BUILDING:
   - Infantry Weapons/Armor → terran-engineering_bay
   - Vehicle/Ship Weapons/Armor → terran-armory
   - Ground Weapons/Armor/Shields → protoss-forge
   - Air Weapons/Armor → protoss-cybernetics_core
   - Melee/Missile/Carapace → zerg-evolution_chamber
   - Flyer Attack/Carapace → zerg-spire

2. SPECIFIC Upgrades (affects 1-2 units) → attribute to the UNIT:
   Include both STAT changes AND RESEARCH cost/time changes on the unit.
   - Stimpack → terran-marine AND terran-marauder
   - Charge → protoss-zealot
   - Blink → protoss-stalker
   - Grooved Spines → zerg-hydralisk
   - Metabolic Boost → zerg-zergling
   - Anabolic Synthesis → zerg-ultralisk

3. SUMMONED UNITS → attribute to the CASTER:
   - Interceptor stats/build time → protoss-carrier
   - Locust stats → zerg-swarm_host
   - Auto-Turret stats → terran-raven
   - Broodling stats → zerg-brood_lord
   - Creep Tumor stats → zerg-queen

NEUTRAL ENTITIES - Map objects and mechanics:
- neutral-ramp (vision up/down ramps, ramp blocking rules, ramp width)
- neutral-vespene_geyser (footprint, visibility, yield changes)
- neutral-mineral_field (health, collision, harvest rate)
- neutral-rocks (armor, health changes) - ONLY IN VERSUS, ignore Co-op rocks
- neutral-collapsible_rock_tower
- neutral-inhibitor_zone_generator
- neutral-acceleration_zone_generator
- neutral-xelnaga_tower

GLOBAL MECHANIC CHANGES - Use neutral entity, NOT per-race duplicates:
- "Vision up ramps reduced" → ONE entry for neutral-ramp (NOT 3 entries per race!)
- "Ramp blocking rules changed" → ONE entry for neutral-ramp
- "Building placement on ramps" → ONE entry for neutral-ramp
These are map mechanics, not race-specific unit changes.

COMMONLY MISSED UNITS - check these explicitly:
- protoss-tempest (Tectonic Destabilizers upgrade)
- protoss-mothership (Strategic Recall, Mass Recall, Time Warp)
- terran-battlecruiser (Tactical Jump, Yamato Cannon)
- zerg-viper (Parasitic Bomb, Abduct)
- zerg-queen (Transfuse, Creep Tumor)

VISUAL CHANGES: Only include if they affect player reaction or clarity
(e.g., "targeting line more visible", "EMP radius indicator"). Ignore cosmetic-only changes.

VALID ENTITY IDS - You MUST use ONLY these exact IDs:
{valid_ids_text}

If an entity cannot be mapped to any ID above (e.g., new terrain element, new unit), use "unknown" as entity_id.

MORPHED/TOGGLE MODES - use the BASE unit ID (modes are NOT separate entities):
- Transport Overlord → zerg-overlord
- Siege Tank (Sieged mode) → terran-siege_tank
- Viking (Assault/Fighter modes) → terran-viking
- Lurker (Burrowed) → zerg-lurker
- Liberator (AG mode) → terran-liberator
- Warp Prism (Phasing mode) → protoss-warp_prism

NOTE: Hellion and Hellbat ARE separate units (use terran-hellion or terran-hellbat as appropriate)

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

CRITICAL: ALL fields (entity_id, entity_name, race, changes with text and change_type) are REQUIRED."""

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


def parse_patch(html_path: Path, version: str, api_key: str) -> dict:
    """Parse a single patch file and return structured JSON.

    Args:
        html_path: Path to HTML file
        version: Patch version from config (authoritative, used for exception lookup)
        api_key: OpenRouter API key

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
    patch_data = parse_with_llm(body_text, version, api_key)

    # Use HTML metadata date (authoritative), fallback to LLM date only if HTML has none
    authoritative_date = html_date or patch_data.date or "unknown"

    # Convert to output format
    result = {
        "metadata": {
            "version": patch_data.version,
            "date": authoritative_date,
            "title": f"StarCraft II Patch {patch_data.version}",
            "url": "",  # Will be filled in by pipeline script
        },
        "changes": [],
    }

    # Flatten changes
    for entity in patch_data.changes:
        for change in entity.changes:
            # VALIDATE: Every change MUST have change_type
            if not change.change_type:
                raise ParseError(
                    f"CRITICAL ERROR in {html_path.name}: Change missing change_type!\n"
                    f"Entity: {entity.entity_id}\n"
                    f"Text: {change.text}\n"
                    "Parser MUST classify every change."
                )

            # VALIDATE: change_type must be valid
            if change.change_type not in ["buff", "nerf", "mixed"]:
                raise ParseError(
                    f"CRITICAL ERROR in {html_path.name}: Invalid change_type '{change.change_type}'\n"
                    f"Entity: {entity.entity_id}\n"
                    f"Text: {change.text}\n"
                    f"Must be one of: buff, nerf, mixed"
                )

            change_id = f"{entity.entity_id}_{len(result['changes'])}"
            result["changes"].append(
                {
                    "id": change_id,
                    "patch_version": patch_data.version,
                    "entity_id": entity.entity_id,
                    "raw_text": change.text,
                    "change_type": change.change_type,
                }
            )

    # FAIL LOUDLY if no changes found
    if len(result["changes"]) == 0:
        raise ParseError(
            f"No balance changes extracted from {html_path.name}\n"
            "This patch may have no balance changes, or the parser failed."
        )

    return result


def parse_patches_combined(html_paths: list[Path], version: str, api_key: str) -> dict:
    """Parse multiple patch files together (main + BU) and return merged JSON.

    This is used when a patch has both a main client update and a Balance Update.
    The LLM sees both sources together and intelligently deduplicates.

    Args:
        html_paths: List of HTML files to parse together (main first, then additional)
        version: Patch version from config (authoritative, used for exception lookup)
        api_key: OpenRouter API key

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
    patch_data = parse_with_llm(body_text, version, api_key, is_multi_source=True)

    # Use HTML metadata date (authoritative), fallback to LLM date only if HTML has none
    authoritative_date = html_date or patch_data.date or "unknown"

    # Convert to output format (same as parse_patch)
    result = {
        "metadata": {
            "version": patch_data.version,
            "date": authoritative_date,
            "title": f"StarCraft II Patch {patch_data.version}",
            "url": "",  # Will be filled in by pipeline script
        },
        "changes": [],
    }

    # Flatten changes
    for entity in patch_data.changes:
        for change in entity.changes:
            # VALIDATE: Every change MUST have change_type
            if not change.change_type:
                raise ParseError(
                    f"CRITICAL ERROR: Change missing change_type!\n"
                    f"Entity: {entity.entity_id}\n"
                    f"Text: {change.text}\n"
                    "Parser MUST classify every change."
                )

            # VALIDATE: change_type must be valid
            if change.change_type not in ["buff", "nerf", "mixed"]:
                raise ParseError(
                    f"CRITICAL ERROR: Invalid change_type '{change.change_type}'\n"
                    f"Entity: {entity.entity_id}\n"
                    f"Text: {change.text}\n"
                    f"Must be one of: buff, nerf, mixed"
                )

            change_id = f"{entity.entity_id}_{len(result['changes'])}"
            result["changes"].append(
                {
                    "id": change_id,
                    "patch_version": patch_data.version,
                    "entity_id": entity.entity_id,
                    "raw_text": change.text,
                    "change_type": change.change_type,
                }
            )

    # FAIL LOUDLY if no changes found
    if len(result["changes"]) == 0:
        raise ParseError(
            f"No balance changes extracted from combined patches.\n"
            f"Files: {[p.name for p in html_paths]}"
        )

    return result
