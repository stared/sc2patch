"""Check if race field in processed data matches entity_id prefix."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


def extract_race_from_id(entity_id: str) -> str:
    """Extract race from entity_id prefix."""
    if entity_id.startswith("terran-"):
        return "terran"
    elif entity_id.startswith("protoss-"):
        return "protoss"
    elif entity_id.startswith("zerg-"):
        return "zerg"
    elif entity_id.startswith("neutral-"):
        return "neutral"
    else:
        return "unknown"


def main():
    """Check for race field mismatches."""
    patches_dir = Path("data/processed/patches")

    mismatches = []
    all_race_fields = defaultdict(lambda: {"id_race": None, "field_race": set(), "examples": []})

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        for change in data["changes"]:
            entity_id = change["entity_id"]
            id_race = extract_race_from_id(entity_id)

            # Check if there's a race field
            field_race = change.get("race", None)

            all_race_fields[entity_id]["id_race"] = id_race
            if field_race:
                all_race_fields[entity_id]["field_race"].add(field_race)

            all_race_fields[entity_id]["examples"].append({
                "patch": data["metadata"]["version"],
                "raw_text": change["raw_text"][:80],
                "field_race": field_race
            })

            # Check for mismatch
            if field_race and field_race != id_race:
                mismatches.append({
                    "entity_id": entity_id,
                    "id_race": id_race,
                    "field_race": field_race,
                    "patch": data["metadata"]["version"],
                    "raw_text": change["raw_text"][:100]
                })

    # Display results
    console.print("\n[bold]Race Field Consistency Check[/bold]\n")

    if mismatches:
        console.print(f"[red]Found {len(mismatches)} mismatches![/red]\n")

        table = Table(show_header=True, header_style="bold red")
        table.add_column("Entity ID", style="yellow")
        table.add_column("ID Race", style="cyan")
        table.add_column("Field Race", style="magenta")
        table.add_column("Patch", style="dim")
        table.add_column("Text Sample", style="dim")

        for m in mismatches[:20]:  # Show first 20
            table.add_row(
                m["entity_id"],
                m["id_race"],
                m["field_race"],
                m["patch"],
                m["raw_text"]
            )

        console.print(table)
    else:
        console.print("[green]No race field mismatches found![/green]")

    # Check if race field even exists
    console.print("\n[bold]Checking if 'race' field exists in changes...[/bold]\n")

    # Sample a few entities
    sample_entities = list(all_race_fields.items())[:10]

    for entity_id, info in sample_entities:
        has_race_field = len(info["field_race"]) > 0
        status = "[green]✓[/green]" if has_race_field else "[red]✗[/red]"

        console.print(f"{status} {entity_id}")
        console.print(f"    ID race: {info['id_race']}")
        console.print(f"    Field race: {info['field_race'] if has_race_field else '(no race field)'}")

        if info['examples']:
            ex = info['examples'][0]
            console.print(f"    Example: [{ex['patch']}] race={ex['field_race']} - {ex['raw_text']}...")
        console.print()


if __name__ == "__main__":
    main()
