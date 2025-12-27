"""Parse patch notes with LLM via OpenRouter."""

import json
import os
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Model to use for parsing
OPENROUTER_MODEL = "google/gemini-3-pro-preview"

# Path to units database
UNITS_JSON_PATH = Path(__file__).parent.parent.parent / "data" / "units.json"


def load_valid_entity_ids() -> dict[str, list[str]]:
    """Load valid entity_ids from units.json, grouped by race."""
    with open(UNITS_JSON_PATH) as f:
        units = json.load(f)

    by_race: dict[str, list[str]] = {"terran": [], "zerg": [], "protoss": [], "neutral": []}
    for unit in units:
        by_race[unit["race"]].append(unit["id"])

    for race in by_race:
        by_race[race].sort()

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
    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract article body - try multiple selectors
    body = None

    # Modern Blizzard pages
    if (article := soup.find("section", class_="blog")) or (article := soup.find("article", class_="Content")) or (article := soup.find("div", id="content")) or (article := soup.find("div", class_="article-content")):
        body = article

    if not body:
        # Fallback: get everything after </head>
        if soup.body:
            body = soup.body
        else:
            raise ParseError(f"Could not find article body in {html_path}")

    # Get text content
    body_text = body.get_text(separator="\n", strip=True)

    return body_text


def parse_with_llm(
    body_text: str, version_hint: str | None = None, api_key: str | None = None
) -> PatchChanges:
    """Extract balance changes using LLM via OpenRouter.

    Args:
        body_text: Text content to parse
        version_hint: Optional version hint for the model
        api_key: OpenRouter API key (uses OPENROUTER_API_KEY env var if not provided)

    Returns:
        Parsed patch changes

    Raises:
        ParseError: If parsing fails
    """
    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ParseError("OPENROUTER_API_KEY not found in environment")

    # Load valid entity IDs and format for prompt
    valid_ids = load_valid_entity_ids()
    valid_ids_text = "\n".join(
        f"  {race.upper()}: {', '.join(ids)}" for race, ids in valid_ids.items()
    )

    system_prompt = f"""You are a StarCraft II balance patch expert. Extract balance changes from patch notes.

CRITICAL: ONLY extract VERSUS (MULTIPLAYER) balance changes!

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

NEUTRAL ENTITIES - Don't forget map objects:
- neutral-vespene_geyser (footprint, visibility, yield changes)
- neutral-mineral_field (health, collision, harvest rate)
- neutral-rocks (armor, health changes)
- neutral-collapsible_rock_tower
- neutral-inhibitor_zone_generator
- neutral-acceleration_zone_generator
- neutral-xelnaga_tower

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

Version hint: {version_hint if version_hint else "Unknown - extract from content"}

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


def parse_patch(html_path: Path, api_key: str | None = None) -> dict:
    """Parse a single patch file and return structured JSON.

    Args:
        html_path: Path to HTML file
        api_key: Optional OpenRouter API key

    Returns:
        Dictionary with metadata and changes

    Raises:
        ParseError: If parsing fails
    """
    # Extract body text
    body_text = extract_body_from_html(html_path)

    # Try to infer version from filename
    version_hint = html_path.stem

    # Parse with LLM
    patch_data = parse_with_llm(body_text, version_hint, api_key)

    # Convert to output format
    result = {
        "metadata": {
            "version": patch_data.version,
            "date": patch_data.date or "unknown",
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
