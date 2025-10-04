"""Load and validate StarCraft 2 patch URLs."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def load_patch_urls(urls_path: Path) -> list[str]:
    """Load patch URLs from JSON file.

    Args:
        urls_path: Path to patch_urls.json

    Returns:
        List of patch URLs

    Raises:
        FileNotFoundError: If URLs file doesn't exist
        ValueError: If URLs list is invalid or empty
    """
    if not urls_path.exists():
        raise FileNotFoundError(f"Patch URLs file not found: {urls_path}")

    with urls_path.open() as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Patch URLs file must contain a JSON array")

    if not data:
        raise ValueError("Patch URLs list is empty")

    # Validate each URL
    for i, url in enumerate(data):
        if not isinstance(url, str):
            raise ValueError(f"URL at index {i} is not a string: {url}")
        if not url.strip():
            raise ValueError(f"Empty URL at index {i}")
        if not url.startswith("https://"):
            raise ValueError(f"Invalid URL at index {i}: {url}")

    console.print(f"[green]✓[/green] Loaded {len(data)} patch URLs from {urls_path}")
    return data


def display_urls_summary(urls: list[str]) -> None:
    """Display summary table of patch URLs.

    Args:
        urls: List of patch URLs
    """
    table = Table(title="StarCraft 2 Patch URLs")
    table.add_column("#", style="dim", justify="right")
    table.add_column("URL", style="blue", overflow="fold")

    for i, url in enumerate(urls, 1):
        table.add_row(str(i), url)

    console.print(table)
    console.print(f"\n[green]Total URLs: {len(urls)}[/green]")


def main() -> None:
    """Main entry point for loading patch URLs."""
    console.print("[bold]Loading StarCraft 2 Patch URLs...[/bold]\n")

    urls_path = Path("data/patch_urls.json")
    urls = load_patch_urls(urls_path)
    display_urls_summary(urls)


if __name__ == "__main__":
    main()
