"""Parse balance patches directly from HTML using GPT-5.

This script:
1. Reads HTML files from data/raw_html/
2. Strips HEAD section to save tokens
3. Extracts article body content
4. Sends to GPT-5 for structured extraction
5. Saves to data/processed/patches/{version}.json
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import track

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

load_dotenv()

console = Console()

MODEL = "openai/gpt-5"

# Complete URL mapping for all balance patches
PATCH_URLS = {
    # Wings of Liberty (1.x)
    "1.1.0": "https://news.blizzard.com/en-gb/starcraft2/9993888/patch-1-1-0-now-live",
    "1.1.2": "https://news.blizzard.com/en-gb/starcraft2/9990145",
    "1.1.3": "http://us.battle.net/sc2/en/blog/1113827/patch-113-now-live-11-9-2010",
    "1.2.0": "https://news.blizzard.com/en-gb/starcraft2/9995561",
    "1.3.0": "https://news.blizzard.com/en-us/starcraft2/2514162",
    "1.3.3": "https://news.blizzard.com/en-gb/starcraft2/9982849",
    "1.4.0": "https://news.blizzard.com/en-us/starcraft2/3549513/patch-1-4-0-now-live",
    "1.4.2": "https://news.blizzard.com/en-gb/starcraft2/10002543/patch-1-4-2-now-live",
    "1.4.3": "https://news.blizzard.com/en-gb/starcraft2/9995857/patch-1-4-3-now-live",
    "1.4.3 BU": "http://eu.battle.net/sc2/en/blog/4380324/Balance_Update_-_110512-10_05_2012",
    # Heart of the Swarm (2.x)
    "2.0.8 BU": "https://news.blizzard.com/en-us/starcraft2/9693907",
    "2.0.9": "http://us.battle.net/sc2/en/blog/10278173",
    "2.0.9 BU": "https://news.blizzard.com/en-us/starcraft2/10393911",
    "2.0.11 BU": "https://news.blizzard.com/en-us/starcraft2/10782713",
    "2.0.12": "https://news.blizzard.com/en-us/starcraft2/11523757",
    "2.1 BU": "https://news.blizzard.com/en-us/starcraft2/12802185",
    "2.1 BU2": "https://news.blizzard.com/en-us/starcraft2/13108934",
    "2.1.2 BU": "https://news.blizzard.com/en-us/starcraft2/14216442",
    "2.1.3 BU": "https://news.blizzard.com/en-us/starcraft2/14933073",
    "2.1.9 BU": "https://news.blizzard.com/en-us/starcraft2/18598811",
    # Legacy of the Void (3.x)
    "3.8.0": "https://news.blizzard.com/en-us/starcraft2/20372512/starcraft-ii-legacy-of-the-void-3-8-0-patch-notes",
    "3.8.0 BU": "https://news.blizzard.com/en-gb/starcraft2/20399161/legacy-of-the-void-balance-update-december-8-2016",
    "3.11.0 BU": "https://news.blizzard.com/en-us/article/20562669/legacy-of-the-void-balance-update-march-7-2017",
    "3.12.0 BU": "https://news.blizzard.com/en-gb/starcraft2/20720843/legacy-of-the-void-balance-update-april-2017",
    "3.14.0": "https://news.blizzard.com/en-us/article/20799759/starcraft-ii-legacy-of-the-void-3-14-0-patch-notes",
    # Legacy of the Void (4.x)
    "4.0.0": "https://news.blizzard.com/en-us/starcraft2/21183638/starcraft-ii-4-0-patch-notes",
    "4.0.2 BU": "https://news.blizzard.com/en-us/starcraft2/21272911/starcraft-ii-balance-update-november-28-2017",
    "4.1.1 BU": "https://news.blizzard.com/en-us/starcraft2/21349570",
    "4.1.4 BU": "https://news.blizzard.com/en-gb/starcraft2/21494433/starcraft-ii-balance-update-january-29-2018",
    "4.2.1 BU": "https://news.blizzard.com/en-us/starcraft2/21637913",
    "4.11.3": "https://news.blizzard.com/en-us/article/23230078/starcraft-ii-4-11-3-patch-notes",
    "4.11.4 BU": "https://news.blizzard.com/en-us/starcraft2/23312740/starcraft-ii-4-11-4-patch-notes",
    # Legacy of the Void (5.x)
    "5.0.2 BU": "https://news.blizzard.com/en-gb/starcraft2/23495670/starcraft-ii-5-0-2-patch-notes",
    "5.0.9": "https://news.blizzard.com/en-us/article/23774006/starcraft-ii-5-0-9-ptr-patch-notes",
    "5.0.12": "https://news.blizzard.com/en-us/starcraft2/24009150/starcraft-ii-5-0-12-patch-notes",
    "5.0.13": "https://news.blizzard.com/en-us/article/24078322/starcraft-ii-5-0-13-patch-notes",
    "5.0.14": "https://news.blizzard.com/en-us/article/24162754/starcraft-ii-5-0-14-patch-notes",
    "5.0.15": "https://news.blizzard.com/en-us/article/24225313/starcraft-ii-5-0-15-patch-notes",
}

# Reverse mapping: URL path to version
URL_TO_VERSION = {}
for version, url in PATCH_URLS.items():
    # Extract path component
    path = url.split("/")[-1]
    URL_TO_VERSION[path] = version


class BalanceChange(BaseModel):
    """A single balance change for an entity."""

    entity_id: str = Field(description="Entity ID in format: race-unit_name (e.g., 'terran-marine', 'protoss-stalker')")
    entity_name: str = Field(description="Display name of the entity (e.g., 'Marine', 'Stalker')")
    race: str = Field(description="Race: 'terran', 'protoss', 'zerg', or 'neutral'")
    changes: List[str] = Field(description="List of specific changes to this entity")


class PatchChanges(BaseModel):
    """All balance changes in a patch."""

    version: str = Field(description="Patch version (e.g., '4.0', '3.8.0')")
    date: str | None = Field(default=None, description="Patch date in ISO format YYYY-MM-DD (if available)")
    changes: List[BalanceChange] = Field(description="List of all balance changes grouped by entity")


def extract_body_from_html(html_path: Path) -> tuple[str, str | None]:
    """Extract article body from HTML, removing HEAD and navigation.

    Returns:
        tuple[str, str | None]: (body_text, patch_version)
    """
    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Try to determine version from filename
    filename = html_path.stem
    version = URL_TO_VERSION.get(filename)

    # Extract article body - try multiple selectors
    body = None

    # Modern Blizzard pages
    if article := soup.find("section", class_="blog"):
        body = article
    elif article := soup.find("article", class_="Content"):
        body = article
    # Old battle.net pages
    elif article := soup.find("div", id="content"):
        body = article
    elif article := soup.find("div", class_="article-content"):
        body = article

    if not body:
        # Fallback: get everything after </head>
        if soup.body:
            body = soup.body
        else:
            raise ValueError(f"Could not find article body in {html_path}")

    # Get text content
    body_text = body.get_text(separator="\n", strip=True)

    return body_text, version


def extract_changes_with_llm(body_text: str, version: str | None) -> PatchChanges:
    """Extract balance changes using GPT-5."""

    system_prompt = """You are a StarCraft II balance patch expert. Extract balance changes from patch notes.

