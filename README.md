# StarCraft II Balance Patch Analyzer

Extract, parse, and visualize StarCraft II balance patch changes using a clean 4-stage pipeline.

## Features

- 🚀 **4-stage pipeline**: Download → Parse → Validate → Export
- 🤖 **GPT-5 powered parsing**: Accurate extraction of balance changes
- ✅ **Hard validation**: Fail fast with clear errors
- 📊 **Interactive visualization**: React-based patch history browser
- 📝 **Timestamped logs**: Debug-friendly markdown logs for every run
- 🎯 **Single source of truth**: Only `data/patch_urls.json` is manually edited

## Installation

```bash
uv sync
```

**API Keys:** Create a `.env` file with:
```
OPENROUTER_API_KEY=your-key-here
```

## Quick Start

```bash
# 1. Download patches
uv run python scripts/1_download.py

# 2. Parse with GPT-5 (uses OPENROUTER_API_KEY from .env)
uv run python scripts/2_parse.py

# 3. Validate
uv run python scripts/3_validate.py

# 4. Export for visualization
uv run python scripts/4_export_for_viz.py

# 5. Run visualization
cd visualization
pnpm install
pnpm dev  # Visit http://localhost:5173
```

## Tech Tree and Images

The project includes a complete StarCraft II tech tree and unit/building images:

```bash
# Extract tech tree from Liquipedia (already done, generates data/tech_tree.json)
uv run python scripts/parse_tech_tree.py

# Download all unit/building images (191 images from tech tree icons)
uv run python scripts/download_images_from_tech_tree.py
```

- **Tech tree**: 203 entities (units, buildings, upgrades) with dependencies
- **Images**: 203 tech tree icons (50×50 for units, 76×76 for buildings)
- **Sources**: Liquipedia tech tree, manually added for special units
- **Documentation**: See `visualization/public/assets/units/README.md`

## Pipeline Stages

### Stage 1: Download
**Script:** `scripts/1_download.py`

Downloads HTML from Blizzard News and converts to Markdown for review.

```bash
uv run python scripts/1_download.py              # Download all
uv run python scripts/1_download.py --skip-existing  # Skip existing
```

**Outputs:**
- `data/raw_html/{version}.html` - Raw HTML for parsing
- `data/raw_patches/{version}.md` - Human-readable Markdown
- `data/logs/YYYY-MM-DD-HH-MM-download.md` - Execution log

### Stage 2: Parse
**Script:** `scripts/2_parse.py`

Extracts structured balance changes using GPT-5 via OpenRouter.

```bash
uv run python scripts/2_parse.py              # Parse all
uv run python scripts/2_parse.py --skip-existing  # Skip existing
uv run python scripts/2_parse.py 5.0.15       # Parse specific version
```

**Requires:** `OPENROUTER_API_KEY` environment variable

**Outputs:**
- `data/processed/patches/{version}.json` - Structured patch data
- `data/logs/YYYY-MM-DD-HH-MM-parse.md` - Execution log

### Stage 3: Validate
**Script:** `scripts/3_validate.py`

Validates all processed patches for completeness and correctness.

```bash
uv run python scripts/3_validate.py
```

**Outputs:**
- `data/logs/YYYY-MM-DD-HH-MM-validate.md` - Validation report
- Exit code 0 if valid, 1 if failures

### Stage 4: Export
**Script:** `scripts/4_export_for_viz.py`

Copies processed data to visualization directory.

```bash
uv run python scripts/4_export_for_viz.py
```

**Outputs:**
- `visualization/public/data/processed/patches/*.json` - Patch files
- `visualization/public/data/units.json` - Units reference
- `visualization/public/data/patches_manifest.json` - Patch index
- `data/logs/YYYY-MM-DD-HH-MM-export.md` - Execution log

## Data Format

Each patch is stored as a JSON file with this structure:

```json
{
  "metadata": {
    "version": "5.0.9",
    "date": "2022-03-08",
    "title": "StarCraft II Patch 5.0.9",
    "url": "https://news.blizzard.com/..."
  },
  "changes": [
    {
      "id": "protoss-void_ray_0",
      "patch_version": "5.0.9",
      "entity_id": "protoss-void_ray",
      "raw_text": "Cost increased from 200 to 250",
      "change_type": "nerf"
    }
  ]
}
```

**Change Types:**
- `buff` - Entity becomes STRONGER (cost reduced, damage increased, etc.)
- `nerf` - Entity becomes WEAKER (cost increased, damage reduced, etc.)
- `mixed` - Has both positive and negative aspects

## Project Structure

```
sc2patches/
├── scripts/
│   ├── 1_download.py         # Stage 1: Download patches
│   ├── 2_parse.py            # Stage 2: Parse with GPT-5
│   ├── 3_validate.py         # Stage 3: Validate data
│   └── 4_export_for_viz.py   # Stage 4: Export for visualization
├── src/sc2patches/
│   ├── logger.py             # Timestamped markdown logging
│   ├── download.py           # Download & convert logic
│   └── parse.py              # GPT-5 parsing logic
├── data/
│   ├── patch_urls.json       # ← ONLY manually edited file
│   ├── logs/                 # Timestamped execution logs
│   ├── raw_html/             # Downloaded HTML
│   ├── raw_patches/          # Human-readable Markdown
│   └── processed/patches/    # Final JSON data
└── visualization/            # React + Vite visualization
    ├── src/
    └── public/data/          # Exported data (copies from data/)
```

## Adding New Patches

1. Find patch URL on Blizzard News or Liquipedia
2. Add URL to `data/patch_urls.json`
3. Run pipeline:
   ```bash
   uv run python scripts/1_download.py
   uv run python scripts/2_parse.py {version}
   uv run python scripts/3_validate.py
   uv run python scripts/4_export_for_viz.py
   ```
4. Check logs for any issues: `ls -lt data/logs/`
5. Commit changes

## Development

### Format and Check Code

```bash
# Python
uv run ruff format .
uv run ruff check .
uv run ty check src/

# TypeScript (in visualization/)
cd visualization
pnpm lint
pnpm type-check
```

### Run Visualization

```bash
cd visualization
pnpm install
pnpm dev          # Development server
pnpm build        # Production build
```

## Design Philosophy

- **Fail fast, fail loud** - No silent failures or defensive programming
- **Single source of truth** - Only `data/patch_urls.json` is manually defined
- **Timestamped logs** - Every run generates a markdown log for debugging
- **Hard validation** - Missing data causes immediate failures
- **Type safety** - Pydantic models for Python, TypeScript for visualization

## Current Coverage

42 patches spanning:
- **Wings of Liberty** (1.x): 8 patches
- **Heart of the Swarm** (2.x): 7 patches
- **Legacy of the Void** (3.x-4.x): 19 patches
- **Legacy of the Void II** (5.x): 8 patches

## Documentation

- **[PIPELINE.md](PIPELINE.md)** - Detailed pipeline documentation
- **[CLAUDE.md](CLAUDE.md)** - Project guidelines and conventions

## Troubleshooting

**Download fails with 404:**
- URL may be dead → check Liquipedia or Web Archive

**Parse returns empty:**
- Check `OPENROUTER_API_KEY` is set
- Check OpenRouter API status
- Retry the specific patch

**Validation fails:**
- Check the error in logs: `ls -lt data/logs/`
- Re-parse that patch: `uv run python scripts/2_parse.py {version}`

**Visualization doesn't load:**
- Run stage 4: `uv run python scripts/4_export_for_viz.py`
- Check `visualization/public/data/` has patch files

## License

MIT
