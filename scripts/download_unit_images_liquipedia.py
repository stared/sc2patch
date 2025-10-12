"""Download unit images from Liquipedia."""

import json
import time
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track

console = Console()

# Map unit IDs to Liquipedia unit names
# Liquipedia uses format: Techtree-unit-[race]-[unit].png
UNIT_NAME_MAPPING = {
    # Terran units
    "terran-scv": "scv",
    "terran-marine": "marine",
    "terran-marauder": "marauder",
    "terran-reaper": "reaper",
    "terran-ghost": "ghost",
    "terran-hellion": "hellion",
    "terran-hellbat": "hellionbattlemode",  # Special name on Liquipedia
    "terran-widow_mine": "widowmine",  # Note: no underscore in Liquipedia
    "terran-cyclone": "cyclone",
    "terran-siege_tank": "siegetank",  # Note: no underscore
    "terran-thor": "thor",
    "terran-viking": "vikingfighter",  # Special name on Liquipedia
    "terran-medivac": "medivac",
    "terran-liberator": "liberator",
    "terran-raven": "raven",
    "terran-banshee": "banshee",
    "terran-battlecruiser": "battlecruiser",
    "terran-mule": "mule",

    # Protoss units
    "protoss-probe": "probe",
    "protoss-zealot": "zealot",
    "protoss-stalker": "stalker",
    "protoss-sentry": "sentry",
    "protoss-adept": "adept",
    "protoss-high_templar": "hightemplar",  # Note: no underscore
    "protoss-dark_templar": "darktemplar",  # Note: no underscore
    "protoss-archon": "archon",
    "protoss-immortal": "immortal",
    "protoss-colossus": "colossus",
    "protoss-disruptor": "disruptor",
    "protoss-observer": "observer",
    "protoss-warp_prism": "warpprism",  # Note: no underscore
    "protoss-phoenix": "phoenix",
    "protoss-void_ray": "voidray",  # Note: no underscore
    "protoss-oracle": "oracle",
    "protoss-tempest": "tempest",
    "protoss-carrier": "carrier",
    "protoss-mothership": "mothership",

    # Zerg units
    "zerg-drone": "drone",
    "zerg-overlord": "overlord",
    "zerg-overseer": "overseer",
    "zerg-zergling": "zergling",
    "zerg-baneling": "baneling",
    "zerg-roach": "roach",
    "zerg-ravager": "ravager",
    "zerg-hydralisk": "hydralisk",
    "zerg-lurker": "lurker",
    "zerg-infestor": "infestor",
    "zerg-swarm_host": "swarmhost",  # Note: no underscore
    "zerg-ultralisk": "ultralisk",
    "zerg-queen": "queen",
    "zerg-mutalisk": "mutalisk",
    "zerg-corruptor": "corruptor",
    "zerg-brood_lord": "broodlord",  # Note: no underscore
    "zerg-broodling": "broodling",
    "zerg-viper": "viper",
    "zerg-changeling": "changeling",
    "zerg-locust": "locust",
}


def get_liquipedia_image_url(unit_id: str) -> Optional[str]:
    """Get the image URL for a unit from Liquipedia."""

    liquipedia_name = UNIT_NAME_MAPPING.get(unit_id)
    if not liquipedia_name:
        console.print(f"[yellow]No mapping for {unit_id}[/yellow]")
        return None

    race = unit_id.split("-")[0]

    # Fetch the Liquipedia units page to get the actual image URLs
    units_page_url = "https://liquipedia.net/starcraft2/Units_(Legacy_of_the_Void)"

    try:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(units_page_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Look for the specific unit image
            # The pattern is: Techtree-unit-[race]-[unit].png
            image_filename = f"Techtree-unit-{race}-{liquipedia_name}.png"

            # Find image tags with this filename
            img_tag = soup.find("img", attrs={"alt": lambda x: x and image_filename in x if x else False})
            if not img_tag:
                # Try to find by src
                img_tag = soup.find("img", attrs={"src": lambda x: x and liquipedia_name in x.lower() if x else False})

            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]

                # Convert to full URL if needed
                if img_url.startswith("/"):
                    img_url = f"https://liquipedia.net{img_url}"

                # Get a higher resolution version (50px instead of 25px)
                if "25px-" in img_url:
                    img_url = img_url.replace("25px-", "50px-")

                return img_url

    except Exception as e:
        console.print(f"[red]Error fetching Liquipedia page: {e}[/red]")

    # If we couldn't find it on the page, try constructing the URL directly
    # This is a fallback - the actual URLs have hash directories we don't know
    console.print(f"[yellow]Could not find image for {unit_id} on Liquipedia page[/yellow]")
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


