# Pipeline Scripts

Four stages transform Blizzard patch notes into visualization data.

## Stages

| Script | Input | Output |
|--------|-------|--------|
| `1_download.py` | `data/patch_urls.json` | `data/raw_html/*.html` |
| `2_parse.py` | HTML files | `data/processed/patches/*.json` |
| `3_validate.py` | JSON files | Validation report |
| `4_export_for_viz.py` | Processed data | `visualization/public/data/` |

## Quick Start

```bash
uv run python scripts/1_download.py
uv run python scripts/2_parse.py      # Requires OPENROUTER_API_KEY
uv run python scripts/3_validate.py
uv run python scripts/4_export_for_viz.py
```

## Utilities

`utils/` contains helper scripts for one-off tasks (image downloads, data fixes).

## Logs

Each stage writes timestamped logs to `data/logs/`.
