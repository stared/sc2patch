"""Create entity regrouping rules for child entities (upgrades, abilities) to parent entities."""

import json
from pathlib import Path

from rich.console import Console

console = Console()


# Define regrouping rules: child entity -> parent entity
REGROUPING_RULES = {
    # Swarm Host and its related entities
    "zerg-locust": "zerg-swarm_host",
    "zerg-spawn_locusts": "zerg-swarm_host",
    "zerg-flying_locusts": "zerg-swarm_host",
    "zerg-enduring_locusts": "zerg-swarm_host",

    # Protoss Forge upgrades
    "protoss-shields_level_1": "protoss-forge",
    "protoss-shields_level_2": "protoss-forge",
    "protoss-shields_level_3": "protoss-forge",
    "protoss-ground_weapons_level_1": "protoss-forge",
    "protoss-ground_weapons_level_2": "protoss-forge",
    "protoss-ground_weapons_level_3": "protoss-forge",
    "protoss-ground_armor_level_1": "protoss-forge",
    "protoss-ground_armor_level_2": "protoss-forge",
    "protoss-ground_armor_level_3": "protoss-forge",

    # Orbital Command (naming inconsistency fix)
    "terran-orbital_command_center": "terran-orbital_command",

    # Hellbat and its upgrade
    "terran-infernal_pre_igniter": "terran-hellbat",

    # Ghost and its upgrades
    "terran-moebius_reactor": "terran-ghost",
    "terran-cloaking_field": "terran-ghost",  # Ghost cloak upgrade
    "terran-personal_cloaking": "terran-ghost",  # Personal Cloaking upgrade

    # Engineering Bay upgrades
    "terran-hi_sec_auto_tracking": "terran-engineering_bay",

    # Nydus (merge worm into network)
    "zerg-nydus_worm": "zerg-nydus_network",

    # Other Terran upgrades to their buildings
    "terran-drilling_claws": "terran-widow_mine",  # Widow Mine upgrade
    "terran-rapid_fire_launchers": "terran-cyclone",  # Cyclone upgrade
    "terran-smart_servos": "terran-thor",  # Thor upgrade
    "terran-mag_field_launchers": "terran-cyclone",  # Another Cyclone upgrade
    "terran-enhanced_munitions": "terran-liberator",  # Liberator upgrade

    # Protoss Nexus abilities
    "protoss-mass_recall": "protoss-nexus",
    "protoss-strategic_recall": "protoss-nexus",

    # Zerg Hydralisk upgrades
    "zerg-evolve_grooved_spines": "zerg-hydralisk",
    "zerg-muscular_augments": "zerg-hydralisk",
    "zerg-grooved_spines": "zerg-hydralisk",
    "zerg-mutate_ventral_sacs": "zerg-overlord",
}


def main():
    """Display and save regrouping rules."""
    console.print("[bold]Entity Regrouping Rules[/bold]\n")
    console.print("Child entities will be merged into their parent entities:\n")

    # Group by parent
    by_parent = {}
    for child, parent in REGROUPING_RULES.items():
        if parent not in by_parent:
            by_parent[parent] = []
        by_parent[parent].append(child)

    for parent in sorted(by_parent.keys()):
        children = by_parent[parent]
        console.print(f"[cyan]{parent}[/cyan]")
        for child in sorted(children):
            console.print(f"  ← {child}")
        console.print()

    # Save rules to JSON
    output_file = Path("data/entity_regrouping_rules.json")
    with open(output_file, "w") as f:
        json.dump(REGROUPING_RULES, f, indent=2)

    console.print(f"[green]✓ Saved {len(REGROUPING_RULES)} regrouping rules to {output_file}[/green]")
    console.print(f"\n[bold]Total:[/bold] {len(set(REGROUPING_RULES.values()))} parent entities")
    console.print(f"[bold]Total:[/bold] {len(REGROUPING_RULES)} child entities to regroup")


if __name__ == "__main__":
    main()
