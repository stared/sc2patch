"""Parse patch notes with GPT-5 via OpenRouter."""

import json
import os
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


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


def parse_with_gpt5(
    body_text: str, version_hint: str | None = None, api_key: str | None = None
) -> PatchChanges:
    """Extract balance changes using GPT-5.

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

    system_prompt = """You are a StarCraft II balance patch expert. Extract balance changes from patch notes.

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

UPGRADE-TO-UNIT MAPPINGS:
Assign upgrades/abilities to the UNIT they affect, NOT as separate entities:
- Stimpack → terran-marine AND terran-marauder (list change under BOTH)
- Charge → protoss-zealot
- Blink → protoss-stalker
- Grooved Spines → zerg-hydralisk
- Metabolic Boost → zerg-zergling
- etc.

Return JSON in this EXACT format:
{
  "version": "4.0",
  "date": "2017-11-15",
  "changes": [
    {
      "entity_id": "terran-marine",
      "entity_name": "Marine",
      "race": "terran",
      "changes": [
        {"text": "Health increased from 45 to 55", "change_type": "buff"},
        {"text": "Attack damage reduced from 6 to 5", "change_type": "nerf"}
      ]
    }
  ]
}

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
                "model": "openai/gpt-5",
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
        content = result["choices"][0]["message"]["content"]

        # Parse JSON response
        parsed_data = json.loads(content)
        return PatchChanges(**parsed_data)

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ParseError(f"Failed to parse GPT-5 response: {e}") from e


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

    # Parse with GPT-5
    patch_data = parse_with_gpt5(body_text, version_hint, api_key)

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
