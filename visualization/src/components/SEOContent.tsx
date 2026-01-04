import { Helmet } from 'react-helmet-async';
import { ProcessedPatchData, Unit, Race } from '../types';

interface SEOContentProps {
  selectedEntityId: string | null;
  selectedRace: Race | null;
  units: Map<string, Unit>;
  patches: ProcessedPatchData[];
  filteredPatches: ProcessedPatchData[];
}

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
  const baseUrl = 'https://p.migdal.pl/sc2-balance-timeline';

  // Default (no selection)
  let title = '15 Years of StarCraft II Balance Changes Visualized';
  let description = 'The complete timeline of StarCraft II balance. Analyze 15 years of Blizzard patches, detailing every buff and nerf for Zerg, Terran, and Protoss units. Interactive visualization built with D3.js.';
  let canonicalUrl = baseUrl;
  let jsonLd: object | null = null;

  if (selectedEntityId) {
    // Unit selected
    const unit = units.get(selectedEntityId);
    const unitName = unit?.name || formatUnitName(selectedEntityId);
    const race = unit?.race || selectedEntityId.split('-')[0] as Race;
    const raceName = formatRaceName(race);

    const stats = getChangeStats(selectedEntityId, patches);
    const dateRange = getDateRange(filteredPatches);
    const patchCount = filteredPatches.length;

    title = `${unitName} Balance Changes Visualized - StarCraft 2`;
    description = `View the complete balance history for the ${raceName} ${unitName} in StarCraft 2. Explore ${patchCount} patches from ${dateRange.start} to ${dateRange.end}, including ${stats.buffs} buffs and ${stats.nerfs} nerfs.`;
    canonicalUrl = `${baseUrl}/${race}/${selectedEntityId.split('-').slice(1).join('-')}`;

    jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'ItemPage',
      'name': `${unitName} Balance History`,
      'url': canonicalUrl,
      'mainEntity': {
        '@type': 'VideoGame',
        'name': 'StarCraft II',
        'character': {
          '@type': 'Thing',
          'name': unitName,
          'description': `${raceName} ${unit?.type || 'unit'}`
        }
      },
      'breadcrumb': {
        '@type': 'BreadcrumbList',
        'itemListElement': [
          { '@type': 'ListItem', 'position': 1, 'name': 'SC2 Balance Timeline', 'item': baseUrl },
          { '@type': 'ListItem', 'position': 2, 'name': raceName, 'item': `${baseUrl}/${race}/` },
          { '@type': 'ListItem', 'position': 3, 'name': unitName, 'item': canonicalUrl }
        ]
      }
    };
  } else if (selectedRace) {
    // Race selected
    const raceName = formatRaceName(selectedRace);
    const patchCount = filteredPatches.length;
    const dateRange = getDateRange(filteredPatches);

    // Count unique units in patches
    const unitIds = new Set<string>();
    filteredPatches.forEach(patch => {
      patch.entities.forEach((_, id) => {
        if (id.startsWith(selectedRace)) unitIds.add(id);
      });
    });

    title = `${raceName} Balance Changes Visualized - StarCraft 2`;
    description = `Comprehensive timeline of balance changes for all ${raceName} units in SC2. Explore ${patchCount} patches affecting ${unitIds.size} units from ${dateRange.start} to ${dateRange.end}.`;
    canonicalUrl = `${baseUrl}/${selectedRace}/`;

    jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      'name': `${raceName} Balance History`,
      'url': canonicalUrl,
      'about': {
        '@type': 'VideoGame',
        'name': 'StarCraft II'
      },
      'breadcrumb': {
        '@type': 'BreadcrumbList',
        'itemListElement': [
          { '@type': 'ListItem', 'position': 1, 'name': 'SC2 Balance Timeline', 'item': baseUrl },
          { '@type': 'ListItem', 'position': 2, 'name': raceName, 'item': canonicalUrl }
        ]
      }
    };
  }

  // Render accessible text content for unit page
  const renderUnitAccessibleContent = () => {
    if (!selectedEntityId) return null;

    const unit = units.get(selectedEntityId);
    const unitName = unit?.name || formatUnitName(selectedEntityId);
    const race = unit?.race || selectedEntityId.split('-')[0] as Race;
    const raceName = formatRaceName(race);
    const stats = getChangeStats(selectedEntityId, patches);
    const dateRange = getDateRange(filteredPatches);

    return (
      <div className="sr-only">
        <h2>Balance Change Log: {unitName}</h2>
        <p>
          The {raceName} {unitName} has received {filteredPatches.length} balance patches
          from {dateRange.start} to {dateRange.end}, including {stats.buffs} buffs
          and {stats.nerfs} nerfs.
        </p>

        {filteredPatches.map(patch => {
          const entity = patch.entities.get(selectedEntityId);
          if (!entity) return null;

          return (
            <section key={patch.version} aria-labelledby={`patch-${patch.version}`}>
              <h3 id={`patch-${patch.version}`}>
                <a href={patch.url} target="_blank" rel="noopener noreferrer">
                  Patch {patch.version}
                </a> - {formatDate(patch.date)}
              </h3>
              <ul>
                {entity.changes.map((change, i) => (
                  <li key={i}>
                    <strong>{formatChangeType(change.change_type)}:</strong> {change.raw_text}
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    );
  };

  // Render accessible text content for race page
  const renderRaceAccessibleContent = () => {
    if (!selectedRace || selectedEntityId) return null;

    const raceName = formatRaceName(selectedRace);
    const dateRange = getDateRange(filteredPatches);

    // Group by unit
    const unitPatches = new Map<string, ProcessedPatchData[]>();
    filteredPatches.forEach(patch => {
      patch.entities.forEach((_, id) => {
        if (id.startsWith(selectedRace)) {
          if (!unitPatches.has(id)) unitPatches.set(id, []);
          unitPatches.get(id)!.push(patch);
        }
      });
    });

    const sortedUnits = Array.from(unitPatches.entries())
      .sort((a, b) => b[1].length - a[1].length);

    return (
      <div className="sr-only">
        <h2>{raceName} Balance Change Overview</h2>
        <p>
          The {raceName} faction has received balance changes in {filteredPatches.length} patches
          from {dateRange.start} to {dateRange.end}, affecting {sortedUnits.length} different
          units, buildings, and abilities.
        </p>

        <h3>Units with Balance Changes</h3>
        <ul>
          {sortedUnits.map(([id, patchList]) => {
            const unit = units.get(id);
            const name = unit?.name || formatUnitName(id);
            const stats = getChangeStats(id, patches);
            return (
              <li key={id}>
                {name}: {patchList.length} patches ({stats.buffs} buffs, {stats.nerfs} nerfs)
              </li>
            );
          })}
        </ul>
      </div>
    );
  };

  return (
    <>
      <Helmet>
        <title>{title}</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={canonicalUrl} />

        {/* Open Graph */}
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:url" content={canonicalUrl} />
        <meta property="og:type" content="website" />
        <meta property="og:image" content={`${baseUrl}/sc2_balance_timeline.png`} />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={`${baseUrl}/sc2_balance_timeline.png`} />

        {/* JSON-LD */}
        {jsonLd && (
          <script type="application/ld+json">
            {JSON.stringify(jsonLd)}
          </script>
        )}
      </Helmet>

      {/* Accessible text alternative - visually hidden but read by screen readers and indexed by search engines */}
      {renderUnitAccessibleContent()}
      {renderRaceAccessibleContent()}
    </>
  );
}
