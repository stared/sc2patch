#!/usr/bin/env python3
"""Download unit and building images from Liquipedia using tech tree data."""

import json
import time
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


def download_image(url: str, output_path: Path) -> bool:
    """Download an image from URL to the specified path."""
    try:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True

    except Exception as e:
        console.print(f"[red]Error downloading {url}: {e}[/red]")
        return False


def main(test_mode: bool = False, test_limit: int = 10) -> None:
    """Main execution."""
    tech_tree_file = Path("data/tech_tree.json")
    output_dir = Path("visualization/public/assets/units")

    console.print(f"[cyan]Reading tech tree from {tech_tree_file}[/cyan]")
    tech_tree = json.loads(tech_tree_file.read_text())

    # Filter entities with icon URLs
    entities_with_icons = [e for e in tech_tree if e.get("icon_url")]
    entities_without_icons = [e for e in tech_tree if not e.get("icon_url")]

    console.print(f"[green]Total entities: {len(tech_tree)}[/green]")
    console.print(f"[green]Entities with icons: {len(entities_with_icons)}[/green]")
    console.print(f"[yellow]Entities without icons: {len(entities_without_icons)}[/yellow]")

    if entities_without_icons:
        console.print(f"\n[yellow]Entities without icon URLs:[/yellow]")
        for entity in entities_without_icons[:5]:
            console.print(f"  - {entity['entity_id']} ({entity['name']})")
        if len(entities_without_icons) > 5:
            console.print(f"  ... and {len(entities_without_icons) - 5} more")

    # Test mode: only download a few
    if test_mode:
        console.print(f"\n[yellow]TEST MODE: Only downloading {test_limit} entities[/yellow]")
        entities_to_download = entities_with_icons[:test_limit]
    else:
        entities_to_download = entities_with_icons

    console.print(f"\n[cyan]Downloading {len(entities_to_download)} images...[/cyan]\n")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading images...", total=len(entities_to_download))

        for entity in entities_to_download:
            entity_id = entity["entity_id"]
            entity_name = entity["name"]
            entity_type = entity["type"]
            icon_url = entity["icon_url"]

            # Upgrade resolution: 25px → 50px
            if "25px-" in icon_url:
                icon_url = icon_url.replace("25px-", "50px-")

            output_path = output_dir / f"{entity_id}.png"

            # Skip if already exists and is reasonable size
            if output_path.exists():
                file_size = output_path.stat().st_size
                # Skip if file exists and is between 500 bytes and 10KB (reasonable for 50x50 PNG)
                if 500 < file_size < 10000:
                    skipped_count += 1
                    progress.update(task, advance=1)
                    continue

            progress.update(
                task, description=f"Downloading {entity_type}: {entity_name} ({entity_id})"
            )

            if download_image(icon_url, output_path):
                success_count += 1
            else:
                failed_count += 1

            progress.update(task, advance=1)

            # Be nice to Liquipedia servers
            time.sleep(0.1)

    console.print(f"\n[green]✓ Download complete![/green]")
    console.print(f"  Success: {success_count}")
    console.print(f"  Failed: {failed_count}")
    console.print(f"  Skipped (already exist): {skipped_count}")
    console.print(f"  Output directory: {output_dir}")


if __name__ == "__main__":
    import sys

    # Check for --test flag
    test_mode = "--test" in sys.argv
    main(test_mode=test_mode)
