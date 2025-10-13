"""Find all entities used in patches that are missing from units.json."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


def extract_race_from_id(entity_id: str) -> str:
    """Extract race from entity_id prefix."""
    if entity_id.startswith("terran-"):
        return "terran"
    elif entity_id.startswith("protoss-"):
        return "protoss"
    elif entity_id.startswith("zerg-"):
        return "zerg"
    elif entity_id.startswith("neutral-"):
        return "neutral"
    else:
        return "unknown"


def infer_type(entity_id: str) -> str:
    """Infer entity type from name patterns."""
    name = entity_id.lower()

    # Buildings
    building_keywords = [
        "nexus", "gateway", "forge", "cybernetics", "twilight", "templar",
        "dark_shrine", "robotics", "stargate", "fleet_beacon", "pylon",
        "assimilator", "photon_cannon", "shield_battery",
        "command_center", "supply_depot", "refinery", "barracks", "factory",
        "starport", "engineering_bay", "missile_turret", "sensor_tower",
        "bunker", "fusion_core", "armory", "ghost_academy", "tech_lab",
        "reactor", "planetary_fortress", "orbital_command",
        "hatchery", "spawning_pool", "evolution_chamber", "roach_warren",
        "baneling_nest", "spine_crawler", "spore_crawler", "lair", "hive",
        "hydralisk_den", "lurker_den", "infestation_pit", "spire",
        "greater_spire", "nydus", "ultralisk_cavern", "extractor"
    ]

    # Upgrades
    upgrade_keywords = [
        "upgrade", "weapons", "armor", "shields", "attack", "carapace",
        "level_1", "level_2", "level_3", "research", "stimpack", "combat_shield",
        "concussive_shells", "hi_sec", "neosteel", "building_armor",
        "melee_attacks", "ground_weapons", "air_weapons", "ground_armor",
        "air_armor", "vehicle_weapons", "vehicle_plating", "ship_weapons",
        "ship_plating", "infantry_weapons", "infantry_armor", "missile_attacks",
        "metabolic_boost", "adrenal_glands", "centrifugal_hooks",
        "glial_reconstitution", "tunneling_claws", "chitinous_plating",
        "grooved_spines", "muscular_augments", "pneumatized_carapace",
        "charge", "blink", "resonating_glaives", "extended_thermal_lance",
        "gravitic_drive", "graviton_catapult", "flux_vanes", "anion_pulse"
    ]

    for keyword in building_keywords:
        if keyword in name:
            return "building"

    for keyword in upgrade_keywords:
        if keyword in name:
            return "upgrade"

    # Default to unit if not clearly building or upgrade
    return "unit"


def main():
    """Find missing entities and their details."""
    patches_dir = Path("data/processed/patches")
    units_file = Path("visualization/public/data/units.json")

    # Load existing units.json
    with open(units_file) as f:
        existing_units = json.load(f)

    existing_ids = {unit["id"] for unit in existing_units}

    console.print(f"[bold]Loaded {len(existing_ids)} entities from units.json[/bold]\n")

    # Collect all entities from patches
    all_entities = defaultdict(lambda: {
        "occurrences": 0,
        "patches": [],
        "examples": []
    })

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        for change in data["changes"]:
            entity_id = change["entity_id"]
            all_entities[entity_id]["occurrences"] += 1
            all_entities[entity_id]["patches"].append(data["metadata"]["version"])

            if len(all_entities[entity_id]["examples"]) < 1:
                all_entities[entity_id]["examples"].append(change["raw_text"][:100])

    # Find missing entities
    missing_entities = []

    for entity_id, info in all_entities.items():
        if entity_id not in existing_ids:
            race = extract_race_from_id(entity_id)
            entity_type = infer_type(entity_id)

            # Create display name
            name = entity_id.replace(f"{race}-", "", 1) if race != "unknown" else entity_id
            name = name.replace("_", " ").title()

            missing_entities.append({
                "id": entity_id,
                "name": name,
                "race": race,
                "type": entity_type,
                "occurrences": info["occurrences"],
                "patches": info["patches"],
                "example": info["examples"][0] if info["examples"] else ""
            })

    # Display results
    console.print(f"[yellow]Found {len(missing_entities)} entities missing from units.json[/yellow]\n")

    if missing_entities:
        # Group by race
        by_race = defaultdict(list)
        for entity in missing_entities:
            by_race[entity["race"]].append(entity)

        for race in ["terran", "protoss", "zerg", "neutral", "unknown"]:
            if race not in by_race:
                continue

            entities = sorted(by_race[race], key=lambda x: x["occurrences"], reverse=True)

            console.print(f"\n[cyan]{'='*100}[/cyan]")
            console.print(f"[bold cyan]{race.upper()}[/bold cyan] - {len(entities)} missing entities\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Entity ID", style="yellow", width=40)
            table.add_column("Name", style="white", width=25)
            table.add_column("Type", style="green")
            table.add_column("Uses", style="dim", justify="right")
            table.add_column("Example", style="dim", width=40)

            for entity in entities:
                table.add_row(
                    entity["id"],
                    entity["name"],
                    entity["type"],
                    str(entity["occurrences"]),
                    entity["example"]
                )

            console.print(table)

    # Save complete list for units.json generation
    output_file = Path("data/missing_entities.json")
    with open(output_file, "w") as f:
        json.dump(missing_entities, f, indent=2)

    console.print(f"\n[green]✓ Saved missing entities to {output_file}[/green]")
    console.print(f"\n[bold]Total entities in patches: {len(all_entities)}[/bold]")
    console.print(f"[bold]In units.json: {len(existing_ids)}[/bold]")
    console.print(f"[bold red]Missing: {len(missing_entities)}[/bold red]")


if __name__ == "__main__":
    main()
