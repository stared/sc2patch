#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Generate release patch files for expansion launches.

Creates patch files for WoL (1.0.0), HotS (2.0.0), and LotV (3.0.0)
with unit introduction changes.

Usage:
    uv run scripts/generate_release_patches.py
"""

import json
from pathlib import Path

# Expansion release metadata
RELEASES = {
    "1.0.0": {
        "date": "2010-07-27",
        "title": "Wings of Liberty",
        "url": "https://en.wikipedia.org/wiki/StarCraft_II:_Wings_of_Liberty",
    },
    "2.0.0": {
        "date": "2013-03-12",
        "title": "Heart of the Swarm",
        "url": "https://en.wikipedia.org/wiki/StarCraft_II:_Heart_of_the_Swarm",
    },
    "3.0.0": {
        "date": "2015-11-10",
        "title": "Legacy of the Void",
        "url": "https://en.wikipedia.org/wiki/StarCraft_II:_Legacy_of_the_Void",
    },
}

# Units introduced in each expansion (by name)
# WoL gets all units NOT in HotS or LotV lists
HOTS_UNITS = {
    "Hellbat",
    "Widow Mine",
    "Viper",
    "Swarm Host",
    "Mothership Core",
    "Oracle",
    "Tempest",
}

LOTV_UNITS = {
    "Cyclone",
    "Liberator",
    "Ravager",
    "Lurker",
    "Adept",
    "Disruptor",
}

def load_units() -> list[dict]:
    """Load units from data/units.json, filter to actual units only."""
    with open("data/units.json") as f:
        units = json.load(f)
    # Only include actual units (not upgrades, abilities, mechanics)
    return [u for u in units if u.get("type", "unit") == "unit"]


def get_expansion(unit_name: str) -> str:
    """Determine which expansion a unit was introduced in."""
    if unit_name in LOTV_UNITS:
        return "3.0.0"
    if unit_name in HOTS_UNITS:
        return "2.0.0"
    return "1.0.0"


def create_change(entity_id: str, patch_version: str, index: int) -> dict:
    """Create a change entry for unit introduction."""
    return {
        "id": f"{entity_id}_{index}",
        "patch_version": patch_version,
        "entity_id": entity_id,
        "raw_text": "Unit introduced",
        "change_type": "buff",
    }


def generate_release_patch(version: str, units: list[dict]) -> dict:
    """Generate a release patch file."""
    release = RELEASES[version]
    changes = []

    # Filter units for this expansion (units already filtered to type=unit)
    expansion_units = [u for u in units if get_expansion(u["name"]) == version]

    # Sort by race, then name for consistent ordering
    expansion_units.sort(key=lambda u: (u["race"], u["name"]))

    for i, unit in enumerate(expansion_units):
        changes.append(create_change(unit["id"], version, i))

    return {
        "metadata": {
            "version": version,
            "date": release["date"],
            "title": release["title"],
            "url": release["url"],
            "patch_type": "release",
        },
        "changes": changes,
    }


def main() -> None:
    """Generate release patch files."""
    units = load_units()
    output_dir = Path("data/processed/patches")
    output_dir.mkdir(parents=True, exist_ok=True)

    for version in RELEASES:
        patch = generate_release_patch(version, units)
        output_file = output_dir / f"{version}.json"

        with open(output_file, "w") as f:
            json.dump(patch, f, indent=2)

        unit_count = len(patch["changes"])
        print(f"Generated {output_file.name}: {unit_count} units introduced")


if __name__ == "__main__":
    main()
