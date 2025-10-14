import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence, LayoutGroup, useAnimation } from 'framer-motion';
import { ProcessedPatchData, ProcessedEntity, ProcessedChange, Unit } from '../types';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  totalPatches: number;
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
  isVisible: boolean;
  onHover: (entity: EntityWithPosition) => void;
  onLeave: () => void;
  onClick: () => void;
  index?: number;
  isFiltered?: boolean;
}

function EntityCell({ entityId, entity, units, patchVersion, isVisible, onHover, onLeave, onClick, index = 0, isFiltered = false }: EntityCellProps) {
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

  if (!isVisible) {
    return null;
  }

  // Calculate staggered delay based on index - more sophisticated choreography
  const staggerDelay = isFiltered ? 0 : Math.min(index * 0.015, 0.3);
  const rowPosition = Math.floor(index / 4); // Assuming ~4 entities per row
  const waveDelay = rowPosition * 0.02; // Wave effect across rows

  return (
    <motion.div
      className="entity-cell"
      layoutId={`entity-${entityId}-${patchVersion}`}
      initial={{ opacity: 0, scale: 0, y: 30, rotateX: -15 }}
      animate={{
        opacity: 1,
        scale: 1,
        y: 0,
        rotateX: 0,
        transition: {
          delay: staggerDelay + waveDelay,
          duration: 0.5,
          ease: [0.16, 1, 0.3, 1], // More aggressive easeOutExpo curve
          opacity: { duration: 0.3, delay: staggerDelay + waveDelay },
          scale: {
            type: "spring",
            stiffness: 200,
            damping: 20,
            delay: staggerDelay + waveDelay
          }
        }
      }}
      exit={{
        opacity: 0,
        scale: 0.6,
        y: -20,
        rotateX: 10,
        transition: {
          duration: 0.25,
          ease: [0.7, 0, 0.84, 0] // easeInQuart for smooth exit
        }
      }}
      whileHover={{
        scale: 1.15,
        rotateZ: 1,
        transition: {
          type: "spring",
          stiffness: 300,
          damping: 15,
          mass: 0.5
        }
      }}
      whileTap={{ scale: 0.92, rotateZ: -1 }}
      transition={{
        layout: {
          type: "spring",
          stiffness: 400,
          damping: 30,
          mass: 0.8
        }
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

export function PatchGrid({ patches, units, totalPatches, selectedEntityId, onEntitySelect }: PatchGridProps) {
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

  // Don't filter patches - always show all, just hide entities
  const allPatches = patches;

  // Get selected entity details from first patch that has it
  const selectedEntity = selectedEntityId
    ? patches.find(p => p.entities.has(selectedEntityId))?.entities.get(selectedEntityId)
    : null;

  // Group entities by race for each patch
  const patchesWithGroupedEntities = allPatches.map(patch => {
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
    <LayoutGroup>
      <div className="patch-grid-container" data-filtered={!!selectedEntityId}>
        <div className={`patch-grid ${selectedEntityId ? 'filtered' : ''}`}>
          {/* Race headers with orchestrated animations */}
          <motion.div
            className={selectedEntityId ? "race-headers-filtered" : "race-headers"}
            layout
            transition={{
              type: "spring",
              stiffness: 250,
              damping: 30,
              mass: 0.8
            }}
          >
          <motion.div
            className="patch-label-space"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: 0.4,
              ease: [0.16, 1, 0.3, 1]
            }}
          />
          <AnimatePresence mode="popLayout" initial={false}>
            {selectedEntityId ? (
              // Show only the selected unit's race with smooth transition
              <motion.div
                key="filtered-race"
                className="race-header"
                initial={{ opacity: 0, y: -20, scale: 0.9 }}
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: 1,
                  transition: {
                    y: {
                      type: "spring",
                      stiffness: 300,
                      damping: 25
                    },
                    opacity: { duration: 0.3 },
                    scale: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
                  }
                }}
                exit={{
                  opacity: 0,
                  y: 20,
                  scale: 0.9,
                  transition: {
                    duration: 0.2,
                    ease: [0.7, 0, 0.84, 0]
                  }
                }}
                style={{ color: RACE_COLORS[selectedEntity?.race as keyof typeof RACE_COLORS || 'neutral'] }}
              >
                {(selectedEntity?.race || 'neutral').charAt(0).toUpperCase() + (selectedEntity?.race || 'neutral').slice(1)}
              </motion.div>
            ) : (
              // Show all races with wave animation
              (['terran', 'zerg', 'protoss', 'neutral'] as const).map((race, index) => (
                <motion.div
                  key={race}
                  className="race-header"
                  initial={{ opacity: 0, y: -15, scale: 0.8, rotateX: -30 }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    rotateX: 0,
                    transition: {
                      delay: index * 0.08,
                      y: {
                        type: "spring",
                        stiffness: 300,
                        damping: 22,
                        delay: index * 0.08
                      },
                      opacity: {
                        duration: 0.4,
                        delay: index * 0.08
                      },
                      scale: {
                        duration: 0.5,
                        delay: index * 0.08,
                        ease: [0.16, 1, 0.3, 1]
                      },
                      rotateX: {
                        duration: 0.6,
                        delay: index * 0.08,
                        ease: [0.16, 1, 0.3, 1]
                      }
                    }
                  }}
                  exit={{
                    opacity: 0,
                    y: 15,
                    scale: 0.8,
                    rotateX: 30,
                    transition: {
                      duration: 0.25,
                      delay: (3 - index) * 0.03, // Reverse stagger for exit
                      ease: [0.7, 0, 0.84, 0]
                    }
                  }}
                  style={{ color: RACE_COLORS[race], transformStyle: 'preserve-3d' }}
                >
                  {race.charAt(0).toUpperCase() + race.slice(1)}
                </motion.div>
              ))
            )}
          </AnimatePresence>
          {selectedEntityId && (
            <motion.div
              className="changes-header"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
            >
              Changes
            </motion.div>
          )}
          </motion.div>

          {/* Patch rows with expansion separators */}
          <AnimatePresence mode="wait" initial={false}>
            {patchesWithGroupedEntities.map((patch, patchIndex) => {
              const prevExpansion = patchIndex > 0 ? patchesWithGroupedEntities[patchIndex - 1].expansion : null;
              const showExpansionBar = patch.expansion !== prevExpansion;
              const hasSelectedEntity = selectedEntityId ? patch.entities.has(selectedEntityId) : false;

              // Only render patches that have the selected entity when filtering
              if (selectedEntityId && !hasSelectedEntity) {
                return null;
              }

              // Calculate cascade delay with exponential easing for cinematic effect
              const baseDelay = selectedEntityId ? 0.02 : 0.04;
              const rowDelay = Math.min(patchIndex * baseDelay, 0.8);
              const depthScale = 1 - (patchIndex * 0.001); // Subtle depth perception

              return (
                <React.Fragment key={patch.version}>
                  {showExpansionBar && !selectedEntityId && (
                    <motion.div
                      className="expansion-separator"
                      layout
                      initial={{ opacity: 0, scaleX: 0, scaleY: 0.5 }}
                      animate={{
                        opacity: 0.9,
                        scaleX: 1,
                        scaleY: 1,
                        transition: {
                          delay: rowDelay,
                          scaleX: {
                            type: "spring",
                            stiffness: 100,
                            damping: 20,
                            delay: rowDelay,
                            duration: 0.8
                          },
                          scaleY: {
                            delay: rowDelay + 0.2,
                            duration: 0.3
                          },
                          opacity: {
                            delay: rowDelay + 0.1,
                            duration: 0.4
                          }
                        }
                      }}
                      exit={{
                        opacity: 0,
                        scaleX: 0,
                        scaleY: 0.5,
                        transition: {
                          duration: 0.3,
                          ease: [0.7, 0, 1, 0.5]
                        }
                      }}
                      style={{
                        backgroundColor: EXPANSION_COLORS[patch.expansion],
                        transformOrigin: 'center',
                        filter: `brightness(${1 + Math.sin(patchIndex * 0.5) * 0.1})`
                      }}
                    >
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8, y: 10 }}
                        animate={{
                          opacity: 1,
                          scale: 1,
                          y: 0,
                          transition: {
                            delay: rowDelay + 0.4,
                            duration: 0.4,
                            ease: [0.16, 1, 0.3, 1]
                          }
                        }}
                      >
                        {patch.expansion.toUpperCase()}
                      </motion.span>
                    </motion.div>
                  )}
                  <motion.div
                    className={selectedEntityId ? "patch-row-filtered" : "patch-row"}
                    layout
                    layoutId={`patch-row-${patch.version}`}
                    initial={{
                      opacity: 0,
                      x: -50,
                      scale: 0.95,
                      filter: "blur(4px)"
                    }}
                    animate={{
                      opacity: 1,
                      x: 0,
                      scale: depthScale,
                      filter: "blur(0px)",
                      transition: {
                        delay: rowDelay,
                        x: {
                          type: "spring",
                          stiffness: 120,
                          damping: 25,
                          delay: rowDelay
                        },
                        opacity: {
                          duration: 0.4,
                          delay: rowDelay
                        },
                        scale: {
                          duration: 0.6,
                          delay: rowDelay,
                          ease: [0.16, 1, 0.3, 1]
                        },
                        filter: {
                          duration: 0.5,
                          delay: rowDelay + 0.1
                        }
                      }
                    }}
                    exit={{
                      opacity: 0,
                      x: 40,
                      scale: 0.9,
                      filter: "blur(4px)",
                      transition: {
                        duration: 0.25,
                        ease: [0.7, 0, 0.84, 0]
                      }
                    }}
                    transition={{
                      layout: {
                        type: "spring",
                        stiffness: 350,
                        damping: 28,
                        mass: 0.9
                      }
                    }}
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
                        <motion.div
                          className="unit-icon-cell"
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{
                            opacity: 1,
                            scale: 1,
                            transition: {
                              delay: rowDelay + 0.1,
                              duration: 0.3,
                              ease: [0.23, 1, 0.32, 1]
                            }
                          }}
                        >
                          <EntityCell
                            entityId={selectedEntityId}
                            entity={patch.entities.get(selectedEntityId)!}
                            units={units}
                            patchVersion={patch.version}
                            isVisible={true}
                            onHover={handleEntityHover}
                            onLeave={handleEntityLeave}
                            onClick={() => handleEntityClick(selectedEntityId)}
                            isFiltered={true}
                          />
                        </motion.div>
                        <motion.div
                          className="changes-list"
                          initial={{ opacity: 0, x: -20 }}
                          animate={{
                            opacity: 1,
                            x: 0,
                            transition: {
                              delay: rowDelay + 0.2,
                              duration: 0.4,
                              ease: [0.23, 1, 0.32, 1]
                            }
                          }}
                        >
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
                        </motion.div>
                      </>
                    ) : (
                      // Show all races with entities - orchestrated column animations
                      (['terran', 'zerg', 'protoss', 'neutral'] as const).map((race, raceIndex) => {
                        let entityIndex = raceIndex * 10; // Base index per race column
                        const columnDelay = rowDelay + (raceIndex * 0.06);
                        const isEmptyColumn = patch.byRace[race].length === 0;

                        return (
                          <motion.div
                            key={race}
                            className="race-column"
                            initial={{
                              opacity: 0,
                              x: -10 + (raceIndex * 5),
                              scale: 0.98
                            }}
                            animate={{
                              opacity: isEmptyColumn ? 0.3 : 1,
                              x: 0,
                              scale: 1,
                              transition: {
                                x: {
                                  type: "spring",
                                  stiffness: 200,
                                  damping: 20,
                                  delay: columnDelay
                                },
                                opacity: {
                                  duration: 0.4,
                                  delay: columnDelay,
                                  ease: [0.16, 1, 0.3, 1]
                                },
                                scale: {
                                  duration: 0.5,
                                  delay: columnDelay,
                                  ease: [0.16, 1, 0.3, 1]
                                }
                              }
                            }}
                            exit={{
                              opacity: 0,
                              x: 10 - (raceIndex * 5),
                              scale: 0.98,
                              transition: {
                                duration: 0.3,
                                delay: (3 - raceIndex) * 0.02,
                                ease: [0.7, 0, 0.84, 0]
                              }
                            }}
                          >
                            {patch.byRace[race].map(([entityId, entity], idx) => (
                              <EntityCell
                                key={`${entityId}-${patch.version}`}
                                entityId={entityId}
                                entity={entity}
                                units={units}
                                patchVersion={patch.version}
                                isVisible={true}
                                onHover={handleEntityHover}
                                onLeave={handleEntityLeave}
                                onClick={() => handleEntityClick(entityId)}
                                index={entityIndex + idx}
                                isFiltered={false}
                              />
                            ))}
                          </motion.div>
                        );
                      })
                    )}
                  </motion.div>
                </React.Fragment>
              );
            })}
          </AnimatePresence>

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
    </LayoutGroup>
  );
}