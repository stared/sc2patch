#!/usr/bin/env python3
"""Stage 3: Validate processed patches for completeness and correctness.

Usage:
    uv run python scripts/3_validate.py
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from sc2patches.logger import PipelineLogger

console = Console()

VALID_CHANGE_TYPES = {"buff", "nerf", "mixed"}
REQUIRED_METADATA_FIELDS = ["version", "date", "url"]
REQUIRED_CHANGE_FIELDS = ["entity_id", "raw_text", "change_type"]


@dataclass
class ValidationStats:
    """Statistics collected during validation."""

    total_patches: int = 0
    total_entities: int = 0
    total_changes: int = 0
    change_type_counts: dict[str, int] = field(default_factory=lambda: {"buff": 0, "nerf": 0, "mixed": 0})


def validate_metadata(metadata: dict, errors: list[str]) -> None:
    """Validate metadata fields, appending errors to list."""
    for fld in REQUIRED_METADATA_FIELDS:
        if fld not in metadata:
            errors.append(f"Missing metadata.{fld}")
        elif not metadata[fld]:
            errors.append(f"Empty metadata.{fld}")


def validate_change(i: int, change: dict, errors: list[str]) -> None:
    """Validate a single change, appending errors to list."""
    for fld in REQUIRED_CHANGE_FIELDS:
        if fld not in change:
            errors.append(f"Change {i}: missing '{fld}'")
        elif not change.get(fld):
            errors.append(f"Change {i}: empty '{fld}'")

    if "change_type" in change and change["change_type"] not in VALID_CHANGE_TYPES:
        errors.append(f"Change {i}: invalid change_type '{change['change_type']}' (must be buff/nerf/mixed)")


def validate_patch_file(patch_path: Path) -> tuple[bool, list[str]]:
    """Validate a single patch JSON file.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors: list[str] = []

    try:
        with patch_path.open() as f:
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

    validate_metadata(data["metadata"], errors)

    changes = data["changes"]
    if not isinstance(changes, list):
        errors.append("'changes' must be a list")
        return False, errors

    for i, change in enumerate(changes):
        validate_change(i, change, errors)

    return len(errors) == 0, errors


def collect_statistics(patch_files: list[Path], valid_patches: list[str]) -> ValidationStats:
    """Collect statistics from valid patches."""
    stats = ValidationStats(total_patches=len(patch_files))

    for patch_path in patch_files:
        if patch_path.stem not in valid_patches:
            continue
        with patch_path.open() as f:
            data = json.load(f)
        stats.total_entities += len({c["entity_id"] for c in data["changes"]})
        stats.total_changes += len(data["changes"])
        for change in data["changes"]:
            change_type = change.get("change_type")
            if change_type in stats.change_type_counts:
                stats.change_type_counts[change_type] += 1

    return stats


def display_summary(stats: ValidationStats, valid_patches: list[str], invalid_patches: list[tuple[str, list[str]]]) -> None:
    """Display validation summary table."""
    console.print("\n[bold]Validation Summary:[/bold]")

    table = Table()
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total patches", str(stats.total_patches))
    table.add_row("[green]Valid patches[/green]", f"[green]{len(valid_patches)}[/green]")
    if invalid_patches:
        table.add_row("[red]Invalid patches[/red]", f"[red]{len(invalid_patches)}[/red]")
    table.add_row("Total entities", str(stats.total_entities))
    table.add_row("Total changes", str(stats.total_changes))
    table.add_row("  • Buffs", str(stats.change_type_counts["buff"]))
    table.add_row("  • Nerfs", str(stats.change_type_counts["nerf"]))
    table.add_row("  • Mixed", str(stats.change_type_counts["mixed"]))

    console.print(table)


def display_invalid_patches(invalid_patches: list[tuple[str, list[str]]]) -> None:
    """Display details of invalid patches."""
    if not invalid_patches:
        return
    console.print("\n[bold red]Invalid Patches:[/bold red]")
    for version, errors in invalid_patches:
        console.print(f"\n[red]{version}:[/red]")
        for error in errors:
            console.print(f"  • {error}")


def main() -> None:
    """Validate all processed patches."""
    patches_dir = Path("data/processed/patches")
    logger = PipelineLogger("validate")

    console.print("\n[bold]Stage 3: Validate Processed Patches[/bold]\n")

    if not patches_dir.exists():
        console.print(f"[red]Error: {patches_dir} does not exist[/red]")
        console.print("Run stage 2 (2_parse.py) first")
        sys.exit(1)

    patch_files = sorted(patches_dir.glob("*.json"))
    if not patch_files:
        console.print(f"[yellow]No patch files found in {patches_dir}[/yellow]")
        sys.exit(1)

    console.print(f"Validating {len(patch_files)} patch files...\n")

    valid_patches: list[str] = []
    invalid_patches: list[tuple[str, list[str]]] = []

    for patch_path in patch_files:
        version = patch_path.stem
        is_valid, errors = validate_patch_file(patch_path)

        if is_valid:
            valid_patches.append(version)
            logger.log_success(version, patch_path.name)
            console.print(f"[green]  ✓ {version}[/green]")
        else:
            invalid_patches.append((version, errors))
            logger.log_failure(version, "\n".join(errors))
            console.print(f"[red]  ✗ {version}:[/red] {'; '.join(errors[:2])}")

    stats = collect_statistics(patch_files, valid_patches)

    log_path = logger.write(
        additional_summary={
            "Total patches": stats.total_patches,
            "Total entities": stats.total_entities,
            "Total changes": stats.total_changes,
            "Buffs": stats.change_type_counts["buff"],
            "Nerfs": stats.change_type_counts["nerf"],
            "Mixed": stats.change_type_counts["mixed"],
        }
    )

    display_summary(stats, valid_patches, invalid_patches)
    display_invalid_patches(invalid_patches)

    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    if invalid_patches:
        console.print(f"\n[red]Validation failed for {len(invalid_patches)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ All patches valid[/green]")


if __name__ == "__main__":
    main()
