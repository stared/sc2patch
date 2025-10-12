"""Generate manifest of all processed patches for visualization.

This script scans data/processed/patches/ and creates a manifest.json
that lists all available patches with their metadata.
"""

import json
from pathlib import Path

from rich.console import Console

console = Console()


def generate_manifest() -> None:
    """Generate manifest of all processed patches."""
    patches_dir = Path("data/processed/patches")
    output_path = Path("visualization/public/data/patches_manifest.json")

    if not patches_dir.exists():
        console.print(f"[red]Error:[/red] {patches_dir} does not exist")
        return

    # Collect all patches
    patches = []
    for patch_file in sorted(patches_dir.glob("*.json")):
        try:
            with open(patch_file) as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            version = metadata.get("version", patch_file.stem)
            date = metadata.get("date", "unknown")
            url = metadata.get("url", "")

            patches.append(
                {
                    "version": version,
                    "date": date,
                    "url": url,
                    "file": patch_file.name,
                    "changes_count": len(data.get("changes", [])),
                }
            )

            console.print(f"[dim]✓[/dim] {version}")

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Failed to read {patch_file.name}: {e}")
            continue

    # Sort by date
    patches.sort(key=lambda p: p["date"] if p["date"] != "unknown" else "9999-99-99")

    # Write manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"patches": patches, "total": len(patches)}, f, indent=2)

    console.print(f"\n[green]✓[/green] Generated manifest with {len(patches)} patches")
    console.print(f"[green]✓[/green] Saved to {output_path}")


if __name__ == "__main__":
    generate_manifest()
