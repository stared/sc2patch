import { forwardRef } from 'react';
import { ProcessedChange, EntityWithPosition, Race } from '../types';
import {
  raceColors,
  changeTypeConfig,
  getChangeColor,
  getChangeIndicator,
  type ChangeType,
} from '../utils/uxSettings';

interface TooltipProps {
  entity: EntityWithPosition | null;
  visible: boolean;
  position: { left: number; top: number };
  selectedEntityId: string | null;
}

export const Tooltip = forwardRef<HTMLDivElement, TooltipProps>(
  ({ entity, visible, position, selectedEntityId }, ref) => {
    if (!entity) return null;

    return (
      <div
        ref={ref}
        className={`tooltip ${visible ? 'visible' : ''}`}
        style={{
          '--race-color': raceColors[(entity.race as Race) || 'neutral'],
          '--change-color': entity.status ? changeTypeConfig[entity.status as ChangeType].color : '#888',
          left: `${position.left}px`,
          top: `${position.top}px`,
        } as React.CSSProperties}
      >
        <h4>{entity.name || 'Unknown'}</h4>
        {!selectedEntityId && (
          <ul>
            {entity.changes.map((change: ProcessedChange, i: number) => (
              <li key={i}>
                <span style={{ color: getChangeColor(change.change_type as ChangeType), fontWeight: 'bold' }}>
                  {getChangeIndicator(change.change_type as ChangeType)}
                </span>
                {change.text}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }
);

Tooltip.displayName = 'Tooltip';
