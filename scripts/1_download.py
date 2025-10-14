#!/usr/bin/env python3
"""Stage 1: Download patches from URLs and convert to HTML + Markdown.

Usage:
    uv run python scripts/1_download.py              # Download all patches
    uv run python scripts/1_download.py --skip-existing  # Skip already downloaded
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from sc2patches.download import DownloadError, download_patch
from sc2patches.logger import PipelineLogger

console = Console()


def load_patch_urls(urls_path: Path) -> list[dict]:
    """Load patch URLs from JSON file.

    Args:
        urls_path: Path to patch_urls.json

    Returns:
        List of patch dictionaries with 'version' and 'url' keys
    """
    if not urls_path.exists():
        console.print(f"[red]Error: {urls_path} not found[/red]")
        sys.exit(1)

    with open(urls_path) as f:
        data = json.load(f)

    # Handle both old format (list of URLs) and new format (dict with patches list)
    if isinstance(data, list):
        # Old format: convert to new format
        return [{"version": f"unknown-{i}", "url": url} for i, url in enumerate(data)]
    if isinstance(data, dict) and "patches" in data:
        # New format
        return data["patches"]
    console.print(f"[red]Error: Invalid format in {urls_path}[/red]")
    sys.exit(1)


def main() -> None:
    """Download all patches from patch_urls.json."""
    # Parse arguments
    skip_existing = "--skip-existing" in sys.argv

    # Setup paths
    urls_path = Path("data/patch_urls.json")
    html_dir = Path("data/raw_html")
    markdown_dir = Path("data/raw_patches")

    # Create logger
    logger = PipelineLogger("download")

    # Load patches to download
    patches = load_patch_urls(urls_path)

    console.print("\n[bold]Stage 1: Download Patches[/bold]")
    console.print(f"Patches to process: {len(patches)}")
    console.print(f"Skip existing: {skip_existing}\n")

    # Download patches with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading...", total=len(patches))

        for patch_info in patches:
            version = patch_info.get("version", "unknown")
            url = patch_info["url"]

            progress.update(task, description=f"Processing {version}")

            try:
                html_path, md_path, metadata = download_patch(
                    url, html_dir, markdown_dir, skip_existing=skip_existing
                )

                # Determine if it was skipped or downloaded
                if skip_existing and html_path.exists():
                    # Check if it existed before this run
                    logger.log_skip(version, "already exists")
                    console.print(f"[dim]  ⊘ {version}: already exists[/dim]")
                else:
                    size_kb = html_path.stat().st_size // 1024
                    logger.log_success(
                        version, f"{url} → {html_path.name} ({size_kb}KB), {md_path.name}"
                    )
                    console.print(f"[green]  ✓ {version}:[/green] {size_kb}KB")

                # Add detail info
                logger.log_detail(f"**{version}**")
                logger.log_detail(f"  - URL: {url}")
                logger.log_detail(f"  - HTML: {html_path.name}")
                logger.log_detail(f"  - Markdown: {md_path.name}")
                logger.log_detail(f"  - Date: {metadata.date}")
                logger.log_detail("")

            except DownloadError as e:
                logger.log_failure(version, str(e))
                console.print(f"[red]  ✗ {version}:[/red] {str(e)[:80]}")

            progress.advance(task)

            # Be polite to server (1 second delay)
            if not skip_existing:
                time.sleep(1.0)

    # Write log
    log_path = logger.write(
        additional_summary={
            "Total patches": len(patches),
            "HTML directory": str(html_dir),
            "Markdown directory": str(markdown_dir),
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
        console.print(f"\n[red]Download failed for {len(logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Download stage complete[/green]")


if __name__ == "__main__":
    main()
