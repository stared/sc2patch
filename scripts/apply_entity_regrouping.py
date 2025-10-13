"""Apply entity regrouping rules to all patch files."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.progress import Progress

console = Console()


def load_regrouping_rules() -> dict[str, str]:
    """Load regrouping rules from JSON file."""
    rules_file = Path("data/entity_regrouping_rules.json")
    with open(rules_file) as f:
        return json.load(f)


def apply_regrouping_to_patch(patch_data: dict, rules: dict[str, str]) -> dict:
    """Apply regrouping rules to a single patch."""
    regrouped_changes = []
    stats = {
        "total_changes": len(patch_data["changes"]),
        "regrouped": 0,
        "by_parent": defaultdict(int)
    }

    for change in patch_data["changes"]:
        entity_id = change["entity_id"]

        # Check if this entity should be regrouped
        if entity_id in rules:
            parent_id = rules[entity_id]
            stats["regrouped"] += 1
            stats["by_parent"][parent_id] += 1

            # Create new change with parent entity_id
            regrouped_change = change.copy()
            regrouped_change["entity_id"] = parent_id

            # Keep original entity_id in raw_text for clarity
            if not change["raw_text"].startswith(f"[{entity_id.split('-')[1].replace('_', ' ').title()}]"):
                # Add context about what part this is
                context = entity_id.split('-')[1].replace('_', ' ').title()
                regrouped_change["raw_text"] = f"[{context}] {change['raw_text']}"

            regrouped_changes.append(regrouped_change)
        else:
            # Keep as-is
            regrouped_changes.append(change)

    # Update patch data
    patch_data["changes"] = regrouped_changes

    return patch_data, stats


def main():
    """Apply regrouping rules to all patches."""
    patches_dir = Path("data/processed/patches")
    rules = load_regrouping_rules()

    console.print(f"[bold]Applying {len(rules)} regrouping rules to all patches...[/bold]\n")

    total_regrouped = 0
    affected_patches = []
    all_stats = defaultdict(int)

    with Progress() as progress:
        patch_files = sorted(patches_dir.glob("*.json"))
        task = progress.add_task("Processing patches...", total=len(patch_files))

        for patch_file in patch_files:
            # Load patch
            with open(patch_file) as f:
                patch_data = json.load(f)

            # Apply regrouping
            regrouped_data, stats = apply_regrouping_to_patch(patch_data, rules)

            if stats["regrouped"] > 0:
                # Save modified patch
                with open(patch_file, "w") as f:
                    json.dump(regrouped_data, f, indent=2)

                affected_patches.append({
                    "version": patch_data["metadata"]["version"],
                    "regrouped": stats["regrouped"],
                    "by_parent": dict(stats["by_parent"])
                })

                total_regrouped += stats["regrouped"]

                # Aggregate stats
                for parent, count in stats["by_parent"].items():
                    all_stats[parent] += count

            progress.update(task, advance=1)

    # Display results
    console.print(f"\n[bold green]✓ Regrouping complete![/bold green]\n")
    console.print(f"[bold]Patches affected:[/bold] {len(affected_patches)}")
    console.print(f"[bold]Total changes regrouped:[/bold] {total_regrouped}\n")

    if affected_patches:
        console.print("[cyan]Affected patches:[/cyan]")
        for patch in affected_patches:
            console.print(f"\n  [yellow]{patch['version']}[/yellow] - {patch['regrouped']} changes regrouped")
            for parent, count in sorted(patch['by_parent'].items()):
                parent_name = parent.split('-')[1].replace('_', ' ').title()
                console.print(f"    → {count} to {parent_name}")

    console.print(f"\n[cyan]Changes by parent entity:[/cyan]")
    for parent, count in sorted(all_stats.items(), key=lambda x: -x[1]):
        parent_name = parent.split('-')[1].replace('_', ' ').title()
        console.print(f"  {parent_name}: {count} changes")


if __name__ == "__main__":
    main()
