"""Download building images by scraping Liquipedia wiki pages."""

import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track
import time

console = Console()

# Buildings to download (entity_id -> wiki page name)
BUILDINGS = {
    # Terran
    "terran-command_center": "Command_Center_(Legacy_of_the_Void)",
    "terran-orbital_command": "Orbital_Command",
    "terran-planetary_fortress": "Planetary_Fortress",
    "terran-supply_depot": "Supply_Depot_(Legacy_of_the_Void)",
    "terran-refinery": "Refinery_(Legacy_of_the_Void)",
    "terran-barracks": "Barracks_(Legacy_of_the_Void)",
    "terran-engineering_bay": "Engineering_Bay_(Legacy_of_the_Void)",
    "terran-missile_turret": "Missile_Turret_(Legacy_of_the_Void)",
    "terran-bunker": "Bunker_(Legacy_of_the_Void)",
    "terran-sensor_tower": "Sensor_Tower",
    "terran-factory": "Factory_(Legacy_of_the_Void)",
    "terran-armory": "Armory_(Legacy_of_the_Void)",
    "terran-starport": "Starport_(Legacy_of_the_Void)",
    "terran-fusion_core": "Fusion_Core",
    "terran-ghost_academy": "Ghost_Academy",

    # Protoss
    "protoss-nexus": "Nexus_(Legacy_of_the_Void)",
    "protoss-pylon": "Pylon_(Legacy_of_the_Void)",
    "protoss-assimilator": "Assimilator_(Legacy_of_the_Void)",
    "protoss-gateway": "Gateway_(Legacy_of_the_Void)",
    "protoss-warpgate": "Warp_Gate",
    "protoss-forge": "Forge_(Legacy_of_the_Void)",
    "protoss-photon_cannon": "Photon_Cannon_(Legacy_of_the_Void)",
    "protoss-cybernetics_core": "Cybernetics_Core_(Legacy_of_the_Void)",
    "protoss-twilight_council": "Twilight_Council",
    "protoss-templar_archives": "Templar_Archives",
    "protoss-dark_shrine": "Dark_Shrine_(Legacy_of_the_Void)",
    "protoss-robotics_facility": "Robotics_Facility_(Legacy_of_the_Void)",
    "protoss-robotics_bay": "Robotics_Bay",
    "protoss-stargate": "Stargate_(Legacy_of_the_Void)",
    "protoss-fleet_beacon": "Fleet_Beacon",
    "protoss-shield_battery": "Shield_Battery",

    # Zerg
    "zerg-hatchery": "Hatchery_(Legacy_of_the_Void)",
    "zerg-lair": "Lair_(Legacy_of_the_Void)",
    "zerg-hive": "Hive_(Legacy_of_the_Void)",
    "zerg-extractor": "Extractor_(Legacy_of_the_Void)",
    "zerg-spawning_pool": "Spawning_Pool_(Legacy_of_the_Void)",
    "zerg-evolution_chamber": "Evolution_Chamber_(Legacy_of_the_Void)",
    "zerg-spine_crawler": "Spine_Crawler_(Legacy_of_the_Void)",
    "zerg-spore_crawler": "Spore_Crawler_(Legacy_of_the_Void)",
    "zerg-roach_warren": "Roach_Warren",
    "zerg-baneling_nest": "Baneling_Nest",
    "zerg-hydralisk_den": "Hydralisk_Den",
    "zerg-lurker_den": "Lurker_Den",
    "zerg-infestation_pit": "Infestation_Pit",
    "zerg-spire": "Spire_(Legacy_of_the_Void)",
    "zerg-greater_spire": "Greater_Spire",
    "zerg-nydus_network": "Nydus_Network",
    "zerg-ultralisk_cavern": "Ultralisk_Cavern",
}


def download_building_image(entity_id: str, wiki_name: str, output_dir: Path) -> bool:
    """Download building image from Liquipedia wiki page."""

    url = f"https://liquipedia.net/starcraft2/{wiki_name}"

    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the first image that looks like a building render
        # These are usually in the upper section of the page
        imgs = soup.find_all('img', limit=20)

        img_url = None
        for img in imgs:
            src = img.get('src', '')
            # Look for SC2 building images (not icons, not tech tree thumbnails)
            if '/commons/images/' in src and ('SC2' in src or 'Techtree' in src):
                # Skip small thumbnails
                if 'thumb' in src and ('600px' in src or '800px' in src or '400px' in src):
                    img_url = src
                    break
                elif 'thumb' not in src:  # Full size image
                    img_url = src
                    break

        if not img_url:
            console.print(f"[yellow]⚠[/yellow] {entity_id}: No building image found")
            return False

        if not img_url.startswith('http'):
            img_url = 'https://liquipedia.net' + img_url

        # Download the image
        img_response = httpx.get(img_url, follow_redirects=True, timeout=30)
        img_response.raise_for_status()

        output_path = output_dir / f"{entity_id}.png"
        output_path.write_bytes(img_response.content)

        console.print(f"[green]✓[/green] {entity_id}")
        return True

    except Exception as e:
        console.print(f"[red]✗[/red] {entity_id}: {e}")
        return False


def main():
    """Download all building images."""
    output_dir = Path("visualization/public/assets/units")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Downloading {len(BUILDINGS)} building images from Liquipedia...[/bold]\n")

    successful = 0
    failed = 0

    for entity_id, wiki_name in track(list(BUILDINGS.items()), description="Downloading..."):
        if download_building_image(entity_id, wiki_name, output_dir):
            successful += 1
        else:
            failed += 1

        # Rate limiting
        time.sleep(0.5)

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓ Downloaded: {successful}[/green]")
    console.print(f"[red]✗ Failed: {failed}[/red]")


if __name__ == "__main__":
    main()