def fetch_all_image_urls() -> dict:
    """Fetch all unit image URLs from Liquipedia in one go."""

    console.print("[cyan]Fetching all image URLs from Liquipedia...[/cyan]")
    units_page_url = "https://liquipedia.net/starcraft2/Units_(Legacy_of_the_Void)"

    image_urls = {}

    try:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(units_page_url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all unit images
            unit_images = soup.find_all("img", attrs={
                "src": lambda x: x and "Techtree-unit-" in x if x else False
            })

            for img in unit_images:
                src = img.get("src", "")

                # Extract unit info from filename
                # Pattern: Techtree-unit-[race]-[unit].png
                if "Techtree-unit-" in src:
                    parts = src.split("Techtree-unit-")[-1].split(".png")[0]
                    if "-" in parts:
                        race_unit = parts.split("-", 1)
                        if len(race_unit) == 2:
                            race, unit_name = race_unit

                            # Find matching unit ID
                            for unit_id, mapped_name in UNIT_NAME_MAPPING.items():
                                if unit_id.startswith(race) and mapped_name == unit_name:
                                    # Convert to full URL
                                    full_url = src if src.startswith("http") else f"https://liquipedia.net{src}"

                                    # Get higher resolution
                                    if "25px-" in full_url:
                                        full_url = full_url.replace("25px-", "50px-")

                                    image_urls[unit_id] = full_url
                                    console.print(f"[green]Found URL for {unit_id}[/green]")
                                    break

    except Exception as e:
        console.print(f"[red]Error fetching Liquipedia page: {e}[/red]")

    return image_urls


def main():
    """Download all unit images from Liquipedia."""

    # Load units data
    units_file = Path("data/units.json")
    units_data = json.loads(units_file.read_text())

    # Filter for actual units only (not buildings, upgrades, abilities)
    units = [u for u in units_data if u["type"] == "unit"]

    console.print(f"[green]Found {len(units)} units to download images for[/green]")

    # Create output directory
    output_dir = Path("visualization/public/assets/units")
    output_dir.mkdir(parents=True, exist_ok=True)

    # First, fetch all image URLs from Liquipedia
    image_urls = fetch_all_image_urls()
    console.print(f"[cyan]Found {len(image_urls)} image URLs on Liquipedia[/cyan]")

    # Track successful downloads
    downloaded = 0
    failed = []

    for unit in track(units, description="Downloading unit images..."):
        unit_id = unit["id"]

        # Output filename
        output_path = output_dir / f"{unit_id}.png"

        # Skip if already downloaded
        if output_path.exists():
            console.print(f"[dim]Skipping {unit_id} (already exists)[/dim]")
            downloaded += 1
            continue

        # Get image URL
        img_url = image_urls.get(unit_id)

        if img_url:
            if download_image(img_url, output_path):
                console.print(f"[green]✓[/green] Downloaded {unit_id}")
                downloaded += 1
            else:
                failed.append(unit_id)
        else:
            console.print(f"[yellow]No image URL found for {unit_id}[/yellow]")
            failed.append(unit_id)

        # Be polite to the server
        time.sleep(0.2)

    # Summary
    console.print("\n[bold]Download Summary:[/bold]")
    console.print(f"[green]Successfully downloaded: {downloaded}/{len(units)}[/green]")

    if failed:
        console.print(f"[red]Failed to download {len(failed)} units:[/red]")
        for unit_id in failed[:10]:  # Show first 10
            console.print(f"  - {unit_id}")
        if len(failed) > 10:
            console.print(f"  ... and {len(failed) - 10} more")

    # List unmapped units
    unmapped = [u["id"] for u in units if u["id"] not in UNIT_NAME_MAPPING]
    if unmapped:
        console.print(f"\n[yellow]Units without mapping ({len(unmapped)}):[/yellow]")
        for unit_id in unmapped:
            console.print(f"  - {unit_id}")


if __name__ == "__main__":
    main()