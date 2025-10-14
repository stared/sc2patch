import React, { useState } from 'react';
import { ProcessedPatchData, ProcessedEntity, ProcessedChange, Unit } from '../types';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
}

const RACE_COLORS = {
  terran: '#4a9eff',
  zerg: '#c874e9',
  protoss: '#ffd700',
  neutral: '#888'
} as const;

const EXPANSION_COLORS = {
  wol: '#4a9eff',
  hots: '#c874e9',
  lotv: '#ffd700'
} as const;

// Determine expansion based on version
function getExpansion(version: string): 'wol' | 'hots' | 'lotv' {
  const majorVersion = parseInt(version.split('.')[0]);
  if (majorVersion === 1) return 'wol';
  if (majorVersion === 2) return 'hots';
  return 'lotv'; // 3.x, 4.x, 5.x
}

// Entity with position for tooltip display
type EntityWithPosition = ProcessedEntity & { x: number; y: number };

interface EntityCellProps {
  entityId: string;
  entity: ProcessedEntity;
  units: Map<string, Unit>;
  onHover: (entity: EntityWithPosition) => void;
  onLeave: () => void;
  onClick: () => void;
  isSelected: boolean;
}

function EntityCell({ entityId, entity, units, onHover, onLeave, onClick, isSelected }: EntityCellProps) {
  const race = (entity.race || 'neutral') as keyof typeof RACE_COLORS;
  const color = RACE_COLORS[race];

  // Determine outline color based on status
  const getOutlineColor = () => {
    if (entity.status === 'buff') return '#4a9eff'; // Blue for buffs
    if (entity.status === 'nerf') return '#ff4444'; // Red for nerfs
    if (entity.status === 'mixed') return '#ff9933'; // Orange for mixed (distinct from neutral grey)
    return color; // Race color by default
  };

  const outlineColor = getOutlineColor();

  const handleMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const entityWithPosition = {
      ...entity,
      name: units.get(entityId)?.name || entity.name || entityId,
      x: rect.left + rect.width / 2,
      y: rect.top
    };
    onHover(entityWithPosition);
  };

  // Check if entity is a unit or building (has image)
  const hasImage = entity.type === 'unit' || entity.type === 'building';

  return (
    <div
      className={`entity-cell ${isSelected ? 'selected' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
      style={{
        borderColor: outlineColor,
        borderWidth: isSelected ? '3px' : '2px',
        borderStyle: 'solid',
        cursor: 'pointer',
        opacity: isSelected ? 1 : 0.9
      }}
    >
      {hasImage ? (
        <img
          src={`${import.meta.env.BASE_URL}assets/units/${entityId}.png`}
          alt={entityId}
          onError={(e) => {
            (e.target as HTMLImageElement).src = `${import.meta.env.BASE_URL}assets/units/placeholder.svg`;
          }}
        />
      ) : (
        <div className="upgrade-cell" style={{ backgroundColor: `${color}20` }}>
          <span style={{ color }}>{(entity.name || entityId.split('-').pop() || '?').charAt(0).toUpperCase()}</span>
        </div>
      )}
    </div>
  );
}

export function PatchGrid({ patches, units }: PatchGridProps) {
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  const handleEntityHover = (entity: EntityWithPosition) => {
    if (!selectedEntityId) {
      setTooltip({ entity, visible: true });
    }
  };

  const handleEntityLeave = () => {
    setTooltip({ entity: null, visible: false });
  };

  const handleEntityClick = (entityId: string) => {
    setSelectedEntityId(selectedEntityId === entityId ? null : entityId);
    setTooltip({ entity: null, visible: false });
  };

  // Filter patches if an entity is selected
  const filteredPatches = selectedEntityId
    ? patches.filter(patch => patch.entities.has(selectedEntityId))
    : patches;

  // Get selected entity details
  const selectedEntity = selectedEntityId ? filteredPatches[0]?.entities.get(selectedEntityId) : null;
  const selectedUnit = selectedEntityId ? units.get(selectedEntityId) : null;

  // Group entities by race for each patch
  const patchesWithGroupedEntities = filteredPatches.map(patch => {
    const byRace = { terran: [], zerg: [], protoss: [], neutral: [] } as Record<string, Array<[string, ProcessedEntity]>>;

    patch.entities.forEach((entity, entityId) => {
      const race = (entity.race || 'neutral') as keyof typeof byRace;
      byRace[race].push([entityId, entity]);
    });

    return {
      ...patch,
      byRace,
      expansion: getExpansion(patch.version)
    };
  });

  return (
    <div className="patch-grid-container">
      {/* Entity Detail Panel */}
      {selectedEntityId && selectedEntity && (
        <div className="entity-detail-panel">
          <div className="entity-detail-header">
            <div className="entity-detail-image">
              {(selectedEntity.type === 'unit' || selectedEntity.type === 'building') ? (
                <img
                  src={`${import.meta.env.BASE_URL}assets/units/${selectedEntityId}.png`}
                  alt={selectedEntityId}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = `${import.meta.env.BASE_URL}assets/units/placeholder.svg`;
                  }}
                />
              ) : (
                <div className="upgrade-icon" style={{
                  backgroundColor: `${RACE_COLORS[selectedEntity.race as keyof typeof RACE_COLORS]}40`,
                  color: RACE_COLORS[selectedEntity.race as keyof typeof RACE_COLORS]
                }}>
                  {(selectedUnit?.name || selectedEntityId.split('-').pop() || '?').charAt(0).toUpperCase()}
                </div>
              )}
            </div>
            <div className="entity-detail-title">
              <h2>{selectedUnit?.name || selectedEntityId}</h2>
              <button onClick={() => handleEntityClick(selectedEntityId)} className="close-detail">
                ✕ Back to all entities
              </button>
            </div>
          </div>
          <div className="entity-detail-changes">
            <h3>All Changes ({filteredPatches.length} patches)</h3>
            {filteredPatches.map(patch => {
              const entity = patch.entities.get(selectedEntityId);
              return entity ? (
                <div key={patch.version} className="patch-changes">
                  <div className="patch-changes-header">
                    <a href={patch.url} target="_blank" rel="noopener noreferrer">
                      {patch.version}
                    </a>
                    <span className="patch-date">{patch.date}</span>
                  </div>
                  <ul>
                    {entity.changes.map((change: ProcessedChange, i: number) => {
                      const changeText = change.text;
                      const changeType = change.change_type;

                      const indicator = changeType === 'buff' ? '+ '
                                     : changeType === 'nerf' ? '− '
                                     : changeType === 'mixed' ? '± '
                                     : '';

                      const indicatorColor = changeType === 'buff' ? '#4a9eff'
                                           : changeType === 'nerf' ? '#ff4444'
                                           : changeType === 'mixed' ? '#ff9933'
                                           : '#ccc';

                      return (
                        <li key={i}>
                          <span style={{ color: indicatorColor, fontWeight: 'bold' }}>{indicator}</span>
                          {changeText}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : null;
            })}
          </div>
        </div>
      )}

      <div className="patch-grid">
        {/* Race headers */}
        <div className="race-headers">
          <div className="patch-label-space"></div>
          {(['terran', 'zerg', 'protoss', 'neutral'] as const).map(race => (
            <div key={race} className="race-header" style={{ color: RACE_COLORS[race] }}>
              {race.charAt(0).toUpperCase() + race.slice(1)}
            </div>
          ))}
        </div>

        {/* Patch rows with expansion separators */}
        {patchesWithGroupedEntities.map((patch, index) => {
          const prevExpansion = index > 0 ? patchesWithGroupedEntities[index - 1].expansion : null;
          const showExpansionBar = patch.expansion !== prevExpansion;

          return (
            <React.Fragment key={patch.version}>
              {showExpansionBar && (
                <div className="expansion-separator" style={{ backgroundColor: EXPANSION_COLORS[patch.expansion] }}>
                  <span>{patch.expansion.toUpperCase()}</span>
                </div>
              )}
              <div className="patch-row">
                <div className="patch-info">
                  <a href={patch.url} target="_blank" rel="noopener noreferrer" className="patch-version">
                    {patch.version}
                  </a>
                  <div className="patch-date">{patch.date.split('-').slice(0, 2).join('-')}</div>
                </div>

                {/* Race columns */}
                {(['terran', 'zerg', 'protoss', 'neutral'] as const).map(race => (
                  <div key={race} className="race-column">
                    {patch.byRace[race].map(([entityId, entity]) => (
                      <EntityCell
                        key={entityId}
                        entityId={entityId}
                        entity={entity}
                        units={units}
                        onHover={handleEntityHover}
                        onLeave={handleEntityLeave}
                        onClick={() => handleEntityClick(entityId)}
                        isSelected={entityId === selectedEntityId}
                      />
                    ))}
                  </div>
                ))}
              </div>
            </React.Fragment>
          );
        })}

        {/* Tooltip (only show when no entity selected) */}
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
            <h4>{tooltip.entity.name || tooltip.entity.id}</h4>
            <ul>
              {tooltip.entity.changes.map((change: ProcessedChange, i: number) => {
                const changeText = change.text;
                const changeType = change.change_type;

                // Get indicator based on change type
                const indicator = changeType === 'buff' ? '+ '
                               : changeType === 'nerf' ? '− '
                               : changeType === 'mixed' ? '± '
                               : '';

                const indicatorColor = changeType === 'buff' ? '#4a9eff'
                                     : changeType === 'nerf' ? '#ff4444'
                                     : changeType === 'mixed' ? '#ff9933'
                                     : '#ccc';

                return (
                  <li key={i}>
                    <span style={{ color: indicatorColor, fontWeight: 'bold' }}>{indicator}</span>
                    {changeText}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}