import React, { useState } from 'react';
import { ProcessedPatchData, ViewMode, Unit } from '../types';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  viewMode: ViewMode;
}

const RACE_COLORS = {
  terran: '#4a9eff',
  zerg: '#c874e9',
  protoss: '#ffd700',
  neutral: '#888'
} as const;

interface EntityCellProps {
  entityId: string;
  entity: any;
  units: Map<string, Unit>;
  onHover: (entity: any) => void;
  onLeave: () => void;
}

function EntityCell({ entityId, entity, units, onHover, onLeave }: EntityCellProps) {
  const race = (entity.race || 'neutral') as keyof typeof RACE_COLORS;
  const color = RACE_COLORS[race];

  // Determine outline color based on status
  const getOutlineColor = () => {
    if (entity.status === 'buff') return '#4a9eff'; // Blue for buffs
    if (entity.status === 'nerf') return '#ff4444'; // Red for nerfs
    if (entity.status === 'mixed') return '#888'; // Grey for mixed
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
      className="entity-cell"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={onLeave}
      style={{
        borderColor: outlineColor,
        borderWidth: '2px',
        borderStyle: 'solid'
      }}
    >
      {hasImage ? (
        <img
          src={`/assets/units/${entityId}.png`}
          alt={entityId}
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/assets/units/placeholder.svg';
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

export function PatchGrid({ patches, units, viewMode }: PatchGridProps) {
  const [tooltip, setTooltip] = useState<{
    entity: any;
    visible: boolean;
  }>({ entity: null, visible: false });

  const handleEntityHover = (entity: any) => {
    setTooltip({ entity, visible: true });
  };

  const handleEntityLeave = () => {
    setTooltip({ entity: null, visible: false });
  };

  // Group entities by race for each patch
  const patchesWithGroupedEntities = patches.map(patch => {
    const byRace = { terran: [], zerg: [], protoss: [], neutral: [] } as Record<string, Array<[string, any]>>;

    patch.entities.forEach((entity, entityId) => {
      const race = (entity.race || 'neutral') as keyof typeof byRace;
      byRace[race].push([entityId, entity]);
    });

    return {
      ...patch,
      byRace
    };
  });

  return (
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

      {/* Patch rows */}
      {patchesWithGroupedEntities.map(patch => (
        <div key={patch.version} className="patch-row">
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
                />
              ))}
            </div>
          ))}
        </div>
      ))}

      {/* Tooltip */}
      {tooltip.visible && tooltip.entity && (
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
            {tooltip.entity.changes.map((change: any, i: number) => {
              const isChange = typeof change === 'object' && change.text;
              const changeText = isChange ? change.text : change;
              const changeType = isChange ? change.change_type : null;

              // Get indicator based on change type
              const indicator = changeType === 'buff' ? '+ '
                             : changeType === 'nerf' ? '− '
                             : changeType === 'mixed' ? '± '
                             : '';

              const indicatorColor = changeType === 'buff' ? '#4a9eff'
                                   : changeType === 'nerf' ? '#ff4444'
                                   : changeType === 'mixed' ? '#888'
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
  );
}