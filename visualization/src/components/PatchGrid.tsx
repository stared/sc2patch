import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ProcessedPatchData, ProcessedEntity, ProcessedChange, Unit, EntityWithPosition } from '../types';
import { layout, timing, raceColors, getChangeIndicator, getChangeColor } from '../utils/uxSettings';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  selectedEntityId: string | null;
  onEntitySelect: (entityId: string | null) => void;
}

interface EntityItem {
  id: string;
  entityId: string;
  patchVersion: string;
  entity: ProcessedEntity;
  x: number;
  y: number;
  visible: boolean;
}

interface PatchRow {
  patch: ProcessedPatchData;
  y: number;
  visible: boolean;
  height: number;
}

export function PatchGrid({ patches, units, selectedEntityId, onEntitySelect }: PatchGridProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const prevSelectedIdRef = useRef<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  useEffect(() => {
    // Animation state - must be calculated INSIDE useEffect for correct timing
    const prevSelectedId = prevSelectedIdRef.current;
    const wasFiltered = prevSelectedId !== null;
    const isFiltered = selectedEntityId !== null;
    const isDeselecting = wasFiltered && !isFiltered;
    const isSelecting = !wasFiltered && isFiltered;

    // Update ref for next render
    prevSelectedIdRef.current = selectedEntityId;

    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 1400;

    // Calculate layout
    const cellsPerRow = Math.floor(layout.raceColumnWidth / (layout.cellSize + layout.cellGap));

    const visiblePatches = patches.map(patch => {
      const visible = !selectedEntityId || patch.entities.has(selectedEntityId);

      let maxRows = 1;
      if (visible && !selectedEntityId) {
        const races = ['terran', 'zerg', 'protoss', 'neutral'] as const;
        races.forEach(race => {
          let count = 0;
          patch.entities.forEach((entity) => {
            if ((entity.race || 'neutral') === race) count++;
          });
          const rows = Math.ceil(count / cellsPerRow);
          maxRows = Math.max(maxRows, rows);
        });
      }

      const height = 40 + maxRows * (layout.cellSize + layout.cellGap) + 10;

      return { patch, visible, height };
    });

    // Calculate Y positions
    let currentY = 80;
    const patchRows: PatchRow[] = visiblePatches.map((item) => {
      const row = {
        ...item,
        y: item.visible ? currentY : -1000
      };
      if (item.visible) {
        currentY += item.height;
      }
      return row;
    });

    // Set SVG height
    let fullGridHeight = 80;
    visiblePatches.forEach(item => {
      fullGridHeight += item.height;
    });
    const svgHeight = fullGridHeight + 200;

    svg.attr('width', width).attr('height', svgHeight);

    // Setup gradients and clip paths (once)
    if (svg.select('defs').empty()) {
      const defs = svg.append('defs');

      const gradient = defs.append('linearGradient')
        .attr('id', 'cellGradient')
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '100%')
        .attr('y2', '100%');

      gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#1a1a1a');

      gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#151515');

      const clipPath = defs.append('clipPath')
        .attr('id', 'roundedCorners');

      clipPath.append('rect')
        .attr('width', layout.cellSize)
        .attr('height', layout.cellSize)
        .attr('rx', 4)
        .attr('ry', 4);
    }

    // Get or create main container
    if (svg.select('.patch-container').empty()) {
      svg.append('g').attr('class', 'patch-container');
    }
    const container = svg.select<SVGGElement>('.patch-container');

    // Render patches
    const patchGroups = container
      .selectAll<SVGGElement, PatchRow>('.patch-row-group')
      .data(patchRows, d => d.patch.version)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('class', 'patch-row-group')
            .attr('transform', d => `translate(0, ${d.y})`)
            .style('opacity', d => {
              if (isDeselecting) return 0;
              return d.visible ? 1 : 0;
            });
          return g;
        },
        update => update,
        exit => exit
          .transition()
          .duration(300)
          .style('opacity', 0)
          .remove()
      );

    // Patch transitions
    if (isDeselecting) {
      patchGroups.each(function(d) {
        const patch = d3.select(this);
        const wasVisible = prevSelectedId && d.patch.entities.has(prevSelectedId);

        if (wasVisible) {
          patch
            .transition()
            .duration(timing.move)
            .ease(d3.easeCubicOut)
            .attr('transform', `translate(0, ${d.y})`);
        } else {
          patch
            .attr('transform', `translate(0, ${d.y})`)
            .transition()
            .delay(timing.move)
            .duration(timing.patchFade)
            .style('opacity', d.visible ? 1 : 0);
        }
      });
    } else {
      patchGroups
        .transition()
        .duration(timing.patchFade)
        .style('opacity', d => d.visible ? 1 : 0)
        .transition()
        .duration(timing.patchMove)
        .ease(d3.easeCubicOut)
        .attr('transform', d => `translate(0, ${d.y})`);
    }

    // Render patch content
    patchGroups.each(function(rowData) {
      const g = d3.select(this);
      const { patch, visible } = rowData;

      if (!visible) return;

      // Patch label
      if (g.select('.patch-label').empty()) {
        const patchLabel = g.append('g')
          .attr('class', 'patch-label')
          .attr('transform', `translate(0, 20)`);

        patchLabel.append('text')
          .attr('class', 'patch-version-text')
          .attr('x', 10)
          .attr('y', 0)
          .style('fill', raceColors.terran)
          .style('font-size', '14px')
          .style('font-weight', '600')
          .style('cursor', 'pointer')
          .text(patch.version)
          .on('click', () => window.open(patch.url, '_blank'));

        patchLabel.append('text')
          .attr('class', 'patch-date-text')
          .attr('x', 10)
          .attr('y', 16)
          .style('fill', '#666')
          .style('font-size', '11px')
          .text(patch.date.split('-').slice(0, 2).join('-'));
      }

      // Entity cells
      const entities: EntityItem[] = [];

      if (selectedEntityId) {
        const entity = patch.entities.get(selectedEntityId);
        if (entity) {
          entities.push({
            id: `${selectedEntityId}-${patch.version}`,
            entityId: selectedEntityId,
            patchVersion: patch.version,
            entity,
            x: layout.patchLabelWidth + 40,
            y: 0,
            visible: true
          });
        }
      } else {
        const races = ['terran', 'zerg', 'protoss', 'neutral'] as const;

        races.forEach((race, raceIndex) => {
          const raceEntities: Array<[string, ProcessedEntity]> = [];
          patch.entities.forEach((entity, entityId) => {
            if ((entity.race || 'neutral') === race) {
              raceEntities.push([entityId, entity]);
            }
          });

          raceEntities.forEach(([entityId, entity], entityIndex) => {
            const row = Math.floor(entityIndex / cellsPerRow);
            const col = entityIndex % cellsPerRow;

            entities.push({
              id: `${entityId}-${patch.version}`,
              entityId,
              patchVersion: patch.version,
              entity,
              x: layout.patchLabelWidth + raceIndex * layout.raceColumnWidth + col * (layout.cellSize + layout.cellGap),
              y: row * (layout.cellSize + layout.cellGap),
              visible: true
            });
          });
        });
      }

      // Render entity cells
      const entityGroups = g.selectAll<SVGGElement, EntityItem>('.entity-cell-group')
        .data(entities, d => d.id)
        .join(
          enter => {
            const eg = enter.append('g')
              .attr('class', 'entity-cell-group')
              .attr('transform', d => `translate(${d.x}, ${d.y})`)
              .style('opacity', isDeselecting ? 0 : 1);

            eg.append('rect')
              .attr('width', layout.cellSize)
              .attr('height', layout.cellSize)
              .attr('rx', 4)
              .style('fill', 'url(#cellGradient)')
              .style('stroke', d => {
                const entity = d.entity;
                if (entity.status === 'buff') return getChangeColor('buff');
                if (entity.status === 'nerf') return getChangeColor('nerf');
                if (entity.status === 'mixed') return getChangeColor('mixed');
                const race = (entity.race || 'neutral') as keyof typeof raceColors;
                return raceColors[race];
              })
              .style('stroke-width', 2)
              .style('cursor', 'pointer');

            eg.append('image')
              .attr('width', layout.cellSize)
              .attr('height', layout.cellSize)
              .attr('href', d => `${import.meta.env.BASE_URL}assets/units/${d.entityId}.png`)
              .attr('clip-path', 'url(#roundedCorners)')
              .attr('preserveAspectRatio', 'xMidYMid slice')
              .style('pointer-events', 'none');

            return eg;
          },
          update => update,
          exit => exit
            .transition()
            .duration(timing.fadeOut)
            .style('opacity', 0)
            .remove()
        );

      // Event handlers
      entityGroups.on('click', (event, d) => {
        event.stopPropagation();
        onEntitySelect(selectedEntityId === d.entityId ? null : d.entityId);
      });

      entityGroups.on('mouseenter', (event, d) => {
        if (!selectedEntityId) {
          const rect = (event.target as SVGElement).getBoundingClientRect();
          setTooltip({
            entity: {
              ...d.entity,
              name: units.get(d.entityId)?.name || d.entity.name || d.entityId,
              x: rect.left + rect.width / 2,
              y: rect.top
            },
            visible: true
          });
        }
      });

      entityGroups.on('mouseleave', () => {
        setTooltip({ entity: null, visible: false });
      });

      // Entity transitions
      if (isSelecting) {
        const shouldFadeOut = (d: EntityItem) => d.entityId !== selectedEntityId;

        entityGroups
          .transition()
          .duration(timing.fadeOut)
          .style('opacity', d => shouldFadeOut(d) ? 0 : 1)
          .transition()
          .duration(timing.move)
          .ease(d3.easeCubicOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`);
      } else if (isDeselecting) {
        const wasSelected = (d: EntityItem) => d.entityId === prevSelectedId;

        entityGroups.each(function(d) {
          const element = d3.select(this);

          if (wasSelected(d)) {
            element
              .transition()
              .duration(timing.move)
              .ease(d3.easeCubicOut)
              .attr('transform', `translate(${d.x}, ${d.y})`);
          } else {
            element
              .transition()
              .delay(timing.move)
              .duration(timing.fadeIn)
              .style('opacity', 1);
          }
        });
      } else {
        entityGroups
          .transition()
          .duration(timing.move)
          .ease(d3.easeCubicOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`);
      }

      // Render changes text if filtered
      if (selectedEntityId) {
        const entity = patch.entities.get(selectedEntityId);
        if (entity && g.select('.changes-group').empty()) {
          const changesGroup = g.append('g')
            .attr('class', 'changes-group')
            .attr('transform', `translate(${layout.patchLabelWidth + 140}, 10)`)
            .style('opacity', 0);

          entity.changes.forEach((change: ProcessedChange, i: number) => {
            const changeText = changesGroup.append('text')
              .attr('x', 0)
              .attr('y', i * 18)
              .style('fill', '#ccc')
              .style('font-size', '13px');

            changeText.append('tspan')
              .style('fill', getChangeColor(change.change_type))
              .style('font-weight', 'bold')
              .text(getChangeIndicator(change.change_type));

            changeText.append('tspan')
              .text(change.text);
          });

          changesGroup
            .transition()
            .delay(timing.changesDelay)
            .duration(timing.fadeIn)
            .style('opacity', 1);
        }
      } else {
        g.select('.changes-group').remove();
      }
    });

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

      {/* Tooltip */}
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
                <span style={{ color: getChangeColor(change.change_type), fontWeight: 'bold' }}>
                  {getChangeIndicator(change.change_type)}
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
