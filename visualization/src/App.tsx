import { useEffect, useState, useRef } from 'react';
import { loadUnits, loadPatches, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, ProcessedChange, EntityWithPosition } from './types';
import { PatchGridRenderer } from './utils/patchGridRenderer';
import { getChangeIndicator, getChangeColor, type ChangeType } from './utils/uxSettings';

function App() {
  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const svgRef = useRef<SVGSVGElement>(null);
  const rendererRef = useRef<PatchGridRenderer | null>(null);
  const prevSelectedIdRef = useRef<string | null>(null);

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

  // Render visualization
  useEffect(() => {
    if (!svgRef.current || patches.length === 0) return;

    if (!rendererRef.current) {
      rendererRef.current = new PatchGridRenderer(svgRef.current);
    }

    const prevSelectedId = prevSelectedIdRef.current;
    prevSelectedIdRef.current = selectedEntityId;

    rendererRef.current.render(
      patches,
      selectedEntityId,
      prevSelectedId,
      setSelectedEntityId,
      setTooltip,
      units
    );
  }, [patches, selectedEntityId, units]);

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
    ? patches.filter(patch => patch.entities.has(selectedEntityId))
    : patches;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1 className="header-title">StarCraft II Balance Changes</h1>
          <div className="header-subtitle">
            {selectedEntityId ? (
              <>
                <span className="filter-label">
                  Showing {filteredPatches.length} of {patches.length} patches affecting
                </span>
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
              <span className="filter-label">Tracking {patches.length} balance patches across all units</span>
            )}
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