For each changed entity (unit, building, upgrade, ability):
1. Create entity_id in format: race-entity_name (e.g., "terran-marine", "protoss-stalker")
2. Use lowercase with underscores for entity_id
3. Extract all specific changes as separate list items
4. Focus ONLY on balance changes (damage, cost, build time, etc.)
5. Ignore bug fixes, UI changes, and editor changes

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
        "Health increased from 45 to 55",
        "Attack damage reduced from 6 to 5"
      ]
    },
    {
      "entity_id": "protoss-stalker",
      "entity_name": "Stalker",
      "race": "protoss",
      "changes": [
        "Cost changed from 125/50 to 100/50"
      ]
    }
  ]
}

CRITICAL: ALL fields (entity_id, entity_name, race, changes) are REQUIRED for each entity."""

    user_prompt = f"""Extract all balance changes from this StarCraft II patch:

{body_text}

Version hint: {version if version else "Unknown - extract from content"}

Return ONLY valid JSON matching the example format. Include ALL required fields."""

    api_key = os.getenv("OPENROUTER_API_KEY")

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
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

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    try:
        parsed_data = json.loads(content)
        return PatchChanges(**parsed_data)
    except Exception as e:
        # Log the problematic content for debugging
        console.print(f"[red]Failed to parse GPT-5 response:[/red]")
        console.print(f"[dim]{content[:500]}...[/dim]")
        raise e


def main():
    """Parse all HTML files with GPT-5."""
    html_dir = Path("data/raw_html")
    output_dir = Path("data/processed/patches")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all HTML files
    html_files = sorted(html_dir.glob("*.html"))

    console.print(f"\n[bold]Parsing {len(html_files)} HTML files with GPT-5...[/bold]\n")

    successful = 0
    failed = []
    skipped = []

    for html_path in track(html_files, description="Processing patches..."):
        try:
            # Extract body and version
            body_text, version = extract_body_from_html(html_path)

            if not version:
                console.print(f"[yellow]⊘ {html_path.name}:[/yellow] No version mapping (skipped)")
                skipped.append(html_path.name)
                continue

            # Check if already processed
            output_path = output_dir / f"{version}.json"
            if output_path.exists():
                console.print(f"[dim]↷ {version}:[/dim] Already processed")
                successful += 1
                continue

            # Parse with GPT-5
            console.print(f"[cyan]→ {version}:[/cyan] Parsing with GPT-5...")
            patch_data = extract_changes_with_llm(body_text, version)

            # Convert to JSON format matching existing structure
            output_data = {
                "metadata": {
                    "version": patch_data.version,
                    "date": patch_data.date or "unknown",
                    "title": f"StarCraft II Patch {patch_data.version}",
                    "url": PATCH_URLS.get(version, ""),
                },
                "changes": []
            }

            # Flatten changes
            for entity in patch_data.changes:
                for i, change_text in enumerate(entity.changes):
                    change_id = f"{entity.entity_id}_{len(output_data['changes'])}"
                    output_data["changes"].append({
                        "id": change_id,
                        "patch_version": patch_data.version,
                        "entity_id": entity.entity_id,
                        "raw_text": change_text,
                    })

            # Save
            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)

            entities_count = len(patch_data.changes)
            changes_count = len(output_data["changes"])
            console.print(
                f"  [green]✓[/green] {version}: {entities_count} entities, "
                f"{changes_count} changes"
            )

            successful += 1

            # Be polite to API
            time.sleep(2.0)

        except Exception as e:
            console.print(f"  [red]✗ Failed:[/red] {e}")
            failed.append((html_path.name, str(e)))

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully processed: {successful}/{len(html_files)}[/green]")

    if skipped:
        console.print(f"\n[yellow]Skipped (no version): {len(skipped)}[/yellow]")
        for name in skipped:
            console.print(f"  {name}")

    if failed:
        console.print(f"\n[red]Failed: {len(failed)}[/red]")
        for name, error in failed:
            console.print(f"  {name}: {error}")


if __name__ == "__main__":
    main()
