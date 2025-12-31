# StarCraft II Balance Timeline

Visual history of StarCraft II multiplayer balance changes (2010–present).

**[Live Demo](https://p.migdal.pl/sc2-balance-timeline/)**

[![](./visualization/public/sc2_balance_timeline.jpg)](<(https://p.migdal.pl/sc2-balance-timeline/)>)

---

## What inside

- All unit changes
- View by race
- Pick era
- Pick history of balance changes by year
- Changes characterized as:
  - buffs (anything that makes a unit stronger)
  - nerfs (anything that makes an unit weaker)
  - mixed (well, anything that is a double edged blade)

If it glows, it is clickable. It should also work on mobile.

Data visualization with D3.js, data extraction with LLM (Gemini 3 Pro).

I decided for unit-first view. So upgrades and similar are for unit. For the same reason, summoned units are assigned to their parent - Locus to Swarm Host, Infested Terran to Infestor, Broodling to Brood Lord (even though it also appears with destored Zerg buildings), etc.

## Data

Data comes from [Blizzard StarCraft II](https://starcraft2.blizzard.com/en-us/), with a lot of suplemental stuff from [Liquipedia](https://liquipedia.net/starcraft2/) ([patch list](https://liquipedia.net/starcraft2), link to unit pages, and checks).

It is a visualization of all balance changes from StarCraft II history.

| Era                | Launch   | Patch Range    | First Balance |
| ------------------ | -------- | -------------- | ------------- |
| Wings of Liberty   | Jul 2010 | 1.1.0 - 1.5.4  | Sep 2010      |
| Heart of the Swarm | Mar 2013 | 2.0.8 - 2.1.9  | May 2013      |
| Legacy of the Void | Nov 2015 | 3.1.1 - 3.14.0 | Jan 2016      |
| Free-to-Play       | Nov 2017 | 4.0 - 4.12.0   | Nov 2017      |
| 10th Anniversary   | Jul 2020 | 5.0.2 - 5.0.15 | Aug 2020      |

As of now, it is 49 balance patches.

I only show patches that are balance for multiplayer - excluding all changes for campaign, co-op, bug fixes, and other adjustment which are not directly for typical ranked game.

Also, I didn't include balance for pre-release tests, are there are too rapid, with more like a creative process of unit design than something actually released. Also - for some of these changes original pages might be out. (If there is a big need for that, I may consider adding).

There are around 39 beta patches:

- WoL Beta: 0.3.0 - 0.20.0
- HotS Beta: Updates #1-15
- LotV Beta: 2.5.0 - 2.5.5

### Processing

Most proessing happends withing Python. Pipeline is as follows.

```
HTML (Blizzard) → LLM Parse → Validate → JSON → D3
```

For paring, LLMs are essiential. I tried first typical scripts, but over so many years Blizzard page changes over and over. Using classical scripts didn't scale at all.

Manual input would work... but it is also why only now I started this project (ideas was old).

We use [Gemini 3 Pro](https://openrouter.ai/google/gemini-3-pro-preview) via [OpenRouter](https://openrouter.ai/) (tested Claude Opus 4.5, GPT-5.2, Gemini 3 Flash — Gemini 3 Pro seems to work the best for this data).

## Running locally

For running vis, you need [pnpm](https://pnpm.io/):

```bash
cd visualization
pnpm install
pnpm dev
```

For parsing and building data, you need Python with [uv](https://docs.astral.sh/uv/).

Copy `.env.example` to `.env` and add your `OPENROUTER_API_KEY`.

```bash
uv sync
uv run python scripts/1_download.py
uv run python scripts/2_parse.py
uv run python scripts/3_validate.py
uv run python scripts/4_export_for_viz.py
```

Most of its development was with Claude Code and Opus 4.5. See [my blog post praising Claude Code + Gemini](https://quesma.com/blog/claude-skills-not-antigravity/).

### Structure

```
├── scripts/           # Pipeline (1-4)
├── src/sc2patches/    # Python library
├── data/              # Source URLs, processed JSON
└── visualization/     # React frontend
```

## License

MIT by [Piotr Mihdał](https://p.migdal.pl/) - processing code and data viz

---

_StarCraft II and Blizzard Entertainment are trademarks of Blizzard Entertainment, Inc._ Unit icons are assets of Blizzard.
