#!/usr/bin/env python3
"""Stage 1b: Download patches from Liquipedia for patches with broken Blizzard URLs.

Usage:
    uv run python scripts/1b_download_liquipedia.py

This script downloads HTML from Liquipedia for patches where the original
Blizzard URL is broken or unavailable. A warning note is added to indicate
the source is Liquipedia, not the official Blizzard patch notes.

Only patches with "liquipedia.net" as the primary URL are processed.
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
from rich.console import Console

from sc2patches.logger import PipelineLogger

console = Console()


def fetch_liquipedia_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML from Liquipedia.

    Args:
        url: Liquipedia URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        Exception: If request fails
    """
    headers = {
        "User-Agent": "SC2PatchesBot/1.0 (https://github.com/stared/sc2-balance-timeline; contact@example.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = httpx.get(url, timeout=timeout, headers=headers, follow_redirects=True)
    response.raise_for_status()
    return response.text


def validate_liquipedia_html(html: str, url: str) -> None:
    """Validate that HTML contains patch/balance content.

    Args:
        html: HTML content
        url: Source URL (for error message)

    Raises:
        Exception: If HTML is invalid
    """
    if not html.strip():
        raise Exception(f"Empty HTML from {url}")

    # Check for balance-related content
    balance_indicators = [
        "Balance Update",
        "balance changes",
        "Balance Changes",
        "Protoss",
        "Terran",
        "Zerg",
    ]

    has_balance = any(ind in html for ind in balance_indicators)

    if not has_balance:
        raise Exception(f"HTML from {url} doesn't contain balance changes")


def url_to_filename(url: str) -> str:
    """Convert Liquipedia URL to filename.

    Args:
        url: Liquipedia URL

    Returns:
        Filename without extension
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    # Last part is like "Patch_2.1" or "Patch_2.1.2"
    filename = path_parts[-1] if path_parts else "unknown"
    return filename


def load_liquipedia_patches(urls_path: Path) -> list[dict]:
    """Load patches that use Liquipedia as primary URL.

    Returns:
        List of patch dicts where url contains 'liquipedia.net'
    """
    with urls_path.open() as f:
        patches = json.load(f)

    return [p for p in patches if "liquipedia.net" in p.get("url", "")]


def main() -> None:
    """Download patches from Liquipedia."""
    urls_path = Path("data/patch_urls.json")
    html_dir = Path("data/raw_html")
    html_dir.mkdir(parents=True, exist_ok=True)

    logger = PipelineLogger("download_liquipedia")

    patches = load_liquipedia_patches(urls_path)

    if not patches:
        console.print("[yellow]No Liquipedia patches found in patch_urls.json[/yellow]")
        return

    console.print("\n[bold]Stage 1b: Download from Liquipedia[/bold]")
    console.print(f"Patches to download: {len(patches)}")
    console.print("[yellow]WARNING: These patches use Liquipedia because original Blizzard URLs are broken[/yellow]\n")

    for patch in patches:
        version = patch["version"]
        url = patch["url"]

        console.print(f"  Processing {version}...")

        try:
            html = fetch_liquipedia_html(url)
            validate_liquipedia_html(html, url)

            # Save HTML
            filename = url_to_filename(url)
            html_path = html_dir / f"{filename}.html"
            html_path.write_text(html, encoding="utf-8")

            size_kb = html_path.stat().st_size // 1024
            logger.log_success(version, f"{url} → {html_path.name} ({size_kb}KB)")
            console.print(f"[green]  ✓ {version}:[/green] {size_kb}KB → {html_path.name}")

            logger.log_detail(f"**{version}** (Liquipedia)")
            logger.log_detail(f"  - URL: {url}")
            logger.log_detail(f"  - HTML: {html_path.name}")
            logger.log_detail(f"  - NOTE: Original Blizzard URL is broken/unavailable")
            logger.log_detail("")

        except Exception as e:
            logger.log_failure(version, str(e))
            console.print(f"[red]  ✗ {version}:[/red] {str(e)[:80]}")

        time.sleep(1.0)  # Be polite to Liquipedia

    log_path = logger.write(
        additional_summary={
            "Total Liquipedia patches": len(patches),
            "HTML directory": str(html_dir),
            "Note": "Blizzard URLs broken, using Liquipedia as source",
        }
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Successful: {len(logger.successful)}")
    console.print(f"  ❌ Failed: {len(logger.failed)}")
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    if logger.failed:
        console.print(f"\n[red]Download failed for {len(logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Liquipedia download complete[/green]")


if __name__ == "__main__":
    main()
