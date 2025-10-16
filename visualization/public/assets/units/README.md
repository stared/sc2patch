# Unit and Building Images

This directory contains icons for StarCraft II units, buildings, and upgrades used in the patch visualization.

## Image Sources

### Automated Downloads (191 images)
Most images are automatically downloaded from Liquipedia tech tree icons using `scripts/download_images_from_tech_tree.py`:
- **Units**: 50×50 PNG from Liquipedia tech tree
- **Buildings**: 76×76 PNG from Liquipedia tech tree
- **Upgrades**: 50×50 PNG from Liquipedia tech tree
- **Source**: https://liquipedia.net/starcraft2/Units_(Legacy_of_the_Void)

### Manually Added Images

#### `zerg-broodling.png`
- **Source**: https://starcraft.fandom.com/wiki/Broodling_(StarCraft_II)
- **Reason**: Summoned unit, not in standard Liquipedia tech tree
- **File**: `50x_broodling.png` (manually downloaded and copied)

#### `protoss-mothership_core.png`
- **Source**: https://liquipedia.net/starcraft2/Units_(Heart_of_the_Swarm)
- **Reason**: Heart of the Swarm unit, removed in Legacy of the Void
- **Note**: Downloaded from HotS tech tree page

#### Neutral/Resource Images (TODO)
The following entities appear in patches but need manual icons:
- `neutral-minerals` / `neutral-mineral_field`
- `neutral-vespene_gas` / `neutral-vespene_geyser`
- `neutral-rocks` / `neutral-zerg_rocks` / `neutral-collapsible_rock_tower`
- `neutral-acceleration_zone_generator`
- `neutral-inhibitor_zone_generator`

**Potential sources**:
- https://liquipedia.net/starcraft2/Resources
- StarCraft II Wiki / Fandom

#### Special Entities
- `terran-all_units`, `protoss-all_units`, `zerg-all_units`: Meta-categories used in patch notes for race-wide changes (no visual needed)
- `zerg-creep_tumor`: Building but not in standard tech tree

### Placeholder
- `placeholder.svg`: Gray question mark, used when image is missing

## Image Specifications

- **Format**: PNG (or SVG for placeholder)
- **Naming**: `{race}-{unit_name}.png` (e.g., `terran-marine.png`)
- **Sizes**:
  - Units: 50×50 pixels
  - Buildings: 76×76 pixels
  - Upgrades: 50×50 pixels
- **Background**: Transparent
- **Style**: Tech tree icons with slight transparency/glow

## Known Issues

### Ramp Range Entity ID
The patch data uses per-race IDs like `terran-ramp`, `protoss-ramp`, `zerg-ramp` for the same change, but this should be normalized to `neutral-ramp` since it affects all races identically.

## Updating Images

To re-download all images from tech tree:
```bash
uv run python scripts/download_images_from_tech_tree.py
```

To download only missing images (skips existing):
```bash
uv run python scripts/download_images_from_tech_tree.py  # Skips files 500B-10KB
```
