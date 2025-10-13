# SC2Patches Project Guidelines

## Code Quality

- **Python 3.12** required
- **Type hints** mandatory for all functions (checked with `ty`)
- **Formatting** with `ruff` (line length: 100)
- **Strict Pydantic models** - validate all data

## Error Handling Philosophy

- **Fail fast, fail loud** - NEVER pass errors silently
- Raise exceptions immediately on validation failures
- Use custom exceptions (e.g., `ValidationError`, `DownloadError`)
- Provide clear error messages with context
- Exit with code 1 on failures

## NO DEFENSIVE PROGRAMMING

- **CRITICAL RULE**: Do NOT add fallbacks or "if this fails, try that" patterns
- Pick ONE extraction method based on actual data inspection
- If it fails, analyze WHY and fix THAT specific issue
- ONLY add conditionals if you've VERIFIED different files have different formats
- Check actual files, don't guess or assume
- Avoid multiple fallback patterns - they hide real problems

## Module Design

- **Modular functions** - each function does one thing
- **Explicit validation** after each pipeline stage
- **Progress visibility** - use Rich for progress bars and logging
- **Type safety** - use Pydantic models for all data structures

# Remarks

- If you need to test something with a script, create a script file and run
  Run Python with `uv` - never bare `python3` or `python`.
- DO NOT edit files with `cat`

## Data Pipeline

**See PIPELINE.md for complete documentation**

The pipeline has 4 stages:

1. **Download** (`scripts/1_download.py`) - Fetch HTML from Blizzard News
2. **Parse** (`scripts/2_parse.py`) - Extract structured data with GPT-5
3. **Validate** (`scripts/3_validate.py`) - Check completeness
4. **Export** (`scripts/4_export_for_viz.py`) - Copy data to visualization

Each stage:
- Takes input from previous stage
- Generates timestamped markdown log in `data/logs/`
- Fails loudly on errors (exit code 1)

**Single source of truth:** `data/patch_urls.json` (only manually edited file)

**Quick start:**
```bash
uv run python scripts/1_download.py
export OPENROUTER_API_KEY="your-key"
uv run python scripts/2_parse.py
uv run python scripts/3_validate.py
uv run python scripts/4_export_for_viz.py
```

## Testing

### Python
Before committing:
```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/
```

### TypeScript (Visualization)
```bash
cd visualization
pnpm lint           # Run ESLint
pnpm type-check     # TypeScript checking
pnpm dev            # Start dev server (localhost:5173)
pnpm build          # Production build
```

## Project Structure

```
sc2patches/
├── PIPELINE.md              # Complete pipeline documentation
├── data/
│   ├── patch_urls.json      # ← ONLY manually edited file
│   ├── logs/                # Timestamped execution logs
│   ├── raw_html/            # Downloaded HTML
│   ├── raw_patches/         # Human-readable Markdown
│   └── processed/patches/   # Final JSON data (one per patch)
├── src/sc2patches/          # Python library
│   ├── logger.py            # Markdown log generation
│   ├── download.py          # Download & convert logic
│   └── parse.py             # GPT-5 parsing logic
├── scripts/                 # Pipeline scripts
│   ├── 1_download.py        # Stage 1: Download
│   ├── 2_parse.py           # Stage 2: Parse with GPT-5
│   ├── 3_validate.py        # Stage 3: Validate
│   └── 4_export_for_viz.py  # Stage 4: Export
├── visualization/           # React + Vite visualization
│   ├── src/                 # React components
│   └── public/data/         # Exported data (copies from data/)
└── pyproject.toml           # Python dependencies (uv)
```

## Data Format

All patches use this JSON structure:
```json
{
  "metadata": {
    "version": "5.0.9",
    "date": "2022-03-08",
    "title": "StarCraft II Patch 5.0.9",
    "url": "https://..."
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

**change_type classification:**
- `"buff"` - Entity becomes stronger (cost reduced, damage increased, etc.)
- `"nerf"` - Entity becomes weaker (cost increased, damage reduced, etc.)
- `"mixed"` - Has both positive and negative aspects

## Conventions

- Use `Path` objects, not strings for file paths
- Use `httpx` for HTTP requests
- Rich console for all user-facing output
- Run Python with `uv`, TypeScript with `pnpm`
- Hard validation: fail fast with clear errors, never silent failures
- Do not commit without an explicit confirmation. Ask for it.
- When needed, manually check Blizzard websites or Liqudidpedia, e.g. https://liquipedia.net/starcraft2/Units_(Legacy_of_the_Void) and its pages, e.g. https://liquipedia.net/starcraft2/Factory_(Legacy_of_the_Void), https://liquipedia.net/starcraft2/Stalker_(Legacy_of_the_Void) or https://liquipedia.net/starcraft2/Chitinous_Plating (to show you patters for buildings, units, upgrades). Useful websites: https://liquipedia.net/starcraft2/Upgrades and for patches - https://liquipedia.net/starcraft2/Patches.