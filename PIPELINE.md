# SC2Patches Pipeline Documentation

## Overview

The SC2Patches pipeline processes StarCraft II balance patch notes through three clear stages:

1. **Download** - Fetch HTML from Blizzard News and convert to Markdown
2. **Parse** - Extract structured data using GPT-5 via OpenRouter
3. **Validate** - Check completeness and correctness

Each stage generates a timestamped markdown log in `data/logs/` for debugging and tracking.

## Pipeline Architecture

```
data/patch_urls.json (MANUAL)
         ↓
    [1_download.py]
         ↓
    data/raw_html/*.html
    data/raw_patches/*.md
         ↓
    [2_parse.py] ← GPT-5 via OpenRouter
         ↓
    data/processed/patches/*.json
         ↓
    [3_validate.py]
         ↓
    ✓ Validated patches ready for visualization
```

## Data Sources

**Primary: Blizzard News**
- Official source: https://news.blizzard.com/en-us/feed/starcraft-2
- Most reliable for modern patches (3.x+)
- Full HTML with structured metadata

**Fallback: Liquipedia**
- Community source: https://liquipedia.net/starcraft2/Patches
- Better coverage for old patches (1.x, 2.x)
- Some patches may link to web archives

## Single Source of Truth

**`data/patch_urls.json`** - The ONLY manually defined file

Everything else is derived/computed from this file and the downloaded HTML.

Current format (array of URLs):
```json
[
  "https://news.blizzard.com/en-us/article/24225313/starcraft-ii-5-0-15-patch-notes",
  "https://news.blizzard.com/en-us/starcraft2/24009150/starcraft-ii-5-0-12-patch-notes"
]
```

## Stage 1: Download

**Script:** `scripts/1_download.py`

**Purpose:** Download HTML from URLs and convert to Markdown for human review

**Usage:**
```bash
# Download all patches
uv run python scripts/1_download.py

# Skip already downloaded files
uv run python scripts/1_download.py --skip-existing
```

**Outputs:**
- `data/raw_html/{filename}.html` - Raw HTML (for parsing)
- `data/raw_patches/{version}.md` - Markdown (for human review)
- `data/logs/YYYY-MM-DD-HH-MM-download.md` - Execution log

**What it does:**
1. Reads `data/patch_urls.json`
2. For each URL:
   - Fetches HTML (with validation - not homepage)
   - Extracts metadata from JSON-LD
   - Saves HTML file
   - Converts to Markdown with frontmatter
   - Saves Markdown file
3. Generates timestamped log

**Common Issues:**
- **404 errors:** Old battle.net URLs may be dead → check Liquipedia or Web Archive
- **Homepage redirect:** URL changed → find new URL on Blizzard News
- **Empty HTML:** Network issue → retry

## Stage 2: Parse

**Script:** `scripts/2_parse.py`

**Purpose:** Parse HTML files with GPT-5 to extract structured balance changes

**Usage:**
```bash
# Parse all HTML files
uv run python scripts/2_parse.py

# Skip already parsed files
uv run python scripts/2_parse.py --skip-existing

# Parse specific version
uv run python scripts/2_parse.py 5.0.15
```

**Requires:** `OPENROUTER_API_KEY` environment variable

**Outputs:**
- `data/processed/patches/{version}.json` - Structured patch data
- `data/logs/YYYY-MM-DD-HH-MM-parse.md` - Execution log

**What it does:**
1. Reads HTML files from `data/raw_html/`
2. For each file:
   - Extracts body text
   - Sends to GPT-5 via OpenRouter API
   - Validates response (all changes have `change_type`)
   - Saves structured JSON
3. Generates timestamped log with statistics

**Output Format:**
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

**Change Type Classification:**
- `buff` - Entity becomes STRONGER (reduced cost, increased damage, etc.)
- `nerf` - Entity becomes WEAKER (increased cost, reduced damage, etc.)
- `mixed` - Both positive and negative aspects

**Common Issues:**
- **No balance changes:** Patch may be co-op only → This is expected, not an error
- **API timeout:** Retry or increase timeout in parse.py
- **Missing change_type:** GPT-5 response incomplete → Check prompt, retry
- **Empty response:** API issue → Check OPENROUTER_API_KEY, retry

## Stage 3: Validate

**Script:** `scripts/3_validate.py`

**Purpose:** Validate all processed patches for completeness

**Usage:**
```bash
uv run python scripts/3_validate.py
```

**Outputs:**
- `data/logs/YYYY-MM-DD-HH-MM-validate.md` - Validation report
- Exit code 0 if all valid, 1 if any failures

