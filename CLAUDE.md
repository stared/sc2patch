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

## Data Pipeline Stages

1. **Download** - Fetch patch notes from Blizzard News and Liquipedia
   - `scripts/download_all_balance_patches.py` - Download from Blizzard News
   - `scripts/download_html_from_liquipedia.py` - Download BU patches from Liquipedia

2. **Parse** - Extract structured data using GPT-5 via OpenRouter
   - `scripts/parse_with_llm_v2.py` - Parse Markdown patches with change_type classification
   - `scripts/parse_html_with_llm.py` - Parse Liquipedia HTML patches
   - **CRITICAL**: Every change MUST have `change_type` (buff/nerf/mixed)
   - Classification is from entity's perspective (stronger/weaker)

3. **Validate** - Verify data completeness
   - `scripts/reparse_missing_change_types.py` - Check all patches have change_type
   - Hard validation in visualization fails if data is incomplete

4. **Generate** - Create manifests and indices
   - `scripts/generate_patch_manifest.py` - Build manifest with all patches
   - `scripts/download_building_images_from_wiki.py` - Fetch unit/building images

Each stage must validate its inputs and outputs.

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
├── src/sc2patches/          # Python parsing library
│   ├── parsers/             # Modular HTML parsers
│   └── convert.py           # HTML to structured data conversion
├── scripts/                 # Pipeline scripts
│   ├── parse_with_llm_v2.py      # Main LLM parser
│   ├── parse_html_with_llm.py    # HTML parser for BU patches
│   └── reparse_missing_*.py      # Validation utilities
├── data/                    # Parsed data and assets
│   ├── processed/patches/   # Final JSON files (one per patch)
│   ├── patches_manifest.json # Index of all patches
│   └── raw_html/            # Downloaded HTML source
├── visualization/           # React + Vite visualization
│   ├── src/
│   │   ├── components/      # PatchGrid, PatchSelector
│   │   └── utils/           # dataLoader.ts (with hard validation)
│   ├── public/data/         # Symlinked to ../data
│   └── package.json         # pnpm dependencies
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
