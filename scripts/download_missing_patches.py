"""Download and convert missing balance patches from CSV."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sc2patches.fetch import fetch_url_to_html, FetchError
from sc2patches.convert import convert_html_to_markdown
from rich.console import Console
from rich.progress import track
import time

console = Console()

def main():
    """Download missing patches."""
    # Load missing patch URLs
    missing_urls_path = Path("data/missing_patch_urls.json")
    with open(missing_urls_path) as f:
        missing_patches = json.load(f)

    console.print(f"\n[bold]Downloading {len(missing_patches)} missing balance patches...[/bold]\n")

    html_dir = Path("data/raw_html")
    md_dir = Path("data/raw_patches")
    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    successful = 0
    failed = []

    for version, url in track(list(missing_patches.items()), description="Downloading patches..."):
        try:
            # Download HTML
            console.print(f"[cyan]{version}[/cyan]: Fetching {url}")
            html_path = fetch_url_to_html(url, html_dir)
            console.print(f"  [green]✓[/green] Downloaded to {html_path.name}")

            # Convert to Markdown
            md_path = convert_html_to_markdown(html_path, md_dir)
            console.print(f"  [green]✓[/green] Converted to {md_path.name}")

            successful += 1

            # Be polite to server
            time.sleep(1.0)

        except (FetchError, Exception) as e:
            console.print(f"  [red]✗ Failed:[/red] {e}")
            failed.append((version, str(e)))

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully downloaded: {successful}/{len(missing_patches)}[/green]")

    if failed:
        console.print(f"\n[red]Failed patches ({len(failed)}):[/red]")
        for version, error in failed:
            console.print(f"  {version}: {error}")

if __name__ == "__main__":
    main()
