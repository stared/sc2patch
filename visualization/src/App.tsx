import { useEffect, useState } from 'react';
import { PatchGrid } from './components/PatchGrid';
import { loadUnits, loadPatches, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit } from './types';

function App() {
  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // Load units and patches data
        const [unitsData, patchesData] = await Promise.all([
          loadUnits(),
          loadPatches()
        ]);

        // Process the patches
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

  // Filter patches if an entity is selected
  const filteredPatches = selectedEntityId
    ? patches.filter(patch => patch.entities.has(selectedEntityId))
    : patches;

  return (
    <div className="app-container">
      {/* Header */}
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

      {/* Main Content */}
      <main className="app-main">
        <PatchGrid
          patches={patches}
          units={units}
          totalPatches={patches.length}
          selectedEntityId={selectedEntityId}
          onEntitySelect={setSelectedEntityId}
        />
      </main>
    </div>
  );
}

export default App
