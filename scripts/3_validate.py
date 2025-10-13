#!/usr/bin/env python3
"""Stage 3: Validate processed patches for completeness and correctness.

Usage:
    uv run python scripts/3_validate.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from sc2patches.logger import PipelineLogger

console = Console()


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_patch_file(patch_path: Path) -> tuple[bool, list[str]]:
    """Validate a single patch JSON file.

    Args:
        patch_path: Path to patch JSON file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    try:
        with open(patch_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    # Check required top-level fields
    if "metadata" not in data:
        errors.append("Missing 'metadata' field")
    if "changes" not in data:
        errors.append("Missing 'changes' field")

    if errors:
        return False, errors

    # Validate metadata
    metadata = data["metadata"]
    required_metadata = ["version", "date", "title"]
    for field in required_metadata:
        if field not in metadata:
            errors.append(f"Missing metadata.{field}")
        elif not metadata[field]:
            errors.append(f"Empty metadata.{field}")

    # Validate changes
    changes = data["changes"]
    if not isinstance(changes, list):
        errors.append("'changes' must be a list")
        return False, errors

    # Check each change
    for i, change in enumerate(changes):
        # Required fields
        required_fields = ["id", "patch_version", "entity_id", "raw_text", "change_type"]
        for field in required_fields:
            if field not in change:
                errors.append(f"Change {i}: missing '{field}'")
            elif not change.get(field):
                errors.append(f"Change {i}: empty '{field}'")

        # Validate change_type values
        if "change_type" in change:
            if change["change_type"] not in ["buff", "nerf", "mixed"]:
                errors.append(
                    f"Change {i}: invalid change_type '{change['change_type']}' "
                    f"(must be buff/nerf/mixed)"
                )

    return len(errors) == 0, errors


def main() -> None:
    """Validate all processed patches."""
    patches_dir = Path("data/processed/patches")

    # Create logger
    logger = PipelineLogger("validate")

    console.print("\n[bold]Stage 3: Validate Processed Patches[/bold]\n")

    if not patches_dir.exists():
        console.print(f"[red]Error: {patches_dir} does not exist[/red]")
        console.print("Run stage 2 (2_parse.py) first")
        sys.exit(1)

    # Get all patch files
    patch_files = sorted(patches_dir.glob("*.json"))

    if not patch_files:
        console.print(f"[yellow]No patch files found in {patches_dir}[/yellow]")
        sys.exit(1)

    console.print(f"Validating {len(patch_files)} patch files...\n")

    # Validate each file
    valid_patches = []
    invalid_patches = []

    for patch_path in patch_files:
        version = patch_path.stem
        is_valid, errors = validate_patch_file(patch_path)

        if is_valid:
            valid_patches.append(version)
            logger.log_success(version, patch_path.name)
            console.print(f"[green]  ✓ {version}[/green]")
        else:
            invalid_patches.append((version, errors))
            error_summary = "; ".join(errors[:2])  # First 2 errors
            logger.log_failure(version, "\n".join(errors))
            console.print(f"[red]  ✗ {version}:[/red] {error_summary}")

    # Statistics
    total_patches = len(patch_files)
    total_entities = 0
    total_changes = 0
    change_type_counts = {"buff": 0, "nerf": 0, "mixed": 0}

    for patch_path in patch_files:
        if patch_path.stem in valid_patches:
            with open(patch_path) as f:
                data = json.load(f)
                entities = set(c["entity_id"] for c in data["changes"])
                total_entities += len(entities)
                total_changes += len(data["changes"])
                for change in data["changes"]:
                    change_type = change.get("change_type")
                    if change_type in change_type_counts:
                        change_type_counts[change_type] += 1

    # Write log
    log_path = logger.write(
        additional_summary={
            "Total patches": total_patches,
            "Total entities": total_entities,
            "Total changes": total_changes,
            "Buffs": change_type_counts["buff"],
            "Nerfs": change_type_counts["nerf"],
            "Mixed": change_type_counts["mixed"],
        }
    )

    # Display summary table
    console.print("\n[bold]Validation Summary:[/bold]")

    table = Table()
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total patches", str(total_patches))
    table.add_row("[green]Valid patches[/green]", f"[green]{len(valid_patches)}[/green]")
    if invalid_patches:
        table.add_row("[red]Invalid patches[/red]", f"[red]{len(invalid_patches)}[/red]")
    table.add_row("Total entities", str(total_entities))
    table.add_row("Total changes", str(total_changes))
    table.add_row("  • Buffs", str(change_type_counts["buff"]))
    table.add_row("  • Nerfs", str(change_type_counts["nerf"]))
    table.add_row("  • Mixed", str(change_type_counts["mixed"]))

    console.print(table)

    # Show invalid patches details
    if invalid_patches:
        console.print("\n[bold red]Invalid Patches:[/bold red]")
        for version, errors in invalid_patches:
            console.print(f"\n[red]{version}:[/red]")
            for error in errors:
                console.print(f"  • {error}")

    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    # Exit with error if any invalid patches
    if invalid_patches:
        console.print(f"\n[red]Validation failed for {len(invalid_patches)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ All patches valid[/green]")


if __name__ == "__main__":
    main()
