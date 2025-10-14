import { useEffect, useState } from 'react';
import { PatchGrid } from './components/PatchGrid';
import { loadUnits, loadPatches, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit } from './types';

function App() {
  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div>
      <div style={{ padding: '20px' }}>
        <h1 style={{ color: '#fff', marginBottom: '20px' }}>StarCraft II Balance Changes</h1>
        <p style={{ color: '#999', marginBottom: '30px' }}>
          Visualizing unit changes across {patches.length} patches
        </p>

        <div style={{ overflow: 'auto', background: '#111', borderRadius: '8px', padding: '20px' }}>
          <PatchGrid patches={patches} units={units} />
        </div>
      </div>
    </div>
  );
}

export default App
