#!/usr/bin/env python3
"""Stage 2: Parse HTML patches with LLM to extract structured balance changes.

Usage:
    uv run python scripts/2_parse.py                    # Parse all HTML files
    uv run python scripts/2_parse.py --skip-existing    # Skip already parsed
    uv run python scripts/2_parse.py 5.0.15             # Parse specific version

Supports multi-HTML parsing when patches have additional_urls in patch_urls.json.
The LLM parses main + BU HTML files together for intelligent deduplication.
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from sc2patches.logger import PipelineLogger
from sc2patches.parse import ParseError, parse_patch, parse_patches_combined

# Load environment variables from .env file
load_dotenv()

console = Console()


def load_patch_config(urls_path: Path) -> list[dict]:
    """Load patch configuration from patch_urls.json.

    Returns:
        List of patch config dicts with version, url, additional_urls
    """
    if not urls_path.exists():
        return []

    with urls_path.open() as f:
        data = json.load(f)

    # New format: list of objects with version, url, optional additional_urls
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data

    return []


def url_to_filename(url: str) -> str:
    """Convert URL to expected filename (without extension)."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    filename = path_parts[-1] if path_parts else "index"
    return filename.replace("-patch-notes", "").replace("_patch_notes", "")


def find_html_files_for_patch(html_dir: Path, version: str, url: str | None = None) -> list[Path]:
    """Find all HTML files for a patch version (main + additional).

    Looks for:
    - Main file: matches version in filename OR URL-derived filename
    - Additional files: {version}_additional_*.html

    Returns:
        List of HTML paths, main file first
    """
    main_files = []
    additional_files = []

    # Expected filename from URL
    expected_filename = url_to_filename(url) if url else None

    # Find main file - look for files containing the version OR matching URL
    for html_path in html_dir.glob("*.html"):
        stem = html_path.stem
        # Skip additional files
        if "_additional_" in stem:
            continue
        # Match version in filename or URL-derived filename
        version_matches = version.replace(".", "-") in stem or version in stem
        url_matches = expected_filename and stem == expected_filename
        if version_matches or url_matches:
            main_files.append(html_path)

    # Find additional files
    for html_path in html_dir.glob(f"{version}_additional_*.html"):
        additional_files.append(html_path)

    # Sort additional files by index
    additional_files.sort()

    # Return main file first, then additional
    if main_files:
        return main_files[:1] + additional_files
    return additional_files


def process_single_patch(
    patch_config: dict,
    html_dir: Path,
    output_dir: Path,
    skip_existing: bool,
    logger: PipelineLogger,
) -> bool:
    """Process a single patch configuration.

    Returns:
        True if processing should continue (success or skip), False otherwise
    """
    version = patch_config["version"]
    url = patch_config["url"]
    output_path = output_dir / f"{version}.json"

    # Check if output already exists
    if output_path.exists() and skip_existing:
        logger.log_skip(version, "already exists")
        console.print(f"[dim]  ⊘ {version}: already exists[/dim]")
        return True

    # Find HTML files for this patch
    html_files = find_html_files_for_patch(html_dir, version, url)
    if not html_files:
        logger.log_skip(version, "no HTML files found")
        console.print(f"[dim]  ⊘ {version}: no HTML files[/dim]")
        return True

    # Parse with appropriate method
    if len(html_files) > 1:
        console.print(f"[cyan]  ↳ Parsing {len(html_files)} files together...[/cyan]")
        result = parse_patches_combined(html_files)
    else:
        result = parse_patch(html_files[0])

    # Override version and URL from config (LLM might extract wrong version for BU patches)
    result["metadata"]["version"] = version
    result["metadata"]["url"] = url
    # Also update patch_version in each change
    for change in result["changes"]:
        change["patch_version"] = version

    # Save to JSON
    with output_path.open("w") as f:
        json.dump(result, f, indent=2)

    entities = len({c["entity_id"] for c in result["changes"]})
    changes = len(result["changes"])
    suffix = f" (merged {len(html_files)} files)" if len(html_files) > 1 else ""

    logger.log_success(version, f"{entities} entities, {changes} changes → {output_path.name}")
    console.print(f"[green]  ✓ {version}:[/green] {entities} entities, {changes} changes{suffix}")

    # Add detail info
    logger.log_detail(f"**{version}**")
    logger.log_detail(f"  - HTML files: {[h.name for h in html_files]}")
    logger.log_detail(f"  - Entities: {entities}, Changes: {changes}")
    logger.log_detail("")

    return True


def main() -> None:
    """Parse all HTML patches with Gemini 3 Pro."""
    skip_existing = "--skip-existing" in sys.argv
    specific_version = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    html_dir = Path("data/raw_html")
    output_dir = Path("data/processed/patches")
    urls_path = Path("data/patch_urls.json")
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_configs = load_patch_config(urls_path)
    logger = PipelineLogger("parse")

    if specific_version:
        configs_to_parse = [p for p in patch_configs if p["version"] == specific_version]
        if not configs_to_parse:
            console.print(f"[red]No config found for version: {specific_version}[/red]")
            sys.exit(1)
    else:
        configs_to_parse = patch_configs

    multi_html_count = sum(1 for p in configs_to_parse if p.get("additional_urls"))

    console.print("\n[bold]Stage 2: Parse Patches with Gemini 3 Pro[/bold]")
    console.print(f"Patches to parse: {len(configs_to_parse)}")
    console.print(f"Patches with additional URLs (multi-HTML): {multi_html_count}")
    console.print(f"Skip existing: {skip_existing}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing...", total=len(configs_to_parse))

        for patch_config in configs_to_parse:
            progress.update(task, description=f"Processing {patch_config['version']}")

            try:
                process_single_patch(patch_config, html_dir, output_dir, skip_existing, logger)
                time.sleep(2.0)  # Be polite to API
            except ParseError as e:
                logger.log_failure(patch_config["version"], str(e))
                console.print(f"[red]  ✗ {patch_config['version']}:[/red] {str(e)[:100]}")

            progress.advance(task)

    log_path = logger.write(
        additional_summary={
            "Total patches": len(configs_to_parse),
            "Multi-HTML patches": multi_html_count,
            "Output directory": str(output_dir),
        }
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Successful: {len(logger.successful)}")
    console.print(f"  ❌ Failed: {len(logger.failed)}")
    console.print(f"  ⊘ Skipped: {len(logger.skipped)}")
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    if logger.failed:
        console.print(f"\n[red]Parse failed for {len(logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Parse stage complete[/green]")


if __name__ == "__main__":
    main()
