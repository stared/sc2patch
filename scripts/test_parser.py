"""Quick test of the parser on a single patch."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sc2patches.parse import parse_patch_html
from rich.console import Console

console = Console()

if __name__ == "__main__":
    # Test on 5.0.15 (simplest format)
    html_path = Path("data/raw_html/starcraft-ii-5-0-15.html")
    md_path = Path("data/raw_patches/5.0.15.md")

    console.print(f"[bold]Testing parser on {md_path.name}...[/bold]\n")

    try:
        metadata, changes = parse_patch_html(html_path, md_path)

        console.print(f"[green]✓[/green] Metadata extracted:")
        console.print(f"  Version: {metadata.version}")
        console.print(f"  Date: {metadata.date}")
        console.print(f"  URL: {metadata.url}")

        console.print(f"\n[green]✓[/green] Extracted {len(changes)} changes\n")

        # Show first 10 changes
        for i, change in enumerate(changes[:10], 1):
            console.print(f"{i}. [{change.race.value}] {change.raw_text[:80]}...")

        if len(changes) > 10:
            console.print(f"... and {len(changes) - 10} more")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise
