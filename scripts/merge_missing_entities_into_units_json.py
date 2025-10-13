"""Merge missing entities into units.json."""

import json
from pathlib import Path

from rich.console import Console

console = Console()


def main():
    """Merge missing entities into units.json."""
    missing_file = Path("data/missing_entities.json")
    units_file = Path("visualization/public/data/units.json")

    # Load data
    with open(missing_file) as f:
        missing_entities = json.load(f)

    with open(units_file) as f:
        existing_units = json.load(f)

    console.print(f"[bold]Loaded {len(existing_units)} existing entities[/bold]")
    console.print(f"[bold]Merging {len(missing_entities)} missing entities[/bold]\n")

    # Convert missing entities to units format
    new_units = []
    for entity in missing_entities:
        new_unit = {
            "id": entity["id"],
            "name": entity["name"],
            "race": entity["race"],
            "type": entity["type"]
        }
        new_units.append(new_unit)

        console.print(
            f"  [green]+[/green] {entity['id']:45} "
            f"[{entity['race']}] "
            f"[dim]{entity['type']}[/dim]"
        )

    # Merge
    all_units = existing_units + new_units

    # Sort by race, then by type, then by name
    race_order = {"terran": 0, "protoss": 1, "zerg": 2, "neutral": 3, "unknown": 4}
    type_order = {"unit": 0, "building": 1, "upgrade": 2, "unknown": 3}

    all_units.sort(key=lambda u: (
        race_order.get(u["race"], 99),
        type_order.get(u["type"], 99),
        u["name"]
    ))

    # Save
    with open(units_file, "w") as f:
        json.dump(all_units, f, indent=2)

    console.print(f"\n[bold green]✓ Saved {len(all_units)} entities to {units_file}[/bold green]")
    console.print(f"  Previous: {len(existing_units)}")
    console.print(f"  Added: {len(new_units)}")
    console.print(f"  Total: {len(all_units)}")


if __name__ == "__main__":
    main()
