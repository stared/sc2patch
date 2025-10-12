"""Download all StarCraft 2 balance patches from CSV."""

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sc2patches.fetch import fetch_url_to_html, FetchError
from sc2patches.convert import convert_html_to_markdown, ConvertError
from rich.console import Console
from rich.progress import track

console = Console()

# Complete URL mapping for all balance patches
PATCH_URLS = {
    # Wings of Liberty (1.x)
    "1.1.0": "https://news.blizzard.com/en-gb/starcraft2/9993888/patch-1-1-0-now-live",
    "1.1.2": "https://news.blizzard.com/en-gb/starcraft2/9990145",
    "1.1.3": "http://us.battle.net/sc2/en/blog/1113827/patch-113-now-live-11-9-2010",
    "1.2.0": "https://news.blizzard.com/en-gb/starcraft2/9995561",
    "1.3.0": "https://news.blizzard.com/en-us/starcraft2/2514162",
    "1.3.3": "https://news.blizzard.com/en-gb/starcraft2/9982849",
    "1.4.0": "https://news.blizzard.com/en-us/starcraft2/3549513/patch-1-4-0-now-live",
    "1.4.2": "https://news.blizzard.com/en-gb/starcraft2/10002543/patch-1-4-2-now-live",
    "1.4.3": "https://news.blizzard.com/en-gb/starcraft2/9995857/patch-1-4-3-now-live",
    "1.4.3 BU": "http://eu.battle.net/sc2/en/blog/4380324/Balance_Update_-_110512-10_05_2012",

    # Heart of the Swarm (2.x)
    "2.0.8 BU": "https://news.blizzard.com/en-us/starcraft2/9693907",
    "2.0.9": "http://us.battle.net/sc2/en/blog/10278173",
    "2.0.9 BU": "https://news.blizzard.com/en-us/starcraft2/10393911",
    "2.0.11 BU": "https://news.blizzard.com/en-us/starcraft2/10782713",
    "2.0.12": "https://news.blizzard.com/en-us/starcraft2/11523757",
    "2.1 BU": "https://news.blizzard.com/en-us/starcraft2/12802185",
    "2.1 BU2": "https://news.blizzard.com/en-us/starcraft2/13108934",
    "2.1.2 BU": "https://news.blizzard.com/en-us/starcraft2/14216442",
    "2.1.3 BU": "https://news.blizzard.com/en-us/starcraft2/14933073",
    "2.1.9 BU": "https://news.blizzard.com/en-us/starcraft2/18598811",

    # Legacy of the Void (3.x)
    "3.8.0": "https://news.blizzard.com/en-us/starcraft2/20372512/starcraft-ii-legacy-of-the-void-3-8-0-patch-notes",
    "3.8.0 BU": "https://news.blizzard.com/en-gb/starcraft2/20399161/legacy-of-the-void-balance-update-december-8-2016",
    "3.11.0 BU": "https://news.blizzard.com/en-us/article/20562669/legacy-of-the-void-balance-update-march-7-2017",
    "3.12.0 BU": "https://news.blizzard.com/en-gb/starcraft2/20720843/legacy-of-the-void-balance-update-april-2017",
    "3.14.0": "https://news.blizzard.com/en-us/article/20799759/starcraft-ii-legacy-of-the-void-3-14-0-patch-notes",

    # Legacy of the Void (4.x)
    "4.0.0": "https://news.blizzard.com/en-us/starcraft2/21183638/starcraft-ii-4-0-patch-notes",
    "4.0.2 BU": "https://news.blizzard.com/en-us/starcraft2/21272911/starcraft-ii-balance-update-november-28-2017",
    "4.1.1 BU": "https://news.blizzard.com/en-us/starcraft2/21349570",
    "4.1.4 BU": "https://news.blizzard.com/en-gb/starcraft2/21494433/starcraft-ii-balance-update-january-29-2018",
    "4.2.1 BU": "https://news.blizzard.com/en-us/starcraft2/21637913",
    "4.11.3": "https://news.blizzard.com/en-us/article/23230078/starcraft-ii-4-11-3-patch-notes",
    "4.11.4 BU": "https://news.blizzard.com/en-us/starcraft2/23312740/starcraft-ii-4-11-4-patch-notes",

    # Legacy of the Void (5.x)
    "5.0.2 BU": "https://news.blizzard.com/en-gb/starcraft2/23495670/starcraft-ii-5-0-2-patch-notes",
    "5.0.9": "https://news.blizzard.com/en-us/article/23774006/starcraft-ii-5-0-9-ptr-patch-notes",
    "5.0.12": "https://news.blizzard.com/en-us/starcraft2/24009150/starcraft-ii-5-0-12-patch-notes",
    "5.0.13": "https://news.blizzard.com/en-us/article/24078322/starcraft-ii-5-0-13-patch-notes",
    "5.0.14": "https://news.blizzard.com/en-us/article/24162754/starcraft-ii-5-0-14-patch-notes",
    "5.0.15": "https://news.blizzard.com/en-us/article/24225313/starcraft-ii-5-0-15-patch-notes",
}


def main():
    """Download all balance patches from CSV."""
    csv_path = Path("data/SC2_balance_patches_all.csv")
    html_dir = Path("data/raw_html")
    md_dir = Path("data/raw_patches")

    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    # Read CSV to get authoritative list
    patches = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            patches.append(row['Patch'])

    console.print(f"\n[bold]Downloading {len(patches)} balance patches from CSV...[/bold]\n")

    successful = 0
    failed = []
    skipped = []

    for version in track(patches, description="Processing patches..."):
        # Check if URL exists
        if version not in PATCH_URLS:
            console.print(f"[yellow]⊘ {version}:[/yellow] No URL mapping (skipped)")
            skipped.append(version)
            continue

        url = PATCH_URLS[version]

        # Check if already downloaded
        md_path = md_dir / f"{version}.md"
        if md_path.exists():
            console.print(f"[dim]↷ {version}:[/dim] Already exists")
            successful += 1
            continue

        try:
            # Download HTML
            console.print(f"[cyan]↓ {version}:[/cyan] {url}")
            html_path = fetch_url_to_html(url, html_dir)

            # Convert to Markdown
            convert_html_to_markdown(html_path, md_dir)
            console.print(f"  [green]✓[/green] Saved to {version}.md")

            successful += 1

            # Be polite to server
            time.sleep(1.0)

        except (FetchError, ConvertError) as e:
            console.print(f"  [red]✗ Failed:[/red] {e}")
            failed.append((version, str(e)))

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully processed: {successful}/{len(patches)}[/green]")

    if skipped:
        console.print(f"\n[yellow]Skipped (no URL): {len(skipped)}[/yellow]")
        for v in skipped:
            console.print(f"  {v}")

    if failed:
        console.print(f"\n[red]Failed: {len(failed)}[/red]")
        for version, error in failed:
            console.print(f"  {version}: {error}")


if __name__ == "__main__":
    main()
