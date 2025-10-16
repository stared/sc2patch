import { useEffect, useRef, useState } from 'react';
import { ProcessedChange, EntityWithPosition, PatchGridProps } from '../types';
import { getChangeIndicator, getChangeColor, type ChangeType } from '../utils/uxSettings';
import { PatchGridRenderer } from '../utils/patchGridRenderer';

export function PatchGrid({ patches, units, selectedEntityId, onEntitySelect }: PatchGridProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const rendererRef = useRef<PatchGridRenderer | null>(null);
  const prevSelectedIdRef = useRef<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  useEffect(() => {
    if (!rendererRef.current) {
      rendererRef.current = new PatchGridRenderer(svgRef.current!);
    }

    const prevSelectedId = prevSelectedIdRef.current;
    prevSelectedIdRef.current = selectedEntityId;

    rendererRef.current.render(
      patches,
      selectedEntityId,
      prevSelectedId,
      onEntitySelect,
      setTooltip,
      units
    );
  }, [patches, selectedEntityId, units, onEntitySelect]);

  return (
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
          <h4>{tooltip.entity.name || 'Unknown'}</h4>
          <ul>
            {tooltip.entity.changes.map((change: ProcessedChange, i: number) => (
              <li key={i}>
                <span style={{ color: getChangeColor(change.change_type as ChangeType), fontWeight: 'bold' }}>
                  {getChangeIndicator(change.change_type as ChangeType)}
                </span>
                {change.text}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
