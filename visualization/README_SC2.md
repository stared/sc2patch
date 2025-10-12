# SC2 Patch Visualization

Interactive visualization of StarCraft II balance changes across patches.

## Setup

1. **Download unit images** (run from project root):
```bash
cd ..
python scripts/download_unit_images.py
```

2. **Install dependencies**:
```bash
cd visualization
pnpm install
```

3. **Start development server**:
```bash
pnpm dev
```

Visit http://localhost:5173/ to view the visualization.

## Features

- **Grid View**: Patches as rows, units grouped by race as columns
- **Hover Details**: Mouse over unit icons to see all changes in that patch
- **View Modes**: Toggle between "By Patch" and "By Unit" views
- **Visual Organization**: Units grouped by race (Terran, Protoss, Zerg)

## Current Status

- ✅ Basic grid visualization
- ✅ Tooltip with change details
- ✅ D3.js integration for future animations
- ✅ View mode toggle buttons
- ⏳ Unit images need to be downloaded
- ⏳ "By Unit" view needs full implementation

## Next Steps

1. Run the image download script to fetch unit icons
2. Add smooth D3.js transitions between view modes
3. Implement buff/nerf/redesign categorization
4. Add filtering and search capabilities