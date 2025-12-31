#!/usr/bin/env python3
"""Parse Liquipedia tech tree HTML to structured JSON using GPT-5."""

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables from .env file
load_dotenv()

console = Console()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found in .env file[/red]")
    raise SystemExit(1)

TECH_TREE_PROMPT = """You are a data extraction assistant. Parse the provided Liquipedia HTML page for \
StarCraft II Legacy of the Void units and extract a complete tech tree.

Extract ALL of the following for each race (Terran, Protoss, Zerg):
1. **Buildings** - all structures
2. **Units** - all ground and air units (including workers)
3. **Upgrades** - important upgrades and researched abilities

For EACH entry, extract the following fields:

**Required fields:**
- `name`: The display name (e.g., "Marine", "Barracks")
- `entity_id`: Normalized identifier (race-name_in_lowercase, e.g., "terran-marine", "protoss-nexus")
- `race`: One of "terran", "protoss", "zerg", or "neutral"
- `type`: One of "unit", "building", or "upgrade"
- `built_from`: The entity that creates/researches this (REQUIRED for ALL entries):
  - Buildings: The worker unit (e.g., "terran-scv", "protoss-probe", "zerg-drone")
  - Units: The structure that produces them (e.g., "terran-barracks", "protoss-gateway")
  - Upgrades: The structure where researched (e.g., "terran-engineering_bay", "protoss-forge")
- `requirements`: Array of entity_ids that must exist before this can be built/trained (empty array [] if none)
  - Example: Barracks requires Supply Depot -> ["terran-supply_depot"]
  - Example: Marauder requires Tech Lab -> ["terran-tech_lab"]
  - Example: Marine has no requirements -> []

**Optional fields (use null if not found):**
- `subpage_url`: Full Liquipedia URL to detailed page
- `icon_url`: Full URL to the icon image

**Format:** Return a JSON array (list) of objects. Each object represents one entity.

**Example entries:**
```json
[
  {
    "name": "SCV",
    "entity_id": "terran-scv",
    "race": "terran",
    "type": "unit",
    "built_from": "terran-command_center",
    "requirements": [],
    "subpage_url": "https://liquipedia.net/starcraft2/SCV_(Legacy_of_the_Void)",
    "icon_url": "https://liquipedia.net/commons/images/..."
  },
  {
    "name": "Barracks",
    "entity_id": "terran-barracks",
    "race": "terran",
    "type": "building",
    "built_from": "terran-scv",
    "requirements": ["terran-supply_depot"],
    "subpage_url": "https://liquipedia.net/starcraft2/Barracks_(Legacy_of_the_Void)",
    "icon_url": "https://liquipedia.net/commons/images/..."
  },
  {
    "name": "Marine",
    "entity_id": "terran-marine",
    "race": "terran",
    "type": "unit",
    "built_from": "terran-barracks",
    "requirements": [],
    "subpage_url": "https://liquipedia.net/starcraft2/Marine_(Legacy_of_the_Void)",
    "icon_url": "https://liquipedia.net/commons/images/..."
  },
  {
    "name": "Stim Pack",
    "entity_id": "terran-stim_pack",
    "race": "terran",
    "type": "upgrade",
    "built_from": "terran-barracks_tech_lab",
    "requirements": [],
    "subpage_url": "https://liquipedia.net/starcraft2/Stim_Pack_(Legacy_of_the_Void)",
    "icon_url": null
  }
]
```

**Important:**
- Include ALL units, buildings, and major upgrades for all three races
- Use full URLs (not relative paths) for subpage_url and icon_url
- Normalize entity_id: lowercase with underscores, prefixed with race (e.g., "Siege Tank" -> "terran-siege_tank")
- `built_from` is REQUIRED for every single entry
- `requirements` is REQUIRED for every entry (use empty array [] if none)
- For tech lab/reactor addons, use entity_id like "terran-barracks_tech_lab"

Return ONLY the JSON array, no other text or markdown formatting."""


