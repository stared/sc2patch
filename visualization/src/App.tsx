import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { loadPatchesData, createUnitsMap, processPatches } from './utils/dataLoader';
import { ProcessedPatchData, Unit, EntityWithPosition, Race } from './types';
import { PatchGridRenderer } from './d3';
import { Tooltip } from './components/Tooltip';
import { Header } from './components/Header';
import { FilterStatus } from './components/FilterStatus';
import { SEOContent } from './components/SEOContent';
import {
  getEraFromVersion,
  eraColors,
  eraData,
  type Era,
} from './utils/uxSettings';

type SortOrder = 'newest' | 'oldest';

// Convert entity_id (e.g., "zerg-hydralisk") to URL path (e.g., "/zerg/hydralisk")
function entityIdToPath(entityId: string): string {
  const [race, ...rest] = entityId.split('-');
  return `/${race}/${rest.join('-')}`;
}

// Parse URL path to get race, entity_id, or patch version
function parseUrlPath(pathname: string): { race: Race | null; entityId: string | null; patchVersion: string | null } {
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length === 0) {
    return { race: null, entityId: null, patchVersion: null };
  }
  // Check for patch URL first: /patch/5.0.9
  if (parts[0] === 'patch' && parts.length >= 2) {
    return { race: null, entityId: null, patchVersion: parts[1] };
  }
  const race = parts[0] as Race;
  const validRaces: Race[] = ['terran', 'zerg', 'protoss', 'neutral'];
  if (!validRaces.includes(race)) {
    return { race: null, entityId: null, patchVersion: null };
  }
  if (parts.length === 1) {
    // Race-only URL like /protoss/
    return { race, entityId: null, patchVersion: null };
  }
  // Unit URL like /protoss/zealot
  const unitParts = parts.slice(1);
  return { race, entityId: `${race}-${unitParts.join('-')}`, patchVersion: null };
}

function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const [units, setUnits] = useState<Map<string, Unit>>(new Map());
  const [patches, setPatches] = useState<ProcessedPatchData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedRace, setSelectedRace] = useState<Race | null>(null);
  // Track race filter state before unit selection (to restore on deselect)
  const [raceBeforeUnitSelect, setRaceBeforeUnitSelect] = useState<Race | null>(null);
  const [selectedEra, setSelectedEra] = useState<Era | null>(null);
  const [selectedPatchVersion, setSelectedPatchVersion] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const svgRef = useRef<SVGSVGElement>(null);
  const rendererRef = useRef<PatchGridRenderer | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const prevWindowWidthRef = useRef(window.innerWidth);
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

  // Sync state with URL path (React Router handles back/forward)
  useEffect(() => {
    const { race, entityId, patchVersion } = parseUrlPath(location.pathname);
    if (entityId !== selectedEntityId) {
      setSelectedEntityId(entityId);
    }
    // Only sync race from URL when no unit is selected
    // When a unit is selected, the race in URL is implicit from unit ID, not a race filter
    if (!entityId && race !== selectedRace) {
      setSelectedRace(race);
    }
    // Sync patch version from URL
    if (patchVersion !== selectedPatchVersion) {
      setSelectedPatchVersion(patchVersion);
    }
  }, [location.pathname, selectedEntityId, selectedRace, selectedPatchVersion]);

  // Navigate to unit URL when selecting (instead of just setting state)
  const handleEntitySelect = useCallback((entityId: string | null) => {
    if (entityId) {
      // Save current race filter before selecting unit
      setRaceBeforeUnitSelect(selectedRace);
      navigate(entityIdToPath(entityId));
    } else {
      // Deselect: restore previous race state (or go home if none was selected)
      if (raceBeforeUnitSelect) {
        navigate(`/${raceBeforeUnitSelect}/`);
      } else {
        navigate('/');
      }
      setRaceBeforeUnitSelect(null);
    }
  }, [navigate, selectedRace, raceBeforeUnitSelect]);

  // Navigate to race URL when selecting race
  const handleRaceSelect = useCallback((race: Race | null) => {
    if (race) {
      navigate(`/${race}/`);
    } else {
      navigate('/');
    }
  }, [navigate]);

  // Navigate to patch URL when selecting patch
  const handlePatchSelect = useCallback((version: string | null) => {
    if (version) {
      navigate(`/patch/${version}`);
    } else {
      navigate('/');
    }
  }, [navigate]);

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

    // Detect if this render is due to resize
    const isResize = windowWidth !== prevWindowWidthRef.current;
    prevWindowWidthRef.current = windowWidth;

    rendererRef.current.render({
      patches: sortedAndFilteredPatches,
      selectedEntityId,
      onEntitySelect: handleEntitySelect,
      setTooltip,
      unitsMap: units,
      selectedRace,
      sortOrder,
      setSortOrder,
      setSelectedRace: handleRaceSelect,
      selectedPatchVersion,
      onPatchSelect: handlePatchSelect
    }, { immediate: isResize });
  }, [sortedAndFilteredPatches, selectedEntityId, units, selectedRace, selectedEra, sortOrder, windowWidth, handleEntitySelect, handleRaceSelect, selectedPatchVersion, handlePatchSelect]);

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
            setSelectedEntityId={handleEntitySelect}
            selectedRace={selectedRace}
            setSelectedRace={handleRaceSelect}
            units={units}
          />
        </div>
      </header>

      <main className="app-main">
        <div className="patch-grid-container" style={{ width: '100%', minHeight: '100vh' }}>
          {filteredPatches.length === 0 && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '60vh',
              color: '#888',
              textAlign: 'center'
            }}>
              <img
                src={`${import.meta.env.BASE_URL}sc2_balance_changeges_logo.jpg`}
                alt="Balance Changes Logo"
                style={{ maxWidth: '250px', marginBottom: '16px', borderRadius: '8px', opacity: 0.8 }}
              />
              <div style={{ fontSize: '14px', color: '#888', marginTop: '10px' }}>
                Apparently, everything is perfectly balanced for {selectedEntityId ? units.get(selectedEntityId)?.name : (selectedRace ? selectedRace.charAt(0).toUpperCase() + selectedRace.slice(1) : 'everyone')} in {selectedEra ? eraData[selectedEra].name : 'this era'}.
              </div>
            </div>
          )}
          <svg
            ref={svgRef}
            role="img"
            style={{
              background: '#0a0a0a',
              display: filteredPatches.length === 0 ? 'none' : 'block',
              width: '100%',
              height: 'auto'
            }}
          />
        </div>

        <SEOContent
          selectedEntityId={selectedEntityId}
          selectedRace={selectedRace}
          units={units}
          patches={patches}
          filteredPatches={filteredPatches}
        />

        <footer className="app-footer" style={{ '--wol-color': eraColors.wol } as React.CSSProperties}>
          <p>
            <a href="https://en.wikipedia.org/wiki/StarCraft_II:_Wings_of_Liberty" target="_blank" rel="noopener noreferrer">StarCraft II: Wings of Liberty</a> was released worldwide on July 27, 2010. Even today, <a href="https://www.youtube.com/watch?v=VSGmPpidDvo" target="_blank" rel="noopener noreferrer">the cinematic teaser</a> is a treat to watch. A beautiful reminder of Blizzard's animation craft at its peak.
          </p>
        </footer>
      </main>

      <Tooltip
        ref={tooltipRef}
        entity={tooltip.entity}
        visible={tooltip.visible}
        position={tooltipPosition}
      />
    </div>
  );
}

export default App
