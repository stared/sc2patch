"""Inspect entity grouping issues in specific patches."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


def inspect_patch(patch_version: str) -> None:
    """Inspect a specific patch for entity grouping."""
    patches_dir = Path("data/processed/patches")
    patch_file = patches_dir / f"{patch_version}.json"

    if not patch_file.exists():
        console.print(f"[red]✗ Patch {patch_version} not found[/red]")
        return

    with open(patch_file) as f:
        data = json.load(f)

    console.print(f"\n[bold cyan]{'='*100}[/bold cyan]")
    console.print(f"[bold cyan]Patch {patch_version}[/bold cyan]")
    console.print(f"[bold cyan]{'='*100}[/bold cyan]\n")

    # Group changes by entity
    by_entity = defaultdict(list)
    for change in data["changes"]:
        by_entity[change["entity_id"]].append(change)

    # Display entities and their changes
    table = Table(show_header=True, header_style="bold")
    table.add_column("Entity ID", style="yellow", width=35)
    table.add_column("Changes", style="dim")
    table.add_column("Type", style="green")

    for entity_id in sorted(by_entity.keys()):
        changes = by_entity[entity_id]
        change_types = ", ".join(c["change_type"] for c in changes)

        # Show first change text
        first_text = changes[0]["raw_text"][:80] + "..." if len(changes[0]["raw_text"]) > 80 else changes[0]["raw_text"]

        table.add_row(
            entity_id,
            f"({len(changes)}) {first_text}",
            change_types
        )

        # Show additional changes if multiple
        if len(changes) > 1:
            for change in changes[1:]:
                text = change["raw_text"][:80] + "..." if len(change["raw_text"]) > 80 else change["raw_text"]
                table.add_row("", f"     {text}", "")

    console.print(table)


def main():
    """Inspect specific patches mentioned by user."""
    patches_to_inspect = [
        "2.1.9 BU",
        "1.4.2",
        "2.0.9 BU",
        "2.1 BU",
        "4.8.2",
        "2.1.3 BU",
        "4.0.2 BU"
    ]

    for patch_version in patches_to_inspect:
        inspect_patch(patch_version)


if __name__ == "__main__":
    main()
