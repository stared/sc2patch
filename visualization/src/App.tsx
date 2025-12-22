import { useEffect, useState, useRef } from 'react';
import { loadUnits, loadPatches, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, ProcessedChange, EntityWithPosition, Race } from './types';
import { PatchGridRenderer } from './utils/patchGridRenderer';
import { getChangeIndicator, getChangeColor, type ChangeType, expansionData, expansionColors, type Expansion } from './utils/uxSettings';

type SortOrder = 'newest' | 'oldest';

function App() {
  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedRace, setSelectedRace] = useState<Race | null>(null);
  const [selectedExpansion, setSelectedExpansion] = useState<Expansion | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const svgRef = useRef<SVGSVGElement>(null);
  const rendererRef = useRef<PatchGridRenderer | null>(null);
  const prevSelectedIdRef = useRef<string | null>(null);
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

        const [unitsData, patchesData] = await Promise.all([
          loadUnits(),
          loadPatches()
        ]);

        const processedPatches = processPatches(patchesData, unitsData);

        setUnits(unitsData);
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

  // Helper to determine expansion from patch date
  const getExpansionFromDate = (dateStr: string): Expansion => {
    const date = new Date(dateStr);
    const hotsRelease = new Date('2013-03-12');
    const lotvRelease = new Date('2015-11-10');
    if (date < hotsRelease) return 'wol';
    if (date < lotvRelease) return 'hots';
    return 'lotv';
  };

  // Sort and filter patches
  const sortedAndFilteredPatches = (() => {
    let result = [...patches];

    // Sort by date
    result.sort((a, b) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return sortOrder === 'newest' ? dateB - dateA : dateA - dateB;
    });

    // Filter by expansion
    if (selectedExpansion) {
      result = result.filter(patch => getExpansionFromDate(patch.date) === selectedExpansion);
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

    rendererRef.current.render({
      patches: sortedAndFilteredPatches,
      selectedEntityId,
      prevSelectedId,
      onEntitySelect: setSelectedEntityId,
      setTooltip,
      unitsMap: units,
      selectedRace,
      sortOrder,
      setSortOrder,
      setSelectedRace
    });
  }, [sortedAndFilteredPatches, selectedEntityId, units, selectedRace, selectedExpansion, sortOrder, windowWidth]);

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
                15 Years of StarCraft II Balance Changes <span className="highlight">Visualized</span>
              </h1>
            </div>
            <div className="attribution">
              <span className="attribution-author">by <a href="https://p.migdal.pl" target="_blank" rel="noopener noreferrer">Piotr Migdał</a></span>
              <a href="https://github.com/stared/sc2patch" target="_blank" rel="noopener noreferrer" className="attribution-source">source code</a>
            </div>
          </div>

          {/* Era Timeline Bar - CLICKABLE */}
          <div className="era-bar">
            {(['wol', 'hots', 'lotv'] as const).map((exp) => (
              <button
                key={exp}
                className={`era-segment era-${exp} ${selectedExpansion === exp ? 'selected' : ''}`}
                style={{
                  width: `${expansionData[exp].percent}%`,
                  backgroundColor: expansionColors[exp]
                }}
                onClick={() => setSelectedExpansion(selectedExpansion === exp ? null : exp)}
                title={expansionData[exp].name}
              >
                <span className="era-label">{expansionData[exp].short}</span>
                <span className="era-count">({expansionData[exp].patches})</span>
              </button>
            ))}
          </div>

          {/* Bottom row: Filter info + Legend */}
          <div className="header-bottom">
            <div className="filter-info">
              {selectedExpansion ? (
                <>
                  <span>Showing {filteredPatches.length} {expansionData[selectedExpansion].name} patches</span>
                  <button
                    className="clear-filter-btn"
                    onClick={() => setSelectedExpansion(null)}
                    title="Clear expansion filter"
                  >
                    ✕
                  </button>
                </>
              ) : selectedEntityId ? (
                <>
                  <span>Showing {filteredPatches.length} patches affecting</span>
                  <span className="selected-unit">
                    <span className="selected-unit-name">{units.get(selectedEntityId)?.name || selectedEntityId}</span>
                    <button
                      className="clear-filter-btn"
                      onClick={() => setSelectedEntityId(null)}
                      title="Clear filter"
                    >
                      ✕
                    </button>
                  </span>
                </>
              ) : (
                <span className="filter-label">
                  Click any unit to see its balance history
                </span>
              )}
            </div>
            <div className="legend">
              <div className="legend-item">
                <span className="legend-dot buff"></span>
                <span>Buff</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot nerf"></span>
                <span>Nerf</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot mixed"></span>
                <span>Mixed</span>
              </div>
            </div>
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

          {!selectedEntityId && tooltip.visible && tooltip.entity && (
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
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App
