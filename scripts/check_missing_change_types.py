"""Check which patches are missing change_type fields."""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    """Check all patches for missing change_type."""
    patches_dir = Path("data/processed/patches")

    missing = []
    complete = []

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        changes = data.get("changes", [])
        total = len(changes)

        if total == 0:
            continue

        with_type = sum(1 for c in changes if "change_type" in c)

        if with_type == 0:
            missing.append((patch_file.name, total))
        elif with_type < total:
            missing.append((patch_file.name, total, with_type))
        else:
            complete.append((patch_file.name, total))

    # Show missing
    if missing:
        table = Table(title="Patches Missing change_type", show_header=True)
        table.add_column("Patch", style="cyan")
        table.add_column("Total Changes", style="yellow")
        table.add_column("With change_type", style="green")

        for item in missing:
            if len(item) == 2:
                table.add_row(item[0], str(item[1]), "0")
            else:
                table.add_row(item[0], str(item[1]), str(item[2]))

        console.print(table)
        console.print(f"\n[red]{len(missing)} patches missing change_type[/red]")

    # Show complete
    console.print(f"\n[green]{len(complete)} patches complete[/green]")

    # Show total changes
    total_missing = sum(item[1] for item in missing)
    total_complete = sum(item[1] for item in complete)
    console.print(f"\nChanges: {total_complete} complete, {total_missing} missing")


if __name__ == "__main__":
    main()
