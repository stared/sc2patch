import { useEffect, useState, useRef } from 'react';
import { loadPatchesData, createUnitsMap, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, EntityWithPosition, Race } from './types';
import { PatchGridRenderer } from './d3';
import { Tooltip } from './components/Tooltip';
import { Header } from './components/Header';
import { FilterStatus } from './components/FilterStatus';
import {
  getEraFromVersion,
  eraColors,
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

    rendererRef.current.render({
      patches: sortedAndFilteredPatches,
      selectedEntityId,
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
          <Header selectedEra={selectedEra} setSelectedEra={setSelectedEra} />

          <FilterStatus
            filteredPatches={filteredPatches}
            selectedEra={selectedEra}
            setSelectedEra={setSelectedEra}
            selectedEntityId={selectedEntityId}
            setSelectedEntityId={setSelectedEntityId}
            selectedRace={selectedRace}
            setSelectedRace={setSelectedRace}
            units={units}
          />
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
