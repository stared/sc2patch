// visualization/scripts/generate-route-files.js
// Generate static HTML files for each route with route-specific meta tags
// So direct URLs work on GitHub Pages AND social media previews are correct

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// CONFIGURATION
const BASE_URL = 'https://p.migdal.pl/sc2-balance-timeline';

// PATHS
const DATA_PATH = path.resolve(__dirname, '../public/data/patches.json');
const UNITS_PATH = path.resolve(__dirname, '../../data/units.json');
const DIST_DIR = path.resolve(__dirname, '../dist');
const INDEX_HTML = path.join(DIST_DIR, 'index.html');

/**
 * Format unit name from entity_id if not in units map
 */
function formatUnitName(entityId) {
  const parts = entityId.split('-');
  const unitName = parts.slice(1).join('-');
  return unitName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format race name
 */
function formatRaceName(race) {
  return race.charAt(0).toUpperCase() + race.slice(1);
}

/**
 * Replace meta tags in HTML template
 */
function injectMetaTags(template, { title, description, url }) {
  let html = template;

  // Title
  html = html.replace(
    /<title>[^<]*<\/title>/,
    `<title>${title}</title>`
  );

  // Meta description
  html = html.replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="description" content="${description}" />`
  );

  // Open Graph
  html = html.replace(
    /<meta\s+property="og:title"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:title" content="${title}" />`
  );
  html = html.replace(
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:description" content="${description}" />`
  );
  html = html.replace(
    /<meta\s+property="og:url"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:url" content="${url}" />`
  );

  // Twitter Card
  html = html.replace(
    /<meta\s+name="twitter:title"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:title" content="${title}" />`
  );
  html = html.replace(
    /<meta\s+name="twitter:description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:description" content="${description}" />`
  );

  // Canonical URL
  if (!html.includes('<link rel="canonical"')) {
    html = html.replace(
      '</head>',
      `  <link rel="canonical" href="${url}" />\n  </head>`
    );
  } else {
    html = html.replace(
      /<link\s+rel="canonical"\s+href="[^"]*"\s*\/?>/,
      `<link rel="canonical" href="${url}" />`
    );
  }

  return html;
}

async function generateRouteFiles() {
  try {
    console.log('📁 Generating route files with meta tags...');

    // Check if dist/index.html exists
    try {
      await fs.access(INDEX_HTML);
    } catch {
      console.error('❌ dist/index.html not found. Run "vite build" first.');
      process.exit(1);
    }

    // Read template and data
    const template = await fs.readFile(INDEX_HTML, 'utf-8');
    const patchesData = JSON.parse(await fs.readFile(DATA_PATH, 'utf-8'));
    const unitsData = JSON.parse(await fs.readFile(UNITS_PATH, 'utf-8'));

    // Build units lookup map
    const unitsMap = new Map();
    unitsData.forEach(unit => unitsMap.set(unit.id, unit));

    // Extract unique entity_ids and races from patches
    const entityIds = new Set();
    const races = new Set();

    patchesData.patches.forEach((patch) => {
      if (patch.entities) {
        patch.entities.forEach((entity) => {
          entityIds.add(entity.entity_id);
          const race = entity.entity_id.split('-')[0];
          races.add(race);
        });
      }
    });

    // Count changes per entity for descriptions
    const changeCounts = new Map();
    patchesData.patches.forEach((patch) => {
      if (patch.entities) {
        patch.entities.forEach((entity) => {
          const count = changeCounts.get(entity.entity_id) || 0;
          changeCounts.set(entity.entity_id, count + 1);
        });
      }
    });

    let created = 0;

    // Generate race pages: /zerg/, /protoss/, etc.
    for (const race of races) {
      const raceName = formatRaceName(race);
      const routeDir = path.join(DIST_DIR, race);
      const routeIndex = path.join(routeDir, 'index.html');

      const title = `${raceName} Balance Changes Visualized - StarCraft 2`;
      const description = `Complete timeline of balance changes for all ${raceName} units in StarCraft 2. Interactive visualization of buffs, nerfs, and patches.`;
      const url = `${BASE_URL}/${race}/`;

      const html = injectMetaTags(template, { title, description, url });

      await fs.mkdir(routeDir, { recursive: true });
      await fs.writeFile(routeIndex, html);
      created++;
    }

    // Generate unit pages: /zerg/hydralisk, /protoss/zealot, etc.
    for (const entityId of entityIds) {
      const parts = entityId.split('-');
      const race = parts[0];
      const unitSlug = parts.slice(1).join('-');

      const unit = unitsMap.get(entityId);
      const unitName = unit?.name || formatUnitName(entityId);
      const raceName = formatRaceName(race);
      const patchCount = changeCounts.get(entityId) || 0;

      const routeDir = path.join(DIST_DIR, race, unitSlug);
      const routeIndex = path.join(routeDir, 'index.html');

      const title = `${unitName} Balance Changes Visualized - StarCraft 2`;
      const description = `View all ${patchCount} balance patches for the ${raceName} ${unitName} in StarCraft 2. Interactive timeline of buffs and nerfs.`;
      const url = `${BASE_URL}/${race}/${unitSlug}`;

      const html = injectMetaTags(template, { title, description, url });

      await fs.mkdir(routeDir, { recursive: true });
      await fs.writeFile(routeIndex, html);
      created++;
    }

    console.log(`✅ Created ${created} route files with custom meta tags`);

  } catch (error) {
    console.error('❌ Error generating route files:', error);
    process.exit(1);
  }
}

generateRouteFiles();