**What it checks:**
- JSON is valid
- Required fields exist: `metadata`, `changes`
- Metadata has: `version`, `date`, `title`
- Each change has: `id`, `patch_version`, `entity_id`, `raw_text`, `change_type`
- `change_type` is one of: `buff`, `nerf`, `mixed`
- No empty fields

**Statistics reported:**
- Total patches
- Total unique entities
- Total changes
- Breakdown by type (buffs/nerfs/mixed)

**Common Issues:**
- **Missing change_type:** Re-run stage 2 on that patch
- **Invalid JSON:** Corrupted file → delete and re-parse
- **Empty fields:** Parser bug → report issue

## Logs

All pipeline stages generate timestamped markdown logs in `data/logs/`:

**Format:** `YYYY-MM-DD-HH-MM-{stage}.md`

**Example:** `2025-10-13-16-17-validate.md`

**Structure:**
```markdown
# Validate Report - 2025-10-13 16:17:10 UTC

**Started:** 2025-10-13 16:17:10 UTC
**Duration:** 0m 12s

## Summary
- ✅ 42 successful
- ❌ 0 failed
- ⊘ 0 skipped

## Successful
- ✅ 5.0.15: 5.0.15.json

## Failed
- ❌ 1.1.3: HTTP 404 error

## Details
[Full debug output]
```

**Benefits:**
- Easy to scan (summary at top)
- Sortable by timestamp
- Compare runs over time
- Debug failures

## Fail Fast Philosophy

**Critical Rule:** Errors fail LOUDLY, immediately

- Download fails HTTP 404 → FAIL (don't continue)
- Parse gets empty response → FAIL (don't create empty file)
- Validate finds missing change_type → FAIL (exit code 1)

**NO defensive programming:**
- NO fallbacks hiding real issues
- NO "try this, then that" patterns
- FIX the root cause, don't work around it

## Running the Full Pipeline

```bash
# 1. Download patches
uv run python scripts/1_download.py

# 2. Parse with GPT-5 (requires OPENROUTER_API_KEY)
export OPENROUTER_API_KEY="your-key-here"
uv run python scripts/2_parse.py

# 3. Validate
uv run python scripts/3_validate.py

# Check logs
ls -lt data/logs/
```

## Testing & Quality

**Before committing:**
```bash
# Format Python code
uv run ruff format .

# Check Python code
uv run ruff check .

# Type check
uv run ty check src/

# Test visualization
cd visualization
pnpm lint
pnpm type-check
pnpm dev  # Visit localhost:5173
```

## Visualization

The React visualization reads directly from `data/processed/patches/*.json`.

**Build-time manifest generation:**
- Vite globs `data/processed/patches/*.json` at build time
- No runtime directory reading needed
- Hard validation fails if data incomplete

## Adding New Patches

1. Find patch URL on Blizzard News or Liquipedia
2. Add URL to `data/patch_urls.json`
3. Run pipeline:
   ```bash
   uv run python scripts/1_download.py
   uv run python scripts/2_parse.py {version}
   uv run python scripts/3_validate.py
   ```
4. Check logs for any issues
5. Commit changes (patches + patch_urls.json)

## Troubleshooting

**Problem:** Download fails with 404
- **Fix:** URL is dead, find new URL or use Web Archive

**Problem:** Parse returns empty
- **Fix:** Check OPENROUTER_API_KEY, check API status, retry

**Problem:** Validate fails - missing change_type
- **Fix:** Re-parse that specific patch: `uv run python scripts/2_parse.py {version}`

**Problem:** GPT-5 classifies incorrectly
- **Fix:** Update prompt in `src/sc2patches/parse.py`, re-parse affected patches

**Problem:** Visualization doesn't load patch
- **Fix:** Check `data/processed/patches/{version}.json` exists and is valid JSON

## File Locations

```
sc2patches/
├── data/
│   ├── patch_urls.json          # ← ONLY manually edited file
│   ├── logs/                    # Timestamped execution logs
│   ├── raw_html/                # Downloaded HTML
│   ├── raw_patches/             # Human-readable Markdown
│   └── processed/patches/       # Final JSON data
├── src/sc2patches/
│   ├── logger.py                # Markdown log generation
│   ├── download.py              # Download & convert logic
│   ├── parse.py                 # GPT-5 parsing logic
│   └── models.py                # Pydantic models
└── scripts/
    ├── 1_download.py            # Stage 1 pipeline
    ├── 2_parse.py               # Stage 2 pipeline
    └── 3_validate.py            # Stage 3 pipeline
```

## Help & Issues

- Documentation: This file (PIPELINE.md)
- Project docs: CLAUDE.md
- Issues: GitHub issues or contact maintainer
