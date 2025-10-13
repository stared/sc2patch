#!/usr/bin/env python3
"""Stage 4: Export processed data for visualization.

Copies processed patches and units data to visualization/public/data/

Usage:
    uv run python scripts/4_export_for_viz.py
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console

from sc2patches.logger import PipelineLogger

console = Console()


def main() -> None:
    """Export processed data to visualization directory."""
    # Setup paths
    source_patches_dir = Path("data/processed/patches")
    source_units_file = Path("data/units.json")

    dest_dir = Path("visualization/public/data")
    dest_patches_dir = dest_dir / "processed" / "patches"
    dest_units_file = dest_dir / "units.json"

    # Create logger
    logger = PipelineLogger("export")

    console.print("\n[bold]Stage 4: Export for Visualization[/bold]\n")

    # Validate source directories exist
    if not source_patches_dir.exists():
        console.print(f"[red]Error: {source_patches_dir} does not exist[/red]")
        console.print("Run stage 2 (2_parse.py) first")
        sys.exit(1)

    if not source_units_file.exists():
        console.print(f"[yellow]Warning: {source_units_file} not found[/yellow]")

    # Create destination directories
    dest_patches_dir.mkdir(parents=True, exist_ok=True)

    # Copy patch files
    patch_files = sorted(source_patches_dir.glob("*.json"))
    console.print(f"Copying {len(patch_files)} patch files...")

    for patch_file in patch_files:
        dest_file = dest_patches_dir / patch_file.name
        shutil.copy2(patch_file, dest_file)
        logger.log_success(patch_file.stem, f"{patch_file.name} → {dest_file.relative_to(dest_dir)}")

    console.print(f"[green]  ✓ Copied {len(patch_files)} patches[/green]")

    # Copy units.json if it exists
    if source_units_file.exists():
        shutil.copy2(source_units_file, dest_units_file)
        logger.log_success("units.json", f"units.json → {dest_units_file.relative_to(dest_dir)}")
        console.print("[green]  ✓ Copied units.json[/green]")

    # Write log
    log_path = logger.write(
        additional_summary={
            "Patch files": len(patch_files),
            "Destination": str(dest_dir),
        }
    )

    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")
    console.print("\n[green]✓ Export complete[/green]")
    console.print(f"\nVisualization data ready in: {dest_dir}")


if __name__ == "__main__":
    main()
