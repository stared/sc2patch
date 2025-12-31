# StarCraft II Balance Timeline

Visual history of StarCraft II multiplayer balance changes (2010–present).

**[Live Demo](https://p.migdal.pl/sc2-balance-timeline/)**

---

## 1. Overview

- **Full history** from Wings of Liberty through Legacy of the Void
- **Unit filtering** with complete change history
- **Categorized** as buff, nerf, or mixed
- **Cited sources** linking to official Blizzard patch notes

---

## 2. Data Pipeline

### Sources
- **Primary:** Official patch notes ([Blizzard News](https://news.blizzard.com/en-us/starcraft2))
- **Validation:** Cross-referenced with [Liquipedia](https://liquipedia.net/starcraft2/Patches)
- **Entities:** Tech tree data from Liquipedia

### Processing
```
HTML (Blizzard) → LLM Parse → Validate → JSON → React/D3
```

**Why LLM?** Patch notes vary in format (tables, bullets, prose). LLMs distinguish bug fixes from balance changes and handle unit renames.

### Classifications
- **Buff** — unit stronger (cost down, damage up)
- **Nerf** — unit weaker (cost up, damage down)
- **Mixed** — both positive and negative

---

## 3. Development

### Stack
- **Frontend:** React, D3.js, TypeScript, Vite
- **Backend:** Python 3.12, Pydantic, httpx
- **LLM:** [Gemini 3 Pro](https://openrouter.ai/google/gemini-3-pro-preview) via [OpenRouter](https://openrouter.ai/) (tested GPT-4.1, GPT-5.2, Gemini Flash — Gemini 3 Pro seems to work the best for this data)

### Quick Start

Requires [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io/).

```bash
uv sync
cd visualization && pnpm install && pnpm dev
```

### Rebuild Data

Copy `.env.example` to `.env` and add your `OPENROUTER_API_KEY`.

```bash
uv run python scripts/1_download.py
uv run python scripts/2_parse.py
uv run python scripts/3_validate.py
uv run python scripts/4_export_for_viz.py
```

### Structure
```
├── scripts/           # Pipeline (1-4)
├── src/sc2patches/    # Python library
├── data/              # Source URLs, processed JSON
└── visualization/     # React frontend
```

---

## Docs

- [DATA.md](DATA.md) — patch coverage, known issues
- [CLAUDE.md](CLAUDE.md) — development guidelines

## License

MIT

---

*StarCraft II and Blizzard Entertainment are trademarks of Blizzard Entertainment, Inc.*
