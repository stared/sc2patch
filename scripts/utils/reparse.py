#!/usr/bin/env python3
"""Re-parse specific patches with different model or validate for Co-op content.

Usage:
    uv run python scripts/utils/reparse.py                           # Check all for Co-op
    uv run python scripts/utils/reparse.py --fix                     # Re-parse patches with Co-op
    uv run python scripts/utils/reparse.py --model google/gemini-3-pro-preview --fix
    uv run python scripts/utils/reparse.py 4.11.4                    # Re-parse specific version
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv
from rich.console import Console

from sc2patches.parse import ParseError, parse_patch

# Load environment variables from .env file
load_dotenv()

console = Console()


def get_api_key() -> str:
    """Get OpenRouter API key from environment."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key
    console.print("[red]OPENROUTER_API_KEY not set in environment[/red]")
    sys.exit(1)


# Co-op keywords to detect
COOP_KEYWORDS = [
    "alarak",
    "karax",
    "zeratul",
    "fenix",
    "artanis",
    "swann",
    "mengsk",
    "nova",
    "tychus",
    "blaze",
    "nikara",
    "rattlesnake",
    "vega",
    "zagara",
    "stukov",
    "abathur",
    "dehaka",
    "stetmann",
    "kerrigan",
    "mecha",
    "infested",
    "hercules",
    "galleon",
    "aberration",
    "gary",
    "bile_launcher",
    "sky_fury",
    "strike_fighter",
    "laser_drill",
    "automated_refinery",
    "war_prism",
]


def has_coop_content(changes: list) -> list:
    """Check if changes contain Co-op content."""
    return [c for c in changes if any(kw in c["entity_id"] for kw in COOP_KEYWORDS)]


def load_patch_urls_mapping(urls_path: Path) -> dict[str, str]:
    """Load URL mapping from patch_urls.json."""
    if not urls_path.exists():
        return {}
    with urls_path.open() as f:
        data = json.load(f)
    if isinstance(data, list):
        urls = data
    elif isinstance(data, dict) and "patches" in data:
        urls = [p["url"] for p in data["patches"]]
    else:
        return {}
    mapping = {}
    for url in urls:
        filename = url.rstrip("/").split("/")[-1].replace("-patch-notes", "")
        mapping[filename] = url
    return mapping


def find_html_for_version(version: str, html_dir: Path) -> Path | None:
    """Find HTML file for a given version."""
    # Try exact match first
    exact = html_dir / f"{version}.html"
    if exact.exists():
        return exact
    # Try partial match with dots
    matches = list(html_dir.glob(f"*{version}*.html"))
    if matches:
        return matches[0]
    # Try with dashes instead of dots (e.g., 4.11.4 -> 4-11-4)
    version_dashed = version.replace(".", "-")
    matches = list(html_dir.glob(f"*{version_dashed}*.html"))
    if matches:
        return matches[0]
    return None


def main() -> None:
    """Re-parse patches with Co-op content or specific versions."""
    # Parse arguments
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
    fix_mode = "--fix" in sys.argv
    specific_versions = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        elif arg in ("--fix",):
            i += 1
        else:
            specific_versions.append(arg)
            i += 1

    # Set model
    os.environ["OPENROUTER_MODEL"] = model

    # Setup paths
    html_dir = Path("data/raw_html")
    patches_dir = Path("data/processed/patches")
    urls_path = Path("data/patch_urls.json")
    url_mapping = load_patch_urls_mapping(urls_path)

    console.print("\n[bold]Re-parse/Validate Patches[/bold]")
    console.print(f"Model: {model}")
    console.print(f"Fix mode: {fix_mode}\n")

    # Get API key for parsing
    api_key = get_api_key()

    if specific_versions:
        # Re-parse specific versions
        for spec in specific_versions:
            # Try as HTML filename first
            html_path = html_dir / f"{spec}.html"
            if not html_path.exists():
                html_path = find_html_for_version(spec, html_dir)

            if not html_path:
                console.print(f"[red]No HTML file found for: {spec}[/red]")
                continue

            console.print(f"Re-parsing {html_path.name}...")
            try:
                parsed = parse_patch(html_path, version=spec, api_key=api_key)
                # Convert ParsedChange list to dicts for coop check
                changes_dicts = [{"entity_id": c.entity_id, "raw_text": c.raw_text} for c in parsed.changes]
                coop = has_coop_content(changes_dicts)

                # Add URL from mapping
                filename = html_path.stem
                if filename in url_mapping:
                    parsed.url = url_mapping[filename]

                console.print(f"  Version: {parsed.version}")
                console.print(f"  Changes: {len(parsed.changes)}")
                console.print(f"  Co-op entries: {len(coop)}")

                if coop:
                    console.print("[yellow]  Co-op content found:[/yellow]")
                    for c in coop:
                        console.print(f"    - {c['entity_id']}")

                # Save
                output_path = patches_dir / f"{parsed.version}.json"
                with output_path.open("w") as f:
                    json.dump(parsed.to_json_dict(), f, indent=2)
                console.print(f"[green]  Saved to {output_path}[/green]")

                time.sleep(2.0)  # Rate limit

            except ParseError as e:
                console.print(f"[yellow]  ⚠ {spec}: {str(e)[:80]}[/yellow]")

        return
    # Scan all patches for Co-op content
    patches_with_coop = []

    for json_path in sorted(patches_dir.glob("*.json")):
        with json_path.open() as f:
            data = json.load(f)
        coop = has_coop_content(data.get("changes", []))
        if coop:
            patches_with_coop.append((json_path, data, coop))
            console.print(f"[yellow]⚠ {json_path.name}:[/yellow] {len(coop)} Co-op entries")
            for c in coop:
                console.print(f"    - {c['entity_id']}: {c['raw_text'][:50]}...")

    if not patches_with_coop:
        console.print("[green]✓ No Co-op content found in any patches![/green]")
        return

    console.print(f"\n[bold]Found {len(patches_with_coop)} patches with Co-op content[/bold]")

    if fix_mode:
        console.print("\n[bold]Re-parsing with updated prompt...[/bold]\n")

        for _json_path, data, _coop in patches_with_coop:
            version = data["metadata"]["version"]
            html_path = find_html_for_version(version, html_dir)

            if not html_path:
                console.print(f"[red]  ✗ {version}: No HTML file found[/red]")
                continue

            console.print(f"Re-parsing {version} ({html_path.name})...")
            try:
                parsed = parse_patch(html_path, version=version, api_key=api_key)
                changes_dicts = [{"entity_id": c.entity_id} for c in parsed.changes]
                new_coop = has_coop_content(changes_dicts)

                # Add URL from mapping
                filename = html_path.stem
                if filename in url_mapping:
                    parsed.url = url_mapping[filename]

                # Save
                output_path = patches_dir / f"{parsed.version}.json"
                with output_path.open("w") as f:
                    json.dump(parsed.to_json_dict(), f, indent=2)

                if new_coop:
                    console.print(f"[yellow]  ⚠ {version}: Still has {len(new_coop)} Co-op entries[/yellow]")
                else:
                    console.print(f"[green]  ✓ {version}: Clean ({len(parsed.changes)} changes)[/green]")

                time.sleep(2.0)  # Rate limit

            except ParseError as e:
                console.print(f"[red]  ✗ {version}: {e}[/red]")
    else:
        console.print("\n[dim]Run with --fix to re-parse these patches[/dim]")


if __name__ == "__main__":
    main()
