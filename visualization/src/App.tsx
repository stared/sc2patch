import { useEffect, useState, useRef } from 'react';
import { loadPatchesData, createUnitsMap, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, EntityWithPosition, Race } from './types';
import { PatchGridRenderer } from './utils/patchGridRenderer';
import { Tooltip } from './components/Tooltip';
import {
  getEraFromVersion,
  eraData,
  eraColors,
  eraOrder,
  raceColors,
  changeTypeConfig,
  changeTypeOrder,
  type Era,
} from './utils/uxSettings';

type SortOrder = 'newest' | 'oldest';

function App() {
  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedRace, setSelectedRace] = useState<Race | null>(null);
  const [selectedEra, setSelectedEra] = useState<Era | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const svgRef = useRef<SVGSVGElement>(null);
  const rendererRef = useRef<PatchGridRenderer | null>(null);
  const prevSelectedIdRef = useRef<string | null>(null);
  const prevSelectedRaceRef = useRef<Race | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const [tooltipPosition, setTooltipPosition] = useState<{ left: number; top: number; flipped: boolean }>({ left: 0, top: 0, flipped: false });

  // Calculate tooltip position - left or right of icon, FIXED distance
  useEffect(() => {
    if (!tooltip.visible || !tooltip.entity || !tooltipRef.current) return;

    const ICON_SIZE = 48;
    const GAP = ICON_SIZE / 2; // exactly 24px, NEVER more
    const EDGE_PADDING = 8;
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const { x: iconCenterX, y: iconCenterY } = tooltip.entity;
    const iconLeft = iconCenterX - ICON_SIZE / 2;
    const iconRight = iconCenterX + ICON_SIZE / 2;

    // Decide: left or right based on which side has room for tooltip
    const spaceOnRight = window.innerWidth - iconRight - GAP;
    const spaceOnLeft = iconLeft - GAP;
    const fitsOnRight = spaceOnRight >= tooltipRect.width + EDGE_PADDING;
    const fitsOnLeft = spaceOnLeft >= tooltipRect.width + EDGE_PADDING;

    // Prefer right, but use left if right doesn't fit and left does
    const placeOnRight = fitsOnRight || (!fitsOnLeft && spaceOnRight >= spaceOnLeft);

    // Position with FIXED gap - no clamping that would increase gap
    const left = placeOnRight
      ? iconRight + GAP
      : iconLeft - GAP - tooltipRect.width;

    // Vertical: center tooltip with icon center, clamp to viewport
    let top = iconCenterY - tooltipRect.height / 2;
    top = Math.max(EDGE_PADDING, Math.min(top, window.innerHeight - tooltipRect.height - EDGE_PADDING));

    setTooltipPosition({ left, top, flipped: !placeOnRight });
  }, [tooltip.visible, tooltip.entity]);

  // Read URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const unit = params.get('unit');
    if (unit) setSelectedEntityId(unit);
  }, []);

  // Update URL when selection changes
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (selectedEntityId) {
      params.set('unit', selectedEntityId);
    } else {
      params.delete('unit');
    }
    const newUrl = params.toString() ? `?${params}` : window.location.pathname;
    window.history.replaceState(null, '', newUrl);
  }, [selectedEntityId]);

  // Handle browser back/forward
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      setSelectedEntityId(params.get('unit'));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // Load and validate single JSON file with Zod
        const data = await loadPatchesData();

        // Convert to Map for quick lookup
        const unitsMap = createUnitsMap(data.units);

        // Process patches for visualization
        const processedPatches = processPatches(data.patches, unitsMap);

        setUnits(unitsMap);
        setPatches(processedPatches);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // Sort and filter patches
  const sortedAndFilteredPatches = (() => {
    let result = [...patches];

    // Sort by date
    result.sort((a, b) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return sortOrder === 'newest' ? dateB - dateA : dateA - dateB;
    });

    // Filter by era
    if (selectedEra) {
      result = result.filter(patch => getEraFromVersion(patch.version) === selectedEra);
    }

    // Filter by race
    if (selectedRace) {
      result = result.filter(patch =>
        Array.from(patch.entities.values()).some(entity =>
          (entity.race || 'neutral') === selectedRace
        )
      );
    }

    return result;
  })();

  // Render visualization
  useEffect(() => {
    if (!svgRef.current || patches.length === 0) return;

    if (!rendererRef.current) {
      rendererRef.current = new PatchGridRenderer(svgRef.current);
    }

    const prevSelectedId = prevSelectedIdRef.current;
    prevSelectedIdRef.current = selectedEntityId;
    const prevSelectedRace = prevSelectedRaceRef.current;
    prevSelectedRaceRef.current = selectedRace;

    rendererRef.current.render({
      patches: sortedAndFilteredPatches,
      selectedEntityId,
      prevSelectedId,
      prevSelectedRace,
      onEntitySelect: setSelectedEntityId,
      setTooltip,
      unitsMap: units,
      selectedRace,
      sortOrder,
      setSortOrder,
      setSelectedRace
    });
  }, [sortedAndFilteredPatches, selectedEntityId, units, selectedRace, selectedEra, sortOrder, windowWidth]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>Loading SC2 Patch Data...</h2>
          <p style={{ color: '#666' }}>Fetching patches and unit information</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center', color: '#ff4444' }}>
          <h2>Error Loading Data</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const filteredPatches = selectedEntityId
    ? sortedAndFilteredPatches.filter(patch => patch.entities.has(selectedEntityId))
    : sortedAndFilteredPatches;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          {/* Top row: Title + Attribution */}
          <div className="header-top">
            <div className="header-title-group">
              <h1 className="header-title">
                15 Years of StarCraft II <span style={{ color: changeTypeConfig.mixed.color }}>Balance Changes</span> Visualized
              </h1>
            </div>
            <div className="attribution">
              <span className="attribution-author">by <a href="https://p.migdal.pl" target="_blank" rel="noopener noreferrer">Piotr Migdał</a></span>
              <a href="https://github.com/stared/sc2-balance-timeline" target="_blank" rel="noopener noreferrer" className="attribution-source">source code</a>
            </div>
          </div>

          {/* Era Timeline */}
          <div className="era-timeline">
            {eraOrder.map((era, i) => (
              <button
                key={era}
                className={`timeline-segment ${selectedEra === era ? 'active' : ''} ${selectedEra && selectedEra !== era ? 'inactive' : ''}`}
                style={{ '--segment-color': eraColors[era] } as React.CSSProperties}
                onClick={() => setSelectedEra(selectedEra === era ? null : era)}
                title={`${eraData[era].name} (${eraData[era].version})`}
              >
                <div className="segment-label">{eraData[era].short}</div>
                <div className="segment-track">
                  <div className="segment-line" />
                </div>
                <div className="segment-date">{eraData[era].releaseDate}{i === eraOrder.length - 1 && <span className="segment-date-now">now</span>}</div>
              </button>
            ))}
          </div>

          {/* Filter Status */}
          <div className="filter-status">
            {(() => {
              // Compute date range from actual filtered patches
              const dates = filteredPatches.map(p => new Date(p.date)).sort((a, b) => a.getTime() - b.getTime());
              const formatDate = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
              const startDate = dates.length > 0 ? formatDate(dates[0]) : '';
              const endDate = dates.length > 0 ? formatDate(dates[dates.length - 1]) : '';

              return (
                <>
                  Showing {filteredPatches.length} patches with{' '}
                  {changeTypeOrder.map((type, i) => (
                    <span key={type}>
                      <span
                        className="filter-chip"
                        style={{ borderColor: changeTypeConfig[type].color, '--chip-color': changeTypeConfig[type].color } as React.CSSProperties}
                      >
                        {changeTypeConfig[type].label}
                      </span>
                      {i === 0 && ', '}
                      {i === 1 && ', and '}
                    </span>
                  ))}
                  {' '}balance changes from {startDate} to {endDate} covering{' '}
                  {selectedEra ? (
                    <button
                      className="filter-chip active"
                      style={{ borderColor: eraColors[selectedEra], '--chip-color': eraColors[selectedEra] } as React.CSSProperties}
                      onClick={() => setSelectedEra(null)}
                    >
                      {eraData[selectedEra].name} ×
                    </button>
                  ) : (
                    <span>the whole timeline</span>
                  )}
                  {' '}and affecting{' '}
                  {selectedEntityId ? (
                    <button
                      className="filter-chip active"
                      style={{ borderColor: raceColors[units.get(selectedEntityId)?.race || 'neutral'], '--chip-color': raceColors[units.get(selectedEntityId)?.race || 'neutral'] } as React.CSSProperties}
                      onClick={() => setSelectedEntityId(null)}
                    >
                      {units.get(selectedEntityId)?.name || selectedEntityId} ×
                    </button>
                  ) : selectedRace ? (
                    <button
                      className="filter-chip active"
                      style={{ borderColor: raceColors[selectedRace], '--chip-color': raceColors[selectedRace] } as React.CSSProperties}
                      onClick={() => setSelectedRace(null)}
                    >
                      {selectedRace.charAt(0).toUpperCase() + selectedRace.slice(1)} ×
                    </button>
                  ) : (
                    <span>all races</span>
                  )}
                  . Hover and click to explore.
                </>
              );
            })()}
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="patch-grid-container" style={{ width: '100%', minHeight: '100vh' }}>
          <svg
            ref={svgRef}
            style={{
              background: '#0a0a0a',
              display: 'block',
              width: '100%',
              height: 'auto'
            }}
          />
        </div>

        <footer className="app-footer" style={{ '--wol-color': eraColors.wol } as React.CSSProperties}>
          <p>
            <span className="footer-wol">StarCraft II: Wings of Liberty</span> was released worldwide on July 27, 2010.
            See its <a href="https://www.youtube.com/watch?v=VSGmPpidDvo" target="_blank" rel="noopener noreferrer">epic cinematic teaser</a>, showcasing Blizzard's legendary animation craft.
          </p>
        </footer>
      </main>

      <Tooltip
        ref={tooltipRef}
        entity={tooltip.entity}
        visible={tooltip.visible}
        position={tooltipPosition}
        selectedEntityId={selectedEntityId}
      />
    </div>
  );
}

export default App
