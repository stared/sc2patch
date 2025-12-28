#!/usr/bin/env python3
"""Stage 4: Export processed data for visualization.

Generates a single patches.json file with all data.

Usage:
    uv run python scripts/4_export_for_viz.py
"""

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console

from sc2patches.logger import PipelineLogger
from sc2patches.models import Change, EntityChanges, Patch, PatchesData, Unit

console = Console()

# Valid version must start with 1-5 (WoL=1.x, HotS=2.x, LotV=3.x, F2P=4.x, 10th=5.x)
VALID_VERSION_PATTERN = r"^[1-5]\."


def is_valid_version(version: str) -> bool:
    """Check if version starts with valid era prefix (1-5)."""
    import re
    return bool(re.match(VALID_VERSION_PATTERN, version))


def load_units(units_file: Path) -> list[Unit]:
    """Load units from JSON file."""
    if not units_file.exists():
        return []
    with units_file.open() as f:
        data = json.load(f)
    return [Unit(**u) for u in data]


def load_patch(patch_file: Path, logger: PipelineLogger) -> Patch | None:
    """Load and convert a patch file to the new format."""
    try:
        with patch_file.open() as f:
            data = json.load(f)

        metadata = data["metadata"]
        version = metadata["version"]

        # Validate version format
        if not is_valid_version(version):
            console.print(f"[yellow]Skipping {patch_file.name}: invalid version '{version}'[/yellow]")
            logger.log_skip(version, f"invalid version format (must start with 1-5)")
            return None

        changes = data["changes"]

        # Group changes by entity_id
        entity_changes: dict[str, list[Change]] = defaultdict(list)
        for c in changes:
            entity_changes[c["entity_id"]].append(
                Change(raw_text=c["raw_text"], change_type=c["change_type"])
            )

        # Convert to EntityChanges
        entities = [
            EntityChanges(entity_id=eid, changes=changes)
            for eid, changes in sorted(entity_changes.items())
        ]

        return Patch(
            version=metadata["version"],
            date=metadata["date"],
            url=metadata.get("url", ""),
            entities=entities,
        )
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load {patch_file.name}: {e}[/yellow]")
        return None


def main() -> None:
    """Export processed data to visualization directory."""
    # Setup paths
    source_patches_dir = Path("data/processed/patches")
    source_units_file = Path("data/units.json")

    dest_dir = Path("visualization/public/data")
    dest_file = dest_dir / "patches.json"

    # Create logger
    logger = PipelineLogger("export")

    console.print("\n[bold]Stage 4: Export for Visualization[/bold]\n")

    # Validate source directory exists
    if not source_patches_dir.exists():
        console.print(f"[red]Error: {source_patches_dir} does not exist[/red]")
        console.print("Run stage 2 (2_parse.py) first")
        sys.exit(1)

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clean old data
    old_patches_dir = dest_dir / "processed" / "patches"
    if old_patches_dir.exists():
        shutil.rmtree(old_patches_dir)
        console.print("[dim]Removed old processed/patches/ directory[/dim]")

    old_manifest = dest_dir / "patches_manifest.json"
    if old_manifest.exists():
        old_manifest.unlink()
        console.print("[dim]Removed old patches_manifest.json[/dim]")

    # Load units
    units = load_units(source_units_file)
    console.print(f"Loaded {len(units)} units")

    # Load all patches
    patch_files = sorted(source_patches_dir.glob("*.json"))
    console.print(f"Loading {len(patch_files)} patch files...")

    patches: list[Patch] = []
    for patch_file in patch_files:
        patch = load_patch(patch_file, logger)
        if patch:
            patches.append(patch)
            logger.log_success(patch.version, f"{len(patch.entities)} entities")

    # Sort by date
    patches.sort(key=lambda p: p.date)

    # Check for "unknown" entities and warn
    unknown_entries = []
    for patch in patches:
        for entity in patch.entities:
            if entity.entity_id == "unknown":
                for change in entity.changes:
                    unknown_entries.append((patch.version, change.raw_text))

    if unknown_entries:
        console.print(f"\n[yellow]⚠ WARNING: Found {len(unknown_entries)} 'unknown' entities:[/yellow]")
        for version, text in unknown_entries:
            console.print(f"[yellow]  {version}: {text[:60]}...[/yellow]")
        console.print("[yellow]  → Add these to units.json with proper entity_ids[/yellow]\n")

    # Create combined data
    data = PatchesData.create(patches=patches, units=units)

    # Write single JSON file
    with dest_file.open("w") as f:
        f.write(data.model_dump_json(indent=2))

    # Stats
    total_changes = sum(
        len(e.changes) for p in patches for e in p.entities
    )

    console.print(f"\n[green]✓ Exported {len(patches)} patches ({total_changes} changes)[/green]")
    console.print(f"[green]✓ Saved to {dest_file}[/green]")

    # Write log
    log_path = logger.write(
        additional_summary={
            "Patches": len(patches),
            "Units": len(units),
            "Total changes": total_changes,
            "Output": str(dest_file),
        }
    )

    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")
    console.print("\n[green]✓ Export complete[/green]")


if __name__ == "__main__":
    main()
