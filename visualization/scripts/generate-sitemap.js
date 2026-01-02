// visualization/scripts/generate-sitemap.js
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

// CONFIGURATION
const BASE_URL = 'https://p.migdal.pl/sc2-balance-timeline';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// PATHS
const DATA_PATH = path.resolve(__dirname, '../public/data/patches.json');
const PUBLIC_DIR = path.resolve(__dirname, '../public');
const SITEMAP_PATH = path.join(PUBLIC_DIR, 'sitemap.xml');
const ROBOTS_PATH = path.join(PUBLIC_DIR, 'robots.txt');

/**
 * Escapes special characters for XML compliance.
 */
function escapeXml(unsafe) {
  return unsafe.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
    }
  });
}

/**
 * Generates the XML string for a single URL entry.
 */
function generateUrlEntry(urlPath, priority = '0.5', changefreq = 'weekly') {
  const fullUrl = `${BASE_URL}${urlPath}`;
  const lastMod = new Date().toISOString();

  return `
  <url>
    <loc>${escapeXml(fullUrl)}</loc>
    <lastmod>${lastMod}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`;
}

async function generateSitemap() {
  try {
    console.log('🗺️  Generating Sitemap...');

    // 1. Read Data
    const fileContent = await fs.readFile(DATA_PATH, 'utf-8');
    const data = JSON.parse(fileContent);

    if (!data.patches || !Array.isArray(data.patches)) {
      throw new Error('Invalid JSON structure: "patches" array missing.');
    }

    // 2. Extract unique entity_ids from all patches
    const entityIds = new Set();
    const races = new Set();

    data.patches.forEach((patch) => {
      if (patch.entities) {
        patch.entities.forEach((entity) => {
          entityIds.add(entity.entity_id);
          // Extract race from entity_id (e.g., 'zerg-hydralisk' -> 'zerg')
          const race = entity.entity_id.split('-')[0];
          races.add(race);
        });
      }
    });

    const urls = [];

    // 3. Add Home Page
    urls.push(generateUrlEntry('/', '1.0', 'daily'));

    // 4. Add Race Pages
    races.forEach((race) => {
      const racePath = `/${race}/`;
      urls.push(generateUrlEntry(racePath, '0.9'));
    });

    // 5. Add Unit Pages
    entityIds.forEach((entityId) => {
      // Extract race and unit slug from entity_id (e.g., 'zerg-hydralisk' -> race='zerg', slug='hydralisk')
      const parts = entityId.split('-');
      const race = parts[0];
      const unitSlug = parts.slice(1).join('-');

      const unitPath = `/${race}/${unitSlug}`;
      urls.push(generateUrlEntry(unitPath, '0.8'));
    });

    // 6. Construct Final XML
    const sitemapContent = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.join('')}
</urlset>
`;

    // 7. Write sitemap.xml
    await fs.writeFile(SITEMAP_PATH, sitemapContent);
    console.log(`✅ Sitemap written to: ${SITEMAP_PATH} (${urls.length} URLs)`);

    // 8. Generate robots.txt
    const robotsContent = `User-agent: *
Allow: /

Sitemap: ${BASE_URL}/sitemap.xml
`;
    await fs.writeFile(ROBOTS_PATH, robotsContent);
    console.log(`✅ Robots.txt written to: ${ROBOTS_PATH}`);

  } catch (error) {
    console.error('❌ Error generating sitemap:', error);
    process.exit(1);
  }
}

generateSitemap();
