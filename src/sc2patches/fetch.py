"""Fetch raw HTML from StarCraft 2 patch URLs."""

import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .discover import load_patch_urls

console = Console()


class FetchError(Exception):
    """Raised when HTML fetch fails."""


def fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML from URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        FetchError: If request fails or returns non-200 status
    """
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code} for {url}") from e
    except httpx.RequestError as e:
        raise FetchError(f"Request failed for {url}: {e}") from e


def url_to_filename(url: str) -> str:
    """Convert URL to safe filename.

    Args:
        url: URL to convert

    Returns:
        Filename (without extension)
    """
    parsed = urlparse(url)
    # Get last part of path
    path_parts = parsed.path.strip("/").split("/")
    filename = path_parts[-1] if path_parts else "index"

    # Remove common suffixes
    return filename.replace("-patch-notes", "").replace("_patch_notes", "")


def validate_patch_html(html: str, url: str) -> None:
    """Validate that HTML contains patch notes, not homepage.

    Args:
        html: HTML content
        url: Source URL (for error message)

    Raises:
        FetchError: If HTML is invalid or is homepage instead of patch notes
    """
    if not html.strip():
        raise FetchError(f"Empty HTML from {url}")

    # Check for homepage indicators
    homepage_indicators = [
        "The ultimate real-time strategy game",
        "REAL-TIME STRATEGY • FREE TO PLAY",
        "The Galaxy is Yours to Conquer",
        "<title>StarCraft II</title>",
    ]

    # Check for patch notes indicators
    patch_indicators = [
        "Patch Notes",
        "Balance Update",
        "patch notes",
        "balance changes",
        "Balance Changes",
    ]

    has_homepage_text = any(ind in html for ind in homepage_indicators)
    has_patch_text = any(ind in html for ind in patch_indicators)

    # If it has homepage text but no patch text, it's a homepage
    if has_homepage_text and not has_patch_text:
        raise FetchError(
            f"URL returned homepage instead of patch notes: {url}\n"
            "This URL is likely dead or redirected."
        )

    # If it has neither, it's probably an error page
    if not has_patch_text:
        raise FetchError(
            f"HTML from {url} doesn't appear to contain patch notes\n"
            "Expected to find: 'Patch Notes', 'Balance Update', etc."
        )


def fetch_url_to_html(url: str, output_dir: Path) -> Path:
    """Fetch URL and save as HTML file.

    Args:
        url: URL to fetch
        output_dir: Directory to save HTML files

    Returns:
        Path to saved HTML file

    Raises:
        FetchError: If fetch fails or content is invalid
    """
    # Fetch HTML
    html = fetch_html(url)

    # Validate content is patch notes, not homepage
    validate_patch_html(html, url)

    # Generate filename from URL
    filename = url_to_filename(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{filename}.html"

    # Save to file
    output_path.write_text(html, encoding="utf-8")

    return output_path


def fetch_all_patches(urls_path: Path, output_dir: Path, delay: float = 1.0) -> dict[str, Path]:
    """Fetch all patches from URL list as HTML files.

    Args:
        urls_path: Path to patch_urls.json
        output_dir: Directory to save HTML files
        delay: Delay between requests in seconds

    Returns:
        Dictionary mapping URL to output file path

    Raises:
        FetchError: If any fetch fails
        FileNotFoundError: If URLs file doesn't exist
    """
    # Load URLs
    urls = load_patch_urls(urls_path)
    results: dict[str, Path] = {}

    console.print(f"[bold]Fetching {len(urls)} patches as HTML...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching patches...", total=len(urls))

        for url in urls:
            filename = url_to_filename(url)
            progress.update(task, description=f"Fetching {filename}...")

            try:
                output_path = fetch_url_to_html(url, output_dir)
                results[url] = output_path
                console.print(f"[green]✓[/green] {output_path.name}")

            except FetchError as e:
                console.print(f"[red]✗[/red] {url}: {e}")
                raise

            progress.advance(task)

            # Be polite to the server
            if delay > 0:
                time.sleep(delay)

    console.print(f"\n[green]✓ Fetched {len(results)} HTML files[/green]")
    return results


def main() -> None:
    """Main entry point for fetching patches."""
    urls_path = Path("data/patch_urls.json")
    output_dir = Path("data/raw_html")

    try:
        fetch_all_patches(urls_path, output_dir, delay=1.0)
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
