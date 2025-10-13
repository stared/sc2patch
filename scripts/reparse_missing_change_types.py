"""Re-parse all patches that are missing change_type field."""

import json
from pathlib import Path
from rich.console import Console

console = Console()


def find_patches_missing_change_type() -> list[tuple[Path, Path]]:
    """Find all patches missing change_type and their source files."""
    patches_dir = Path("data/processed/patches")
    raw_patches_dir = Path("raw_patches")
    raw_html_dir = Path("data/raw_html")

    missing = []

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        changes = data.get("changes", [])
        if not changes:
            continue

        # Check if any change is missing change_type
        missing_types = [c for c in changes if not c.get("change_type")]

        if missing_types:
            # Find source file (markdown or HTML)
            version = data.get("metadata", {}).get("version", "")

            # Try markdown first
            md_file = raw_patches_dir / f"{version}.md"
            if md_file.exists():
                missing.append((patch_file, md_file))
                continue

            # Try HTML (for Liquipedia BU patches)
            # BU patches have various naming conventions
            if " BU" in patch_file.stem or "_BU" in patch_file.stem:
                # These were scraped from Liquipedia HTML
                html_candidates = list(raw_html_dir.glob("*.html"))
                # For now, mark as needing HTML parsing
                missing.append((patch_file, None))  # None = needs HTML scraping
            else:
                console.print(f"[yellow]Warning: No source found for {patch_file.name}[/yellow]")
                missing.append((patch_file, None))

    return missing


def main():
    """Re-parse all patches missing change_type."""
    console.print("\n[bold]Finding patches missing change_type...[/bold]\n")

    missing_patches = find_patches_missing_change_type()

    if not missing_patches:
        console.print("[green]✓ All patches have change_type![/green]")
        return

    console.print(f"Found {len(missing_patches)} patches missing change_type:\n")

    for patch_file, source_file in missing_patches:
        source_str = source_file.name if source_file else "[yellow]NO SOURCE[/yellow]"
        console.print(f"  • {patch_file.name} ← {source_str}")

    console.print(f"\n[bold red]ERROR: {len(missing_patches)} patches need re-parsing![/bold red]")
    console.print("\n[bold]These patches need to be re-parsed with change_type classification.[/bold]")
    console.print("Run parse_with_llm_v2.py on their source files, or scrape from Liquipedia if HTML.")


if __name__ == "__main__":
    main()
