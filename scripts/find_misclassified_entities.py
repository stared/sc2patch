"""Find entities that might be misclassified (e.g., race-specific entities marked as neutral)."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


def main():
    """Search for potentially misclassified entities."""
    patches_dir = Path("data/processed/patches")

    # Search for specific entities mentioned by user
    search_terms = [
        "archon", "shield", "orbital", "command", "medivac", "marine",
        "zealot", "stalker", "roach", "hydralisk"
    ]

    # Collect all entities
    all_entities = defaultdict(lambda: {"occurrences": [], "races": set()})

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        for change in data["changes"]:
            entity_id = change["entity_id"]

            # Determine race from entity_id
            if entity_id.startswith("terran-"):
                race = "terran"
            elif entity_id.startswith("protoss-"):
                race = "protoss"
            elif entity_id.startswith("zerg-"):
                race = "zerg"
            elif entity_id.startswith("neutral-"):
                race = "neutral"
            else:
                race = "unknown"

            all_entities[entity_id]["races"].add(race)
            all_entities[entity_id]["occurrences"].append({
                "patch": data["metadata"]["version"],
                "raw_text": change["raw_text"][:100],
                "change_type": change["change_type"]
            })

    # Find matching entities
    console.print("\n[bold]Searching for potentially misclassified entities...[/bold]\n")

    for search_term in search_terms:
        matches = [
            (entity_id, info)
            for entity_id, info in all_entities.items()
            if search_term in entity_id.lower()
        ]

        if matches:
            console.print(f"\n[cyan]Search: '{search_term}'[/cyan]")
            console.print("=" * 100)

            for entity_id, info in matches:
                race = list(info["races"])[0]
                color = {
                    "terran": "blue",
                    "protoss": "yellow",
                    "zerg": "magenta",
                    "neutral": "white"
                }.get(race, "red")

                console.print(f"\n  [{color}]{entity_id}[/{color}] (classified as: {race})")
                console.print(f"  Appears in {len(info['occurrences'])} patch(es)")

                # Show first occurrence
                if info['occurrences']:
                    occ = info['occurrences'][0]
                    console.print(f"    Example: [{occ['patch']}] {occ['raw_text']}...")


if __name__ == "__main__":
    main()
