"""List ALL entities classified as neutral with full details."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console

console = Console()


def main():
    """Find and display all neutral entities."""
    patches_dir = Path("data/processed/patches")
    all_neutral = defaultdict(list)

    # Collect all neutral entities
    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        for change in data["changes"]:
            entity_id = change["entity_id"]
            if entity_id.startswith("neutral-"):
                all_neutral[entity_id].append({
                    "patch": data["metadata"]["version"],
                    "raw_text": change["raw_text"],
                    "change_type": change["change_type"]
                })

    # Display results
    console.print(f"\n[bold]Found {len(all_neutral)} unique neutral entities:[/bold]\n")
    console.print("=" * 100)

    for entity_id in sorted(all_neutral.keys()):
        console.print(f"\n[cyan]{entity_id}[/cyan]")
        console.print("-" * 100)

        for occ in all_neutral[entity_id]:
            console.print(
                f"  [[yellow]{occ['patch']}[/yellow]] "
                f"([green]{occ['change_type']}[/green]) "
                f"{occ['raw_text'][:120]}..."
            )

        console.print()


if __name__ == "__main__":
    main()