def parse_tech_tree_with_gpt5(html_content: str) -> list[dict]:
    """Parse HTML using GPT-5 via OpenRouter."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing tech tree with GPT-5...", total=None)

        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3.7-sonnet:beta",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{TECH_TREE_PROMPT}\n\nHTML:\n{html_content}",
                        }
                    ],
                },
                timeout=180.0,
            )
            response.raise_for_status()

            # Debug: print response if not JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                console.print("[red]Failed to parse JSON response[/red]")
                console.print(f"[yellow]Response status: {response.status_code}[/yellow]")
                console.print("[yellow]Response body (first 1000 chars):[/yellow]")
                console.print(response.text[:1000])
                raise
            content = result["choices"][0]["message"]["content"]

            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            tech_tree = json.loads(content)
            progress.update(task, completed=True)

            # Validate structure
            if not isinstance(tech_tree, list):
                raise ValueError("Expected tech tree to be a JSON array")

            return tech_tree

        except Exception as e:
            console.print(f"[red]Error calling GPT-5: {e}[/red]")
            raise


def verify_completeness(tech_tree: list[dict]) -> None:
    """Verify the tech tree data is complete."""
    console.print("\n[cyan]Verifying completeness...[/cyan]")

    # Count by race and type
    stats = {}
    for entry in tech_tree:
        race = entry.get("race", "unknown")
        entry_type = entry.get("type", "unknown")
        key = f"{race}_{entry_type}"
        stats[key] = stats.get(key, 0) + 1

    # Display stats
    for race in ["terran", "protoss", "zerg", "neutral"]:
        race_total = sum(v for k, v in stats.items() if k.startswith(race))
        if race_total == 0:
            continue

        console.print(f"\n[yellow]{race.capitalize()}:[/yellow] {race_total} total")
        for entry_type in ["building", "unit", "upgrade"]:
            count = stats.get(f"{race}_{entry_type}", 0)
            if count > 0:
                console.print(f"  {entry_type}s: {count}")

    # Spot check key entities
    console.print("\n[cyan]Spot checking key entities...[/cyan]")
    key_entities = [
        "terran-scv",
        "terran-marine",
        "terran-command_center",
        "protoss-probe",
        "protoss-zealot",
        "protoss-nexus",
        "zerg-drone",
        "zerg-zergling",
        "zerg-hatchery",
    ]

    entity_ids = {e.get("entity_id") for e in tech_tree}
    for entity_id in key_entities:
        found = "✓" if entity_id in entity_ids else "✗"
        console.print(f"  {found} {entity_id}")

    # Check for missing required fields
    console.print("\n[cyan]Checking required fields...[/cyan]")
    missing_fields = []
    for i, entry in enumerate(tech_tree):
        if not entry.get("built_from"):
            missing_fields.append(f"Entry {i} ({entry.get('name', 'unknown')}) missing 'built_from'")
        if "requirements" not in entry:
            missing_fields.append(f"Entry {i} ({entry.get('name', 'unknown')}) missing 'requirements'")

    if missing_fields:
        console.print("[red]Issues found:[/red]")
        for issue in missing_fields[:10]:  # Show first 10
            console.print(f"  - {issue}")
    else:
        console.print("[green]✓ All required fields present[/green]")


def main() -> None:
    """Main execution."""
    html_file = Path("data/liquipedia_units_lotv.html")
    output_json = Path("data/tech_tree.json")

    console.print(f"[cyan]Reading HTML from {html_file}[/cyan]")
    html_content = html_file.read_text()

    console.print("[cyan]Parsing with GPT-5...[/cyan]")
    tech_tree = parse_tech_tree_with_gpt5(html_content)

    # Save JSON
    console.print(f"[cyan]Saving JSON to {output_json}[/cyan]")
    output_json.write_text(json.dumps(tech_tree, indent=2))

    # Verify
    verify_completeness(tech_tree)

    console.print("\n[green]✓ Tech tree parsing complete![/green]")
    console.print(f"  Total entries: {len(tech_tree)}")
    console.print(f"  JSON: {output_json}")


if __name__ == "__main__":
    main()
