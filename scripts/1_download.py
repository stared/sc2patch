#!/usr/bin/env python3
"""Stage 1: Download patches from URLs and convert to HTML + Markdown.

Usage:
    uv run python scripts/1_download.py              # Download all patches
    uv run python scripts/1_download.py --skip-existing  # Skip already downloaded

Supports new schema with:
- version: Patch version (e.g., "5.0.15", "4.1.4")
- url: Primary Blizzard News URL
- additional_urls: Optional array of additional URLs (for BU merging)
- liquipedia: Optional Liquipedia URL (not downloaded, for verification only)
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from sc2patches.download import DownloadError, download_patch, fetch_html, validate_patch_html
from sc2patches.logger import PipelineLogger

console = Console()


def load_patch_urls(urls_path: Path) -> list[dict]:
    """Load patch URLs from JSON file.

    Args:
        urls_path: Path to patch_urls.json

    Returns:
        List of patch dictionaries with 'version', 'url', and optional 'additional_urls'
    """
    if not urls_path.exists():
        console.print(f"[red]Error: {urls_path} not found[/red]")
        sys.exit(1)

    with urls_path.open() as f:
        data = json.load(f)

    # New format: list of objects with version, url, optional additional_urls, optional liquipedia
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data

    console.print(f"[red]Error: Invalid format in {urls_path}[/red]")
    console.print("Expected: list of objects with 'version' and 'url' keys")
    sys.exit(1)


def download_additional_url(
    url: str, html_dir: Path, version: str, index: int, skip_existing: bool
) -> Path | None:
    """Download an additional URL for BU merging.

    Args:
        url: URL to download
        html_dir: Directory to save HTML
        version: Patch version (for filename)
        index: Index of additional URL (0-based)
        skip_existing: Skip if file already exists

    Returns:
        Path to saved HTML file, or None if skipped/failed
    """
    filename = f"{version}_additional_{index}"
    html_path = html_dir / f"{filename}.html"

    if skip_existing and html_path.exists():
        return html_path

    try:
        html = fetch_html(url)
        validate_patch_html(html, url)
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html, encoding="utf-8")
        return html_path
    except DownloadError as e:
        console.print(f"[yellow]  Warning: Failed to download additional URL: {e}[/yellow]")
        return None


def process_patch(
    patch_info: dict,
    html_dir: Path,
    markdown_dir: Path,
    skip_existing: bool,
    logger: PipelineLogger,
) -> int:
    """Process a single patch: download main URL and additional URLs.

    Returns:
        Number of additional URLs downloaded
    """
    version = patch_info.get("version", "unknown")
    url = patch_info["url"]
    additional_urls = patch_info.get("additional_urls", [])
    additional_count = 0

    html_path, md_path, metadata = download_patch(
        url, html_dir, markdown_dir, skip_existing=skip_existing, version_hint=version
    )

    # Determine if it was skipped or downloaded
    if skip_existing and html_path.exists():
        logger.log_skip(version, "already exists")
        console.print(f"[dim]  ⊘ {version}: already exists[/dim]")
    else:
        size_kb = html_path.stat().st_size // 1024
        logger.log_success(version, f"{url} → {html_path.name} ({size_kb}KB), {md_path.name}")
        console.print(f"[green]  ✓ {version}:[/green] {size_kb}KB")

    # Download additional URLs (for BU merging)
    for i, add_url in enumerate(additional_urls):
        add_path = download_additional_url(add_url, html_dir, version, i, skip_existing)
        if add_path:
            add_size = add_path.stat().st_size // 1024
            console.print(f"[green]    + additional_{i}:[/green] {add_size}KB")
            additional_count += 1
        time.sleep(0.5)  # Be polite to server

    # Add detail info
    logger.log_detail(f"**{version}**")
    logger.log_detail(f"  - URL: {url}")
    logger.log_detail(f"  - HTML: {html_path.name}")
    logger.log_detail(f"  - Markdown: {md_path.name}")
    logger.log_detail(f"  - Date: {metadata.date}")
    if additional_urls:
        logger.log_detail(f"  - Additional URLs: {len(additional_urls)}")
    logger.log_detail("")

    return additional_count


def main() -> None:
    """Download all patches from patch_urls.json."""
    skip_existing = "--skip-existing" in sys.argv

    urls_path = Path("data/patch_urls.json")
    html_dir = Path("data/raw_html")
    markdown_dir = Path("data/raw_patches")
    logger = PipelineLogger("download")

    patches = load_patch_urls(urls_path)
    total_urls = sum(1 + len(p.get("additional_urls", [])) for p in patches)

    console.print("\n[bold]Stage 1: Download Patches[/bold]")
    console.print(f"Patches to process: {len(patches)}")
    console.print(f"Total URLs (including additional): {total_urls}")
    console.print(f"Skip existing: {skip_existing}\n")

    additional_downloaded = 0

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
            progress.update(task, description=f"Processing {version}")

            try:
                additional_downloaded += process_patch(
                    patch_info, html_dir, markdown_dir, skip_existing, logger
                )
            except DownloadError as e:
                logger.log_failure(version, str(e))
                console.print(f"[red]  ✗ {version}:[/red] {str(e)[:80]}")

            progress.advance(task)
            if not skip_existing:
                time.sleep(1.0)

    log_path = logger.write(
        additional_summary={
            "Total patches": len(patches),
            "Additional URLs downloaded": additional_downloaded,
            "HTML directory": str(html_dir),
            "Markdown directory": str(markdown_dir),
        }
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Successful: {len(logger.successful)}")
    console.print(f"  ❌ Failed: {len(logger.failed)}")
    console.print(f"  ⊘ Skipped: {len(logger.skipped)}")
    console.print(f"  📎 Additional URLs: {additional_downloaded}")
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    if logger.failed:
        console.print(f"\n[red]Download failed for {len(logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Download stage complete[/green]")


if __name__ == "__main__":
    main()
