"""Download building images from Liquipedia."""

import httpx
from pathlib import Path
from rich.console import Console
from rich.progress import track

console = Console()

# Mapping of entity IDs to Liquipedia building image names
BUILDING_IMAGES = {
    # Terran buildings
    "terran-command_center": "commandcenter",
    "terran-orbital_command": "orbitalcommand",
    "terran-planetary_fortress": "planetaryfortress",
    "terran-supply_depot": "supplydepot",
    "terran-refinery": "refinery",
    "terran-barracks": "barracks",
    "terran-engineering_bay": "engineeringbay",
    "terran-missile_turret": "missileturret",
    "terran-bunker": "bunker",
    "terran-sensor_tower": "sensortower",
    "terran-factory": "factory",
    "terran-armory": "armory",
    "terran-starport": "starport",
    "terran-fusion_core": "fusioncore",
    "terran-ghost_academy": "ghostacademy",
    "terran-tech_lab": "techlab",
    "terran-reactor": "reactor",

    # Protoss buildings
    "protoss-nexus": "nexus",
    "protoss-pylon": "pylon",
    "protoss-assimilator": "assimilator",
    "protoss-gateway": "gateway",
    "protoss-warpgate": "warpgate",
    "protoss-forge": "forge",
    "protoss-photon_cannon": "photoncannon",
    "protoss-cybernetics_core": "cyberneticscore",
    "protoss-twilight_council": "twilightcouncil",
    "protoss-templar_archives": "templararchives",
    "protoss-dark_shrine": "darkshrine",
    "protoss-robotics_facility": "roboticsfacility",
    "protoss-robotics_bay": "roboticsbay",
    "protoss-stargate": "stargate",
    "protoss-fleet_beacon": "fleetbeacon",
    "protoss-shield_battery": "shieldbattery",

    # Zerg buildings
    "zerg-hatchery": "hatchery",
    "zerg-lair": "lair",
    "zerg-hive": "hive",
    "zerg-extractor": "extractor",
    "zerg-spawning_pool": "spawningpool",
    "zerg-evolution_chamber": "evolutionchamber",
    "zerg-spine_crawler": "spinecrawler",
    "zerg-spore_crawler": "sporecrawler",
    "zerg-roach_warren": "roachwarren",
    "zerg-baneling_nest": "banelingnest",
    "zerg-hydralisk_den": "hydraliskden",
    "zerg-lurker_den": "lurkerden",
    "zerg-infestation_pit": "infestationpit",
    "zerg-spire": "spire",
    "zerg-greater_spire": "greaterspire",
    "zerg-nydus_network": "nydusnetwork",
    "zerg-nydus_worm": "nydusworm",
    "zerg-ultralisk_cavern": "ultraliskcavern",
}


def download_building_image(entity_id: str, image_name: str, output_dir: Path) -> bool:
    """Download a single building image from Liquipedia."""

    # Extract race from entity_id
    race = entity_id.split('-')[0]

    # Try the techtree format first
    url = f"https://liquipedia.net/commons/images/thumb/Techtree-building-{race}-{image_name}.png"

    # Alternate URL formats to try
    urls_to_try = [
        f"https://liquipedia.net/commons/images/thumb/Techtree-building-{race}-{image_name}.png",
        f"https://liquipedia.net/commons/images/Techtree-building-{race}-{image_name}.png",
    ]

    output_path = output_dir / f"{entity_id}.png"

    for url in urls_to_try:
        try:
            response = httpx.get(url, follow_redirects=True, timeout=30)
            response.raise_for_status()

            output_path.write_bytes(response.content)
            console.print(f"[green]✓[/green] {entity_id}")
            return True

        except httpx.HTTPError:
            continue

    console.print(f"[red]✗[/red] {entity_id}: No image found")
    return False


def main():
    """Download all building images."""
    output_dir = Path("visualization/public/assets/units")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Downloading {len(BUILDING_IMAGES)} building images...[/bold]\n")

    successful = 0
    failed = 0

    for entity_id, image_name in track(list(BUILDING_IMAGES.items()), description="Downloading..."):
        if download_building_image(entity_id, image_name, output_dir):
            successful += 1
        else:
            failed += 1

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓ Downloaded: {successful}[/green]")
    console.print(f"[red]✗ Failed: {failed}[/red]")


if __name__ == "__main__":
    main()
