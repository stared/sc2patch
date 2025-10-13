#!/usr/bin/env python3
"""Stage 2: Parse HTML patches with GPT-5 to extract structured balance changes.

Usage:
    uv run python scripts/2_parse.py                    # Parse all HTML files
    uv run python scripts/2_parse.py --skip-existing    # Skip already parsed
    uv run python scripts/2_parse.py 5.0.15             # Parse specific version
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from sc2patches.logger import PipelineLogger
from sc2patches.parse import ParseError, parse_patch

# Load environment variables from .env file
load_dotenv()

console = Console()


def load_patch_urls_mapping(urls_path: Path) -> dict[str, str]:
    """Load URL mapping from patch_urls.json.

    Returns:
        Dict mapping filename stems to URLs
    """
    if not urls_path.exists():
        return {}

    with urls_path.open() as f:
        data = json.load(f)

    # Extract URLs
    if isinstance(data, list):
        urls = data
    elif isinstance(data, dict) and "patches" in data:
        urls = [p["url"] for p in data["patches"]]
    else:
        return {}

    # Map filename to URL
    mapping = {}
    for url in urls:
        # Extract filename from URL (last path component)
        filename = url.rstrip("/").split("/")[-1].replace("-patch-notes", "")
        mapping[filename] = url

    return mapping


def main() -> None:
    """Parse all HTML patches with GPT-5."""
    # Parse arguments
    skip_existing = "--skip-existing" in sys.argv
    specific_version = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            specific_version = arg
            break

    # Setup paths
    html_dir = Path("data/raw_html")
    output_dir = Path("data/processed/patches")
    urls_path = Path("data/patch_urls.json")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load URL mapping
    url_mapping = load_patch_urls_mapping(urls_path)

    # Create logger
    logger = PipelineLogger("parse")

    # Get HTML files to parse
    if specific_version:
        html_files = list(html_dir.glob(f"*{specific_version}*.html"))
        if not html_files:
            console.print(f"[red]No HTML files found for version: {specific_version}[/red]")
            sys.exit(1)
    else:
        html_files = sorted(html_dir.glob("*.html"))

    console.print("\n[bold]Stage 2: Parse Patches with GPT-5[/bold]")
    console.print(f"HTML files to parse: {len(html_files)}")
    console.print(f"Skip existing: {skip_existing}\n")

    # Filter out files that already have output (if skip_existing)
    if skip_existing:
        files_to_parse = []
        for html_path in html_files:
            # We need to parse to know version, so we can't perfectly skip
            # Instead, we'll check after parsing
            files_to_parse.append(html_path)
        html_files = files_to_parse

    # Parse patches with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing...", total=len(html_files))

        for html_path in html_files:
            filename = html_path.stem
            progress.update(task, description=f"Processing {filename}")

            try:
                # Parse with GPT-5
                result = parse_patch(html_path)
                version = result["metadata"]["version"]

                # Add URL from mapping if available
                if filename in url_mapping:
                    result["metadata"]["url"] = url_mapping[filename]
                elif version in url_mapping:
                    result["metadata"]["url"] = url_mapping[version]

                # Save output
                output_path = output_dir / f"{version}.json"
                if output_path.exists() and skip_existing:
                    # Already exists (shouldn't happen after check above, but be safe)
                    logger.log_skip(version, "already exists")
                    console.print(f"[dim]  ⊘ {version}: already exists[/dim]")
                else:
                    # Save to JSON
                    with output_path.open("w") as f:
                        json.dump(result, f, indent=2)

                    entities = len({c["entity_id"] for c in result["changes"]})
                    changes = len(result["changes"])

                    logger.log_success(
                        version, f"{entities} entities, {changes} changes → {output_path.name}"
                    )
                    console.print(
                        f"[green]  ✓ {version}:[/green] {entities} entities, {changes} changes"
                    )

                # Add detail info
                logger.log_detail(f"**{version}** ({filename})")
                logger.log_detail(f"  - Entities: {entities}")
                logger.log_detail(f"  - Changes: {changes}")
                logger.log_detail(f"  - Output: {output_path.name}")
                logger.log_detail("")

                # Be polite to API (2 second delay between requests)
                if not skip_existing:
                    time.sleep(2.0)

            except ParseError as e:
                logger.log_failure(filename, str(e))
                console.print(f"[red]  ✗ {filename}:[/red] {str(e)[:100]}")
                # Note: Don't exit on ParseError - some patches may have no balance changes

            progress.advance(task)

    # Write log
    log_path = logger.write(
        additional_summary={
            "Total files": len(html_files),
            "Output directory": str(output_dir),
        }
    )

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Successful: {len(logger.successful)}")
    console.print(f"  ❌ Failed: {len(logger.failed)}")
    console.print(f"  ⊘ Skipped: {len(logger.skipped)}")
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    # Exit with error if any failures
    if logger.failed:
        console.print(f"\n[red]Parse failed for {len(logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Parse stage complete[/green]")


if __name__ == "__main__":
    main()
