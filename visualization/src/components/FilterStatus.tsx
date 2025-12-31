import { ProcessedPatchData, Unit, Race } from '../types';
import {
  eraData,
  eraColors,
  raceColors,
  changeTypeConfig,
  changeTypeOrder,
  type Era,
} from '../utils/uxSettings';

interface FilterStatusProps {
  filteredPatches: ProcessedPatchData[];
  selectedEra: Era | null;
  setSelectedEra: (era: Era | null) => void;
  selectedEntityId: string | null;
  setSelectedEntityId: (id: string | null) => void;
  selectedRace: Race | null;
  setSelectedRace: (race: Race | null) => void;
  units: Map<string, Unit>;
}

export function FilterStatus({
  filteredPatches,
  selectedEra,
  setSelectedEra,
  selectedEntityId,
  setSelectedEntityId,
  selectedRace,
  setSelectedRace,
  units,
}: FilterStatusProps) {
  // Compute date range from actual filtered patches
  const dates = filteredPatches.map(p => new Date(p.date)).sort((a, b) => a.getTime() - b.getTime());
  const formatDate = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  const startDate = dates.length > 0 ? formatDate(dates[0]) : '';
  const endDate = dates.length > 0 ? formatDate(dates[dates.length - 1]) : '';

  return (
    <div className="filter-status">
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
    </div>
  );
}
