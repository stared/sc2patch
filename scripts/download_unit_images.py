"""Download unit images from StarCraft Wiki."""

import json
import re
import time
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track

console = Console()

# Map unit IDs to their expected wiki names
# This handles cases where our IDs don't match wiki naming
UNIT_NAME_MAPPING = {
    "terran-scv": "SCV",
    "terran-marine": "Marine",
    "terran-marauder": "Marauder",
    "terran-reaper": "Reaper",
    "terran-ghost": "Ghost",
    "terran-hellion": "Hellion",
    "terran-hellbat": "Hellbat",
    "terran-widow_mine": "Widow_Mine",
    "terran-cyclone": "Cyclone",
    "terran-siege_tank": "Siege_Tank",
    "terran-thor": "Thor",
    "terran-viking": "Viking",
    "terran-medivac": "Medivac",
    "terran-liberator": "Liberator",
    "terran-raven": "Raven",
    "terran-banshee": "Banshee",
    "terran-battlecruiser": "Battlecruiser",
    "terran-mule": "MULE",

    "protoss-probe": "Probe",
    "protoss-zealot": "Zealot",
    "protoss-stalker": "Stalker",
    "protoss-sentry": "Sentry",
    "protoss-adept": "Adept",
    "protoss-high_templar": "High_Templar",
    "protoss-dark_templar": "Dark_Templar",
    "protoss-immortal": "Immortal",
    "protoss-colossus": "Colossus",
    "protoss-disruptor": "Disruptor",
    "protoss-observer": "Observer",
    "protoss-warp_prism": "Warp_Prism",
    "protoss-phoenix": "Phoenix",
    "protoss-void_ray": "Void_Ray",
    "protoss-oracle": "Oracle",
    "protoss-tempest": "Tempest",
    "protoss-carrier": "Carrier",
    "protoss-mothership": "Mothership",
    "protoss-archon": "Archon",

    "zerg-drone": "Drone",
    "zerg-overlord": "Overlord",
    "zerg-zergling": "Zergling",
    "zerg-baneling": "Baneling",
    "zerg-roach": "Roach",
    "zerg-ravager": "Ravager",
    "zerg-hydralisk": "Hydralisk",
    "zerg-lurker": "Lurker",
    "zerg-infestor": "Infestor",
    "zerg-swarm_host": "Swarm_Host",
    "zerg-ultralisk": "Ultralisk",
    "zerg-queen": "Queen",
    "zerg-mutalisk": "Mutalisk",
    "zerg-corruptor": "Corruptor",
    "zerg-brood_lord": "Brood_Lord",
    "zerg-broodling": "Broodling",
    "zerg-viper": "Viper",
    "zerg-overseer": "Overseer",
    "zerg-changeling": "Changeling",
    "zerg-locust": "Locust",
}


def get_wiki_image_url(unit_id: str) -> Optional[str]:
    """Try to find the image URL for a unit from the wiki."""

    wiki_name = UNIT_NAME_MAPPING.get(unit_id)
    if not wiki_name:
        console.print(f"[yellow]No mapping for {unit_id}[/yellow]")
        return None

    # Common URL patterns found on the wiki
    race = unit_id.split("-")[0].capitalize()

    # Try different URL patterns
    patterns = [
        f"https://static.wikia.nocookie.net/starcraft/images/{{hash}}/Icon_{race}_{wiki_name}.jpg",
        f"https://static.wikia.nocookie.net/starcraft/images/{{hash}}/{wiki_name}_SC2_Icon1.jpg",
        f"https://static.wikia.nocookie.net/starcraft/images/{{hash}}/{wiki_name}_SC2_Icon.jpg",
        f"https://static.wikia.nocookie.net/starcraft/images/{{hash}}/Icon_{wiki_name}.jpg",
    ]

    # We need to scrape the actual page to get the hash
    unit_page_url = f"https://starcraft.fandom.com/wiki/{wiki_name}"

    try:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(unit_page_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Look for unit icon in the infobox
            infobox = soup.find("table", class_="infobox")
            if infobox:
                img_tag = infobox.find("img", alt=lambda x: x and wiki_name.replace("_", " ") in x)
                if not img_tag:
                    # Try to find any image in infobox
                    img_tag = infobox.find("img")

                if img_tag and img_tag.get("src"):
                    # Get the actual image URL
                    img_url = img_tag["src"]
                    # Remove any query parameters
                    if "/revision/" in img_url:
                        img_url = img_url.split("/revision/")[0]
                    return img_url

    except Exception as e:
        console.print(f"[red]Error fetching {unit_page_url}: {e}[/red]")

    return None


def download_image(url: str, output_path: Path) -> bool:
    """Download an image from URL to the specified path."""
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=10, follow_redirects=True)
            response.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True

    except Exception as e:
        console.print(f"[red]Error downloading {url}: {e}[/red]")
        return False


def main():
    """Download all unit images."""

    # Load units data
    units_file = Path("data/units.json")
    units_data = json.loads(units_file.read_text())

    # Filter for actual units only (not buildings, upgrades, abilities)
    units = [u for u in units_data if u["type"] == "unit"]

    console.print(f"[green]Found {len(units)} units to download images for[/green]")

    # Create output directory
    output_dir = Path("visualization/public/assets/units")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track successful downloads
    downloaded = 0
    failed = []

    for unit in track(units, description="Downloading unit images..."):
        unit_id = unit["id"]

        # Output filename
        output_path = output_dir / f"{unit_id}.jpg"

        # Skip if already downloaded
        if output_path.exists():
            console.print(f"[dim]Skipping {unit_id} (already exists)[/dim]")
            downloaded += 1
            continue

        # Get image URL
        img_url = get_wiki_image_url(unit_id)

        if img_url:
            if download_image(img_url, output_path):
                console.print(f"[green]✓[/green] Downloaded {unit_id}")
                downloaded += 1
            else:
                failed.append(unit_id)
        else:
            console.print(f"[yellow]Could not find image URL for {unit_id}[/yellow]")
            failed.append(unit_id)

        # Be polite to the wiki server
        time.sleep(0.5)

    # Summary
    console.print("\n[bold]Download Summary:[/bold]")
    console.print(f"[green]Successfully downloaded: {downloaded}/{len(units)}[/green]")

    if failed:
        console.print(f"[red]Failed to download {len(failed)} units:[/red]")
        for unit_id in failed:
            console.print(f"  - {unit_id}")

    # Create a placeholder image for missing units
    placeholder_path = output_dir / "placeholder.png"
    if not placeholder_path.exists():
        console.print("\n[yellow]Note: You may want to add a placeholder.png for missing units[/yellow]")


if __name__ == "__main__":
    main()