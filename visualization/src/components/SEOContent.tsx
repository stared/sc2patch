import { Helmet } from 'react-helmet-async';
import { ProcessedPatchData, Unit, Race } from '../types';
import seoConfig from '../seoConfig.json';

interface SEOContentProps {
  selectedEntityId: string | null;
  selectedRace: Race | null;
  units: Map<string, Unit>;
  patches: ProcessedPatchData[];
  filteredPatches: ProcessedPatchData[];
}

// --- Helpers ---

// Format unit name for display
function formatUnitName(id: string): string {
  const parts = id.split('-');
  const unitName = parts.slice(1).join('-');
  return unitName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Format race name
function formatRaceName(race: Race): string {
  return race.charAt(0).toUpperCase() + race.slice(1);
}

// Format change type for screen readers
function formatChangeType(type: string): string {
  if (type === 'buff') return 'Buff';
  if (type === 'nerf') return 'Nerf';
  return 'Change';
}

// Get buff/nerf counts for a unit across patches
function getChangeStats(entityId: string, patches: ProcessedPatchData[]): { buffs: number; nerfs: number; mixed: number } {
  let buffs = 0, nerfs = 0, mixed = 0;

  for (const patch of patches) {
    const entity = patch.entities.get(entityId);
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

// Get date range for patches
function getDateRange(patches: ProcessedPatchData[]): { start: string; end: string } {
  if (patches.length === 0) return { start: '', end: '' };

  const dates = patches.map(p => new Date(p.date).getTime());
  const startDate = new Date(Math.min(...dates));
  const endDate = new Date(Math.max(...dates));

  return {
    start: startDate.getFullYear().toString(),
    end: endDate.getFullYear().toString()
  };
}

// Format date for display
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

export function SEOContent({ selectedEntityId, selectedRace, units, patches, filteredPatches }: SEOContentProps) {
  const baseUrl = seoConfig.baseUrl;
  const dateRange = getDateRange(filteredPatches);
  const patchCount = filteredPatches.length;

  let viewData: {
    title: string;
    description: string;
    canonicalUrl: string;
    jsonLd: object | null;
    type: 'default' | 'unit' | 'race';
    unitName?: string;
    raceName?: string;
    stats?: { buffs: number; nerfs: number; mixed: number };
    unitList?: [string, ProcessedPatchData[]][];
  } = {
    title: seoConfig.defaultTitle,
    description: seoConfig.defaultDescription,
    canonicalUrl: baseUrl,
    jsonLd: null,
    type: 'default'
  };

  if (selectedEntityId) {
    // UNIT VIEW
    const unit = units.get(selectedEntityId);
    
    if (!unit) {
      // If we have an ID but no unit data, something is critically wrong with our data loading.
      // We should not try to render a partial view.
      console.error(`CRITICAL: Unit data missing for ID: ${selectedEntityId}`);
      return null;
    }

    const unitName = unit.name;
    const race = unit.race;
    const raceName = formatRaceName(race);
    
    const stats = getChangeStats(selectedEntityId, patches);
    const canonicalUrl = `${baseUrl}/${race}/${selectedEntityId.split('-').slice(1).join('-')}`;

    viewData = {
      type: 'unit',
      unitName,
      raceName,
      stats,
      title: `${unitName} Balance Changes Visualized - StarCraft 2`,
      description: `View the complete balance history for the ${raceName} ${unitName} in StarCraft 2. Explore ${patchCount} patches from ${dateRange.start} to ${dateRange.end}, including ${stats.buffs} buffs and ${stats.nerfs} nerfs.`,
      canonicalUrl,
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'ItemPage',
        'name': `${unitName} Balance History`,
        'url': canonicalUrl,
        'mainEntity': {
          '@type': 'VideoGame',
          'name': 'StarCraft II',
          'character': { '@type': 'Thing', 'name': unitName, 'description': `${raceName} unit` }
        },
        'breadcrumb': {
          '@type': 'BreadcrumbList',
          'itemListElement': [
            { '@type': 'ListItem', 'position': 1, 'name': 'SC2 Balance Timeline', 'item': baseUrl },
            { '@type': 'ListItem', 'position': 2, 'name': raceName, 'item': `${baseUrl}/${race}/` },
            { '@type': 'ListItem', 'position': 3, 'name': unitName, 'item': canonicalUrl }
          ]
        }
      }
    };
  } else if (selectedRace) {
    // RACE VIEW
    const raceName = formatRaceName(selectedRace);
    const canonicalUrl = `${baseUrl}/${selectedRace}/`;

    // Group units for race view listing
    const unitPatches = new Map<string, ProcessedPatchData[]>();
    filteredPatches.forEach(patch => {
      patch.entities.forEach((_, id) => {
        if (id.startsWith(selectedRace)) {
          if (!unitPatches.has(id)) unitPatches.set(id, []);
          unitPatches.get(id)!.push(patch);
        }
      });
    });
    const sortedUnits = Array.from(unitPatches.entries()).sort((a, b) => b[1].length - a[1].length);

    viewData = {
      type: 'race',
      raceName,
      unitList: sortedUnits,
      title: `${raceName} Balance Changes Visualized - StarCraft 2`,
      description: `Comprehensive timeline of balance changes for all ${raceName} units in SC2. Explore ${patchCount} patches affecting ${sortedUnits.length} units from ${dateRange.start} to ${dateRange.end}.`,
      canonicalUrl,
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        'name': `${raceName} Balance History`,
        'url': canonicalUrl,
        'about': { '@type': 'VideoGame', 'name': 'StarCraft II' },
        'breadcrumb': {
          '@type': 'BreadcrumbList',
          'itemListElement': [
            { '@type': 'ListItem', 'position': 1, 'name': 'SC2 Balance Timeline', 'item': baseUrl },
            { '@type': 'ListItem', 'position': 2, 'name': raceName, 'item': canonicalUrl }
          ]
        }
      }
    };
  }

  return (
    <>
      <Helmet>
        <title>{viewData.title}</title>
        <meta name="description" content={viewData.description} />
        <link rel="canonical" href={viewData.canonicalUrl} />

        <meta property="og:title" content={viewData.title} />
        <meta property="og:description" content={viewData.description} />
        <meta property="og:url" content={viewData.canonicalUrl} />
        <meta property="og:type" content="website" />
        <meta property="og:image" content={seoConfig.defaultImage} />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={viewData.title} />
        <meta name="twitter:description" content={viewData.description} />
        <meta name="twitter:image" content={seoConfig.defaultImage} />

        {viewData.jsonLd && (
          <script type="application/ld+json">{JSON.stringify(viewData.jsonLd)}</script>
        )}
      </Helmet>

      {viewData.type === 'unit' && selectedEntityId && viewData.stats && (
        <div className="sr-only">
          <h2>Balance Change Log: {viewData.unitName}</h2>
          <p>The {viewData.raceName} {viewData.unitName} has received {patchCount} balance patches from {dateRange.start} to {dateRange.end}, including {viewData.stats.buffs} buffs and {viewData.stats.nerfs} nerfs.</p>
          {filteredPatches.map(patch => {
            const entity = patch.entities.get(selectedEntityId);
            if (!entity) return null;
            return (
              <section key={patch.version} aria-labelledby={`patch-${patch.version}`}>
                <h3 id={`patch-${patch.version}`}>
                  <a href={patch.url} target="_blank" rel="noopener noreferrer">Patch {patch.version}</a> - {formatDate(patch.date)}
                </h3>
                <ul>
                  {entity.changes.map((change, i) => (
                    <li key={i}><strong>{formatChangeType(change.change_type)}:</strong> {change.raw_text}</li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      {viewData.type === 'race' && viewData.unitList && (
        <div className="sr-only">
          <h2>{viewData.raceName} Balance Change Overview</h2>
          <p>The {viewData.raceName} faction has received balance changes in {patchCount} patches from {dateRange.start} to {dateRange.end}, affecting {viewData.unitList.length} different units.</p>
          <h3>Units with Balance Changes</h3>
          <ul>
            {viewData.unitList.map(([id, patchList]) => {
              const unit = units.get(id);
              const name = unit ? unit.name : formatUnitName(id);
              const stats = getChangeStats(id, patches);
              return (
                <li key={id}>{name}: {patchList.length} patches ({stats.buffs} buffs, {stats.nerfs} nerfs)</li>
              );
            })}
          </ul>
        </div>
      )}
    </>
  );
}
