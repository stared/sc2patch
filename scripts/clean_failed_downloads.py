"""Clean up failed downloads and empty patch data.

This script:
1. Deletes HTML files that are the SC2 homepage (not patch notes)
2. Deletes processed JSON files with zero changes
3. Reports all failures clearly
"""

import json
from pathlib import Path

from rich.console import Console

console = Console()


def is_homepage_html(html_path: Path) -> bool:
    """Check if HTML is the SC2 homepage instead of patch notes."""
    content = html_path.read_text(encoding="utf-8")

    # Homepage indicators
    homepage_indicators = [
        "The ultimate real-time strategy game",
        "REAL-TIME STRATEGY • FREE TO PLAY",
        "The Galaxy is Yours to Conquer",
        "<title>StarCraft II</title>",
    ]

    # Patch notes indicators
    patch_indicators = [
        "Patch Notes",
        "Balance Update",
        "patch notes",
        "balance changes",
    ]

    has_homepage_text = any(ind in content for ind in homepage_indicators)
    has_patch_text = any(ind in content for ind in patch_indicators)

    # If it has homepage text but no patch text, it's a homepage
    return has_homepage_text and not has_patch_text


def main() -> None:
    """Clean up failed downloads."""
    console.print("\n[bold]Cleaning up failed downloads[/bold]\n")

    # Check HTML files
    console.print("[cyan]Checking HTML files...[/cyan]")
    html_dir = Path("data/raw_html")
    deleted_html = []

    for html_file in html_dir.glob("*.html"):
        if is_homepage_html(html_file):
            console.print(f"  [red]✗[/red] {html_file.name} is homepage, deleting")
            html_file.unlink()
            deleted_html.append(html_file.name)

    console.print(f"Deleted {len(deleted_html)} bad HTML files\n")

    # Check processed JSON files
    console.print("[cyan]Checking processed JSON files...[/cyan]")
    processed_dir = Path("data/processed/patches")
    deleted_json = []

    for json_file in processed_dir.glob("*.json"):
        with open(json_file) as f:
            data = json.load(f)

        if len(data.get("changes", [])) == 0:
            version = data.get("metadata", {}).get("version", json_file.stem)
            url = data.get("metadata", {}).get("url", "unknown")
            console.print(f"  [red]✗[/red] {version} has 0 changes, deleting")
            console.print(f"    URL: {url}")
            json_file.unlink()
            deleted_json.append(version)

    console.print(f"Deleted {len(deleted_json)} empty JSON files\n")

    # Summary
    console.print("[bold green]Cleanup complete![/bold green]")
    console.print(f"  HTML files deleted: {len(deleted_html)}")
    console.print(f"  JSON files deleted: {len(deleted_json)}")

    if deleted_json:
        console.print("\n[yellow]These patches failed to parse (URLs may be dead):[/yellow]")
        for version in deleted_json:
            console.print(f"  - {version}")


if __name__ == "__main__":
    main()
