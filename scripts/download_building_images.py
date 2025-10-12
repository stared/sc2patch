"""Download building images from Liquipedia."""
from pathlib import Path
import httpx
from rich.console import Console

console = Console()

# Buildings that commonly appear in patch notes
buildings = {
    # Terran buildings
    "terran-command_center": "https://liquipedia.net/commons/images/6/6d/Techtree-building-terran-commandcenter.png",
    "terran-supply_depot": "https://liquipedia.net/commons/images/3/3c/Techtree-building-terran-supplydepot.png",
    "terran-refinery": "https://liquipedia.net/commons/images/e/e2/Techtree-building-terran-refinery.png",
    "terran-barracks": "https://liquipedia.net/commons/images/c/c5/Techtree-building-terran-barracks.png",
    "terran-factory": "https://liquipedia.net/commons/images/7/75/Techtree-building-terran-factory.png",
    "terran-starport": "https://liquipedia.net/commons/images/1/18/Techtree-building-terran-starport.png",
    "terran-engineering_bay": "https://liquipedia.net/commons/images/6/69/Techtree-building-terran-engineeringbay.png",
    "terran-armory": "https://liquipedia.net/commons/images/5/59/Techtree-building-terran-armory.png",
    "terran-fusion_core": "https://liquipedia.net/commons/images/6/6e/Techtree-building-terran-fusioncore.png",
    
    # Protoss buildings
    "protoss-nexus": "https://liquipedia.net/commons/images/1/18/Techtree-building-protoss-nexus.png",
    "protoss-pylon": "https://liquipedia.net/commons/images/6/60/Techtree-building-protoss-pylon.png",
    "protoss-assimilator": "https://liquipedia.net/commons/images/6/60/Techtree-building-protoss-assimilator.png",
    "protoss-gateway": "https://liquipedia.net/commons/images/c/c5/Techtree-building-protoss-gateway.png",
    "protoss-forge": "https://liquipedia.net/commons/images/1/1c/Techtree-building-protoss-forge.png",
    "protoss-cybernetics_core": "https://liquipedia.net/commons/images/1/14/Techtree-building-protoss-cyberneticscore.png",
    "protoss-robotics_facility": "https://liquipedia.net/commons/images/e/e0/Techtree-building-protoss-roboticsfacility.png",
    "protoss-stargate": "https://liquipedia.net/commons/images/7/78/Techtree-building-protoss-stargate.png",
    "protoss-twilight_council": "https://liquipedia.net/commons/images/0/03/Techtree-building-protoss-twilightcouncil.png",
    "protoss-templar_archives": "https://liquipedia.net/commons/images/a/ad/Techtree-building-protoss-templararchives.png",
    "protoss-dark_shrine": "https://liquipedia.net/commons/images/f/f0/Techtree-building-protoss-darkshrine.png",
    "protoss-robotics_bay": "https://liquipedia.net/commons/images/2/24/Techtree-building-protoss-roboticsbay.png",
    "protoss-fleet_beacon": "https://liquipedia.net/commons/images/d/da/Techtree-building-protoss-fleetbeacon.png",
    
    # Zerg buildings
    "zerg-hatchery": "https://liquipedia.net/commons/images/5/52/Techtree-building-zerg-hatchery.png",
    "zerg-lair": "https://liquipedia.net/commons/images/f/f3/Techtree-building-zerg-lair.png",
    "zerg-hive": "https://liquipedia.net/commons/images/3/3c/Techtree-building-zerg-hive.png",
    "zerg-extractor": "https://liquipedia.net/commons/images/5/51/Techtree-building-zerg-extractor.png",
    "zerg-spawning_pool": "https://liquipedia.net/commons/images/d/dd/Techtree-building-zerg-spawningpool.png",
    "zerg-roach_warren": "https://liquipedia.net/commons/images/1/16/Techtree-building-zerg-roachwarren.png",
    "zerg-baneling_nest": "https://liquipedia.net/commons/images/b/b8/Techtree-building-zerg-banelingnest.png",
    "zerg-hydralisk_den": "https://liquipedia.net/commons/images/4/47/Techtree-building-zerg-hydraliskden.png",
    "zerg-spire": "https://liquipedia.net/commons/images/1/14/Techtree-building-zerg-spire.png",
    "zerg-greater_spire": "https://liquipedia.net/commons/images/3/32/Techtree-building-zerg-greaterspire.png",
    "zerg-infestation_pit": "https://liquipedia.net/commons/images/d/d2/Techtree-building-zerg-infestationpit.png",
    "zerg-ultralisk_cavern": "https://liquipedia.net/commons/images/3/38/Techtree-building-zerg-ultraliskcavern.png",
    "zerg-evolution_chamber": "https://liquipedia.net/commons/images/1/16/Techtree-building-zerg-evolutionchamber.png",
    "zerg-spine_crawler": "https://liquipedia.net/commons/images/1/1a/Techtree-building-zerg-spinecrawler.png",
    "zerg-spore_crawler": "https://liquipedia.net/commons/images/1/1f/Techtree-building-zerg-sporecrawler.png",
    "zerg-lurker_den": "https://liquipedia.net/commons/images/7/7e/Techtree-building-zerg-lurkerden.png",
}

def main():
    output_dir = Path("visualization/public/assets/units")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\n[bold]Downloading {len(buildings)} building images...[/bold]\n")
    
    successful = 0
    failed = []
    
    for building_id, url in buildings.items():
        output_path = output_dir / f"{building_id}.png"
        
        if output_path.exists():
            console.print(f"[yellow]⊙[/yellow] {building_id} (already exists)")
            successful += 1
            continue
        
        try:
            response = httpx.get(url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            
            output_path.write_bytes(response.content)
            console.print(f"[green]✓[/green] {building_id}")
            successful += 1
            
        except Exception as e:
            console.print(f"[red]✗[/red] {building_id}: {e}")
            failed.append((building_id, str(e)))
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully downloaded: {successful}/{len(buildings)}[/green]")
    
    if failed:
        console.print(f"\n[red]Failed: {len(failed)}[/red]")
        for building_id, error in failed:
            console.print(f"  • {building_id}: {error[:60]}...")

if __name__ == "__main__":
    main()
