import { ProcessedPatchData, Unit, ProcessedChange } from '../types';

interface UnitViewProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
}

const RACE_COLORS = {
  terran: '#4a9eff',
  zerg: '#c874e9',
  protoss: '#ffd700',
  neutral: '#888'
} as const;

interface UnitWithChanges {
  unitId: string;
  unit: Unit | null;
  changesByPatch: Map<string, ProcessedChange[]>;
}

export function UnitView({ patches, units }: UnitViewProps) {
  // Collect all units that have changes and organize by unit
  const unitsWithChanges = new Map<string, UnitWithChanges>();

  patches.forEach(patch => {
    patch.entities.forEach((entity, entityId) => {
      if (!unitsWithChanges.has(entityId)) {
        unitsWithChanges.set(entityId, {
          unitId: entityId,
          unit: units.get(entityId) || null,
          changesByPatch: new Map()
        });
      }
      unitsWithChanges.get(entityId)!.changesByPatch.set(patch.version, entity.changes);
    });
  });

  // Group units by race
  const unitsByRace = {
    terran: [] as UnitWithChanges[],
    zerg: [] as UnitWithChanges[],
    protoss: [] as UnitWithChanges[],
    neutral: [] as UnitWithChanges[]
  };

  unitsWithChanges.forEach(unitData => {
    const race = (unitData.unit?.race || 'neutral') as keyof typeof unitsByRace;
    unitsByRace[race].push(unitData);
  });

  // Sort units within each race by name
  (['terran', 'zerg', 'protoss', 'neutral'] as const).forEach(race => {
    unitsByRace[race].sort((a, b) => {
      const nameA = a.unit?.name || a.unitId;
      const nameB = b.unit?.name || b.unitId;
      return nameA.localeCompare(nameB);
    });
  });

  return (
    <div className="unit-view">
      {(['terran', 'zerg', 'protoss', 'neutral'] as const).map(race => (
        <div key={race} className="race-section">
          {unitsByRace[race].length > 0 && (
            <>
              <h2 style={{ color: RACE_COLORS[race], marginTop: '40px', marginBottom: '20px' }}>
                {race.charAt(0).toUpperCase() + race.slice(1)}
              </h2>
              {unitsByRace[race].map(unitData => {
                const hasImage = unitData.unit?.type === 'unit' || unitData.unit?.type === 'building';
                const color = RACE_COLORS[race];

                return (
                  <div key={unitData.unitId} className="unit-row">
                    <div className="unit-header">
                      <div className="unit-icon">
                        {hasImage ? (
                          <img
                            src={`${import.meta.env.BASE_URL}assets/units/${unitData.unitId}.png`}
                            alt={unitData.unitId}
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = `${import.meta.env.BASE_URL}assets/units/placeholder.svg`;
                            }}
                          />
                        ) : (
                          <div className="upgrade-cell" style={{ backgroundColor: `${color}20` }}>
                            <span style={{ color }}>{(unitData.unit?.name || unitData.unitId.split('-').pop() || '?').charAt(0).toUpperCase()}</span>
                          </div>
                        )}
                      </div>
                      <div className="unit-name">
                        <h3>{unitData.unit?.name || unitData.unitId}</h3>
                      </div>
                    </div>
                    <div className="unit-changes">
                      {patches.map(patch => {
                        const changes = unitData.changesByPatch.get(patch.version);
                        if (!changes) return null;

                        return (
                          <div key={patch.version} className="patch-changes-item">
                            <div className="patch-changes-header">
                              <a href={patch.url} target="_blank" rel="noopener noreferrer">
                                {patch.version}
                              </a>
                              <span className="patch-date">{patch.date}</span>
                            </div>
                            <ul>
                              {changes.map((change, i) => {
                                const indicator = change.change_type === 'buff' ? '+ '
                                              : change.change_type === 'nerf' ? '− '
                                              : change.change_type === 'mixed' ? '± '
                                              : '';

                                const indicatorColor = change.change_type === 'buff' ? '#4a9eff'
                                                     : change.change_type === 'nerf' ? '#ff4444'
                                                     : change.change_type === 'mixed' ? '#ff9933'
                                                     : '#ccc';

                                return (
                                  <li key={i}>
                                    <span style={{ color: indicatorColor, fontWeight: 'bold' }}>{indicator}</span>
                                    {change.text}
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
