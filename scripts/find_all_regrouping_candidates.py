"""Find all entities that should potentially be regrouped but aren't."""

import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


# Known unit/building parent entities
KNOWN_PARENTS = {
    # Terran
    "raven", "ghost", "hellbat", "liberator", "cyclone", "thor", "widow_mine",
    "marine", "marauder", "reaper", "battlecruiser", "banshee", "medivac",
    "siege_tank", "viking", "ghost_academy", "engineering_bay", "armory",
    "barracks", "factory", "starport", "command_center", "orbital_command",
    "planetary_fortress", "nexus",

    # Protoss
    "stalker", "zealot", "adept", "sentry", "high_templar", "dark_templar",
    "archon", "immortal", "colossus", "disruptor", "warp_prism", "observer",
    "phoenix", "void_ray", "oracle", "tempest", "carrier", "mothership",
    "nexus", "gateway", "cybernetics_core", "forge", "twilight_council",
    "templar_archives", "dark_shrine", "robotics_facility", "robotics_bay",
    "stargate", "fleet_beacon",

    # Zerg
    "zergling", "baneling", "roach", "ravager", "hydralisk", "lurker",
    "mutalisk", "corruptor", "brood_lord", "swarm_host", "infestor",
    "viper", "ultralisk", "queen", "overlord", "overseer",
    "hatchery", "lair", "hive", "spawning_pool", "roach_warren",
    "baneling_nest", "evolution_chamber", "hydralisk_den", "lurker_den",
    "spire", "greater_spire", "infestation_pit", "ultralisk_cavern",
    "nydus_network"
}


def extract_entity_name(entity_id: str) -> str:
    """Extract entity name without race prefix."""
    parts = entity_id.split("-", 1)
    if len(parts) == 2:
        return parts[1]
    return entity_id


def find_potential_parent(entity_name: str) -> str | None:
    """Find potential parent for an entity based on name patterns."""
    name_lower = entity_name.lower()

    # Direct match with known parents
    if name_lower in KNOWN_PARENTS:
        return None  # Already a parent

    # Check for ability/upgrade patterns
    for parent in KNOWN_PARENTS:
        # Check if entity name contains parent name
        if parent in name_lower:
            return parent

        # Check for specific patterns
        if "cloaking" in name_lower or "cloak" in name_lower:
            if "ghost" in name_lower or "personal" in name_lower:
                return "ghost"
            if "banshee" in name_lower:
                return "banshee"

        if "recall" in name_lower:
            return "nexus"

        if "muscular" in name_lower or "grooved" in name_lower:
            return "hydralisk"

        if "hi_sec" in name_lower or "tracking" in name_lower:
            if "auto" in name_lower:
                return "raven"

    return None


def main():
    """Find all potential regrouping candidates."""
    patches_dir = Path("data/processed/patches")
    existing_rules_file = Path("data/entity_regrouping_rules.json")

    # Load existing rules
    with open(existing_rules_file) as f:
        existing_rules = json.load(f)

    console.print(f"[bold]Loaded {len(existing_rules)} existing regrouping rules[/bold]\n")

    # Find all entities
    all_entities = defaultdict(lambda: {"patches": [], "count": 0})

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        for change in data["changes"]:
            entity_id = change["entity_id"]
            entity_name = extract_entity_name(entity_id)

            all_entities[entity_id]["count"] += 1
            if data["metadata"]["version"] not in all_entities[entity_id]["patches"]:
                all_entities[entity_id]["patches"].append(data["metadata"]["version"])

    # Find candidates
    candidates = []

    for entity_id, info in all_entities.items():
        entity_name = extract_entity_name(entity_id)

        # Skip if already in rules
        if entity_id in existing_rules:
            continue

        # Skip if it's a known parent
        if entity_name in KNOWN_PARENTS:
            continue

        # Find potential parent
        parent_name = find_potential_parent(entity_name)

        if parent_name:
            race = entity_id.split("-")[0]
            parent_id = f"{race}-{parent_name}"

            candidates.append({
                "entity_id": entity_id,
                "entity_name": entity_name,
                "parent_id": parent_id,
                "count": info["count"],
                "patches": info["patches"]
            })

    # Display results
    if candidates:
        console.print(f"[yellow]Found {len(candidates)} potential regrouping candidates:[/yellow]\n")

        # Group by race
        by_race = defaultdict(list)
        for candidate in candidates:
            race = candidate["entity_id"].split("-")[0]
            by_race[race].append(candidate)

        for race in ["terran", "protoss", "zerg"]:
            if race not in by_race:
                continue

            items = sorted(by_race[race], key=lambda x: -x["count"])

            console.print(f"\n[cyan]{'='*100}[/cyan]")
            console.print(f"[bold cyan]{race.upper()}[/bold cyan] - {len(items)} candidates\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Entity ID", style="yellow", width=40)
            table.add_column("Should go to", style="green", width=30)
            table.add_column("Uses", justify="right")
            table.add_column("Patches", style="dim")

            for item in items:
                patches_str = ", ".join(item["patches"][:3])
                if len(item["patches"]) > 3:
                    patches_str += f" +{len(item['patches'])-3} more"

                table.add_row(
                    item["entity_id"],
                    item["parent_id"],
                    str(item["count"]),
                    patches_str
                )

            console.print(table)
    else:
        console.print("[green]No new regrouping candidates found![/green]")

    # Save candidates
    if candidates:
        output_file = Path("data/regrouping_candidates.json")
        with open(output_file, "w") as f:
            json.dump(candidates, f, indent=2)
        console.print(f"\n[green]✓ Saved {len(candidates)} candidates to {output_file}[/green]")


if __name__ == "__main__":
    main()
