import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProcessedPatchData, ProcessedEntity, ProcessedChange, Unit } from '../types';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  selectedEntityId: string | null;
  onEntitySelect: (entityId: string | null) => void;
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
  patchVersion: string;
  onHover: (entity: EntityWithPosition) => void;
  onLeave: () => void;
  onClick: () => void;
}

function EntityCell({ entityId, entity, units, patchVersion, onHover, onLeave, onClick }: EntityCellProps) {
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
    <motion.div
      className="entity-cell"
      layoutId={`entity-${entityId}-${patchVersion}`}
      layout
      transition={{
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1]
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
      style={{
        borderColor: outlineColor,
        borderWidth: '2px',
        borderStyle: 'solid',
        cursor: 'pointer'
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
    </motion.div>
  );
}

export function PatchGrid({ patches, units, selectedEntityId, onEntitySelect }: PatchGridProps) {
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  const handleEntityHover = (entity: EntityWithPosition) => {
    if (!selectedEntityId) {
      setTooltip({ entity, visible: true });
    }
  };

  const handleEntityLeave = () => {
    setTooltip({ entity: null, visible: false });
  };

  const handleEntityClick = (entityId: string) => {
    onEntitySelect(selectedEntityId === entityId ? null : entityId);
    setTooltip({ entity: null, visible: false });
  };

  // Filter patches to only show ones with the selected entity
  const filteredPatches = selectedEntityId
    ? patches.filter(patch => patch.entities.has(selectedEntityId))
    : patches;

  // Get selected entity details from first patch that has it
  const selectedEntity = selectedEntityId
    ? patches.find(p => p.entities.has(selectedEntityId))?.entities.get(selectedEntityId)
    : null;

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
    <div className="patch-grid-container" data-filtered={!!selectedEntityId}>
      <div className={`patch-grid ${selectedEntityId ? 'filtered' : ''}`}>
        {/* Race headers */}
        <div className={selectedEntityId ? "race-headers-filtered" : "race-headers"}>
          <div className="patch-label-space" />
          <AnimatePresence mode="popLayout">
            {selectedEntityId ? (
              // Show only the selected unit's race
              <motion.div
                key="filtered-race"
                layout
                className="race-header"
                style={{ color: RACE_COLORS[selectedEntity?.race as keyof typeof RACE_COLORS || 'neutral'] }}
              >
                {(selectedEntity?.race || 'neutral').charAt(0).toUpperCase() + (selectedEntity?.race || 'neutral').slice(1)}
              </motion.div>
            ) : (
              // Show all races
              (['terran', 'zerg', 'protoss', 'neutral'] as const).map((race) => (
                <motion.div
                  key={race}
                  layout
                  className="race-header"
                  style={{ color: RACE_COLORS[race] }}
                >
                  {race.charAt(0).toUpperCase() + race.slice(1)}
                </motion.div>
              ))
            )}
          </AnimatePresence>
          {selectedEntityId && (
            <motion.div
              layout
              className="changes-header"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              Changes
            </motion.div>
          )}
        </div>

          {/* Patch rows with expansion separators */}
          {patchesWithGroupedEntities.map((patch, patchIndex) => {
            const prevExpansion = patchIndex > 0 ? patchesWithGroupedEntities[patchIndex - 1].expansion : null;
            const showExpansionBar = patch.expansion !== prevExpansion;

            return (
              <React.Fragment key={patch.version}>
                {showExpansionBar && !selectedEntityId && (
                  <div
                    className="expansion-separator"
                    style={{
                      backgroundColor: EXPANSION_COLORS[patch.expansion]
                    }}
                  >
                    <span>{patch.expansion.toUpperCase()}</span>
                  </div>
                )}
                <motion.div
                  layout
                  transition={{
                    duration: 0.3,
                    ease: [0.16, 1, 0.3, 1]
                  }}
                  className={selectedEntityId ? "patch-row-filtered" : "patch-row"}
                >
                  <div className="patch-info">
                    <a href={patch.url} target="_blank" rel="noopener noreferrer" className="patch-version">
                      {patch.version}
                    </a>
                    <div className="patch-date">{patch.date.split('-').slice(0, 2).join('-')}</div>
                  </div>

                  {selectedEntityId ? (
                    // Show selected entity with changes
                    <>
                      <div className="unit-icon-cell">
                        <EntityCell
                          entityId={selectedEntityId}
                          entity={patch.entities.get(selectedEntityId)!}
                          units={units}
                          patchVersion={patch.version}
                          onHover={handleEntityHover}
                          onLeave={handleEntityLeave}
                          onClick={() => handleEntityClick(selectedEntityId)}
                        />
                      </div>
                      <div className="changes-list">
                        <ul>
                          {patch.entities.get(selectedEntityId)?.changes.map((change: ProcessedChange, i: number) => {
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
                    </>
                  ) : (
                    // Show all races with entities
                    (['terran', 'zerg', 'protoss', 'neutral'] as const).map((race) => (
                      <div
                        key={race}
                        className="race-column"
                      >
                        {patch.byRace[race].map(([entityId, entity]) => (
                          <EntityCell
                            key={`${entityId}-${patch.version}`}
                            entityId={entityId}
                            entity={entity}
                            units={units}
                            patchVersion={patch.version}
                            onHover={handleEntityHover}
                            onLeave={handleEntityLeave}
                            onClick={() => handleEntityClick(entityId)}
                          />
                        ))}
                      </div>
                    ))
                  )}
                </motion.div>
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