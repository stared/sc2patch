// visualization/scripts/generate-route-files.js
// Generate static HTML files for each route with route-specific meta tags
// So direct URLs work on GitHub Pages AND social media previews are correct

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// PATHS
const SEO_CONFIG_PATH = path.resolve(__dirname, '../src/seoConfig.json');
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

/**
 * Get date range for patches (matching logic in SEOContent.tsx)
 */
function getDateRange(patches) {
  if (!patches || patches.length === 0) return { start: '', end: '' };

  const dates = patches.map(p => new Date(p.date).getTime());
  const startDate = new Date(Math.min(...dates));
  const endDate = new Date(Math.max(...dates));

  return {
    start: startDate.getFullYear().toString(),
    end: endDate.getFullYear().toString()
  };
}

/**
 * Get buff/nerf counts for a unit across patches (matching logic in SEOContent.tsx)
 */
function getChangeStats(entityId, patches) {
  let buffs = 0, nerfs = 0, mixed = 0;

  for (const patch of patches) {
    // Note: patch.entities is an array in JSON, but a Map in the React app
    // We need to handle the array structure from JSON here
    const entity = patch.entities ? patch.entities.find(e => e.entity_id === entityId) : null;
    
    if (entity) {
      for (const change of entity.changes) {
        if (change.change_type === 'buff') buffs++;
        else if (change.change_type === 'nerf') nerfs++;
        else if (change.change_type === 'mixed') mixed++;
      }
    }
  }

  return { buffs, nerfs, mixed };
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
    const seoConfig = JSON.parse(await fs.readFile(SEO_CONFIG_PATH, 'utf-8'));

    const BASE_URL = seoConfig.baseUrl;
    const allPatches = patchesData.patches;

    // Build units lookup map
    const unitsMap = new Map();
    unitsData.forEach(unit => unitsMap.set(unit.id, unit));

    // Extract unique entity_ids and races from patches
    // And collect relevant patches for each entity/race
    const entityPatchesMap = new Map();
    const racePatchesMap = new Map();

    const entityIds = new Set();
    const races = new Set();

    allPatches.forEach((patch) => {
      if (patch.entities) {
        patch.entities.forEach((entity) => {
          const id = entity.entity_id;
          entityIds.add(id);
          const race = id.split('-')[0];
          races.add(race);

          // Collect patches for unit
          if (!entityPatchesMap.has(id)) entityPatchesMap.set(id, []);
          entityPatchesMap.get(id).push(patch);

          // Collect patches for race
          if (!racePatchesMap.has(race)) racePatchesMap.set(race, []);
          // Avoid duplicates per patch for race map if multiple units updated in same patch?
          // Actually, we want the list of patches that affected the race.
          // Since we iterate entities, we might add the same patch multiple times.
          // Let's use a Set for patch versions per race to ensure uniqueness, then resolve back to patch objects.
        });
      }
    });
    
    // Resolve unique patches for races
    const raceUniquePatches = new Map();
    for (const race of races) {
        const uniquePatchVersions = new Set();
        const racePatchList = [];
        
        allPatches.forEach(patch => {
             if (patch.entities && patch.entities.some(e => e.entity_id.startsWith(race))) {
                 racePatchList.push(patch);
             }
        });
        raceUniquePatches.set(race, racePatchList);
    }

    let created = 0;

    // Generate race pages: /zerg/, /protoss/, etc.
    for (const race of races) {
      const raceName = formatRaceName(race);
      const routeDir = path.join(DIST_DIR, race);
      const routeIndex = path.join(routeDir, 'index.html');
      
      const filteredPatches = raceUniquePatches.get(race) || [];
      const patchCount = filteredPatches.length;
      const dateRange = getDateRange(filteredPatches);
      
      // Calculate unit count
      const raceUnitIds = new Set();
      filteredPatches.forEach(patch => {
          patch.entities.forEach(e => {
              if (e.entity_id.startsWith(race)) raceUnitIds.add(e.entity_id);
          });
      });
      const unitCount = raceUnitIds.size;

      const title = `${raceName} Balance Changes Visualized - StarCraft 2`;
      const description = `Comprehensive timeline of balance changes for all ${raceName} units in SC2. Explore ${patchCount} patches affecting ${unitCount} units from ${dateRange.start} to ${dateRange.end}.`;
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
      if (!unit) {
        console.warn(`⚠️ Skipping route generation for unknown unit ID: ${entityId}`);
        continue;
      }
      
      const unitName = unit.name;
      const raceName = formatRaceName(race);
      
      const unitPatches = entityPatchesMap.get(entityId) || [];
      const patchCount = unitPatches.length;
      const dateRange = getDateRange(unitPatches);
      const stats = getChangeStats(entityId, unitPatches);

      const routeDir = path.join(DIST_DIR, race, unitSlug);
      const routeIndex = path.join(routeDir, 'index.html');

      const title = `${unitName} Balance Changes Visualized - StarCraft 2`;
      const description = `View the complete balance history for the ${raceName} ${unitName} in StarCraft 2. Explore ${patchCount} patches from ${dateRange.start} to ${dateRange.end}, including ${stats.buffs} buffs and ${stats.nerfs} nerfs.`;
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
