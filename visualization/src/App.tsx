import { useEffect, useState, useRef } from 'react';
import { loadPatchesData, createUnitsMap, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, ProcessedChange, EntityWithPosition, Race } from './types';
import { PatchGridRenderer } from './utils/patchGridRenderer';
import {
  getChangeIndicator,
  getChangeColor,
  getEraFromVersion,
  type ChangeType,
  eraData,
  eraColors,
  eraOrder,
  raceColors,
  changeTypeConfig,
  changeTypeOrder,
  type Era
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
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

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
              <a href="https://github.com/stared/sc2-balance-timeline/issues/new?template=factual_error.yml" target="_blank" rel="noopener noreferrer" className="attribution-source report-link">report error</a>
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

          {tooltip.visible && tooltip.entity && (
            <div
              className="tooltip"
              style={{
                left: `${tooltip.entity.x}px`,
                top: `${tooltip.entity.y}px`,
                transform: 'translate(-50%, -100%)',
                marginTop: '-10px'
              }}
            >
              <h4>{tooltip.entity.name || 'Unknown'}</h4>
              {!selectedEntityId && (
                <ul>
                  {tooltip.entity.changes.map((change: ProcessedChange, i: number) => (
                    <li key={i}>
                      <span style={{ color: getChangeColor(change.change_type as ChangeType), fontWeight: 'bold' }}>
                        {getChangeIndicator(change.change_type as ChangeType)}
                      </span>
                      {change.text}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App
