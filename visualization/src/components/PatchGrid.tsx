import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
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

// Layout constants
const CELL_SIZE = 48;
const CELL_GAP = 6;
const PATCH_HEIGHT = 80;
const PATCH_LABEL_WIDTH = 120;
const RACE_COLUMN_WIDTH = 250;

// Entity with position for tooltip display
type EntityWithPosition = ProcessedEntity & { x: number; y: number };

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
}

export function PatchGrid({ patches, units, selectedEntityId, onEntitySelect }: PatchGridProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{
    entity: EntityWithPosition | null;
    visible: boolean;
  }>({ entity: null, visible: false });

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 1400;

    // Clear previous render
    svg.selectAll('*').remove();

    // Calculate which patches to show
    const visiblePatches = patches.map(patch => ({
      patch,
      visible: !selectedEntityId || patch.entities.has(selectedEntityId)
    }));

    // Calculate Y positions for patches (accounting for hidden ones)
    let currentY = 80;
    const patchRows: PatchRow[] = visiblePatches.map((item) => {
      const row = {
        ...item,
        y: item.visible ? currentY : -1000 // Off-screen if not visible
      };
      if (item.visible) {
        currentY += PATCH_HEIGHT;
      }
      return row;
    });

    const height = currentY + 100;
    svg.attr('width', width).attr('height', height);

    // Define gradients FIRST (after clearing, so always create fresh)
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

    // Create main container
    const container = svg.append('g').attr('class', 'patch-container');

    // Render patches
    const patchGroups = container
      .selectAll<SVGGElement, PatchRow>('.patch-row-group')
      .data(patchRows, d => d.patch.version)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('class', 'patch-row-group')
            .attr('transform', d => `translate(0, ${d.y})`)
            .style('opacity', d => d.visible ? 1 : 0);
          return g;
        },
        update => update,
        exit => exit
          .transition()
          .duration(300)
          .style('opacity', 0)
          .remove()
      );

    // Transition patches to new positions
    patchGroups
      .transition()
      .duration(600)
      .ease(d3.easeCubicOut)
      .attr('transform', d => `translate(0, ${d.y})`)
      .style('opacity', d => d.visible ? 1 : 0);

    // Render patch content
    patchGroups.each(function(rowData) {
      const g = d3.select(this);
      const { patch, visible } = rowData;

      if (!visible) return;

      // Clear previous content
      g.selectAll('*').remove();

      // Patch label
      const patchLabel = g.append('g')
        .attr('class', 'patch-label')
        .attr('transform', `translate(0, 20)`);

      patchLabel.append('text')
        .attr('class', 'patch-version-text')
        .attr('x', 10)
        .attr('y', 0)
        .style('fill', '#4a9eff')
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

      // Entity cells
      const entities: EntityItem[] = [];

      if (selectedEntityId) {
        // Filtered view: show only selected entity
        const entity = patch.entities.get(selectedEntityId);
        if (entity) {
          entities.push({
            id: `${selectedEntityId}-${patch.version}`,
            entityId: selectedEntityId,
            patchVersion: patch.version,
            entity,
            x: PATCH_LABEL_WIDTH + 40,
            y: 20,
            visible: true
          });
        }
      } else {
        // Grid view: show all entities by race
        const races = ['terran', 'zerg', 'protoss', 'neutral'] as const;

        races.forEach((race, raceIndex) => {
          const raceEntities: Array<[string, ProcessedEntity]> = [];
          patch.entities.forEach((entity, entityId) => {
            if ((entity.race || 'neutral') === race) {
              raceEntities.push([entityId, entity]);
            }
          });

          raceEntities.forEach(([entityId, entity], entityIndex) => {
            const col = Math.floor(entityIndex / 1); // Wrap entities
            const row = entityIndex % 1;
            entities.push({
              id: `${entityId}-${patch.version}`,
              entityId,
              patchVersion: patch.version,
              entity,
              x: PATCH_LABEL_WIDTH + raceIndex * RACE_COLUMN_WIDTH + col * (CELL_SIZE + CELL_GAP),
              y: row * (CELL_SIZE + CELL_GAP),
              visible: true
            });
          });
        });
      }

      // Render entity cells with D3
      const entityGroups = g.selectAll<SVGGElement, EntityItem>('.entity-cell-group')
        .data(entities, d => d.id)
        .join(
          enter => {
            const eg = enter.append('g')
              .attr('class', 'entity-cell-group')
              .attr('transform', d => `translate(${d.x}, ${d.y})`)
              .style('opacity', 0);

            // Background rect
            eg.append('rect')
              .attr('width', CELL_SIZE)
              .attr('height', CELL_SIZE)
              .attr('rx', 4)
              .style('fill', 'url(#cellGradient)')
              .style('stroke', d => {
                const entity = d.entity;
                if (entity.status === 'buff') return '#4a9eff';
                if (entity.status === 'nerf') return '#ff4444';
                if (entity.status === 'mixed') return '#ff9933';
                const race = (entity.race || 'neutral') as keyof typeof RACE_COLORS;
                return RACE_COLORS[race];
              })
              .style('stroke-width', 2)
              .style('cursor', 'pointer');

            // Image
            eg.append('image')
              .attr('width', CELL_SIZE)
              .attr('height', CELL_SIZE)
              .attr('href', d => `${import.meta.env.BASE_URL}assets/units/${d.entityId}.png`)
              .attr('preserveAspectRatio', 'xMidYMid slice')
              .style('clip-path', 'inset(0 round 4px)')
              .style('pointer-events', 'none');

            eg.on('click', (event, d) => {
              event.stopPropagation();
              onEntitySelect(selectedEntityId === d.entityId ? null : d.entityId);
            });

            eg.on('mouseenter', (event, d) => {
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

            eg.on('mouseleave', () => {
              setTooltip({ entity: null, visible: false });
            });

            return eg.transition()
              .duration(400)
              .style('opacity', 1);
          },
          update => update,
          exit => exit
            .transition()
            .duration(300)
            .style('opacity', 0)
            .remove()
        );

      // Transition entity positions
      entityGroups
        .transition()
        .duration(600)
        .ease(d3.easeCubicOut)
        .attr('transform', d => `translate(${d.x}, ${d.y})`);

      // Render changes text if filtered
      if (selectedEntityId) {
        const entity = patch.entities.get(selectedEntityId);
        if (entity) {
          const changesGroup = g.append('g')
            .attr('class', 'changes-group')
            .attr('transform', `translate(${PATCH_LABEL_WIDTH + 140}, 10)`);

          entity.changes.forEach((change: ProcessedChange, i: number) => {
            const indicator = change.change_type === 'buff' ? '+ '
                           : change.change_type === 'nerf' ? '− '
                           : change.change_type === 'mixed' ? '± '
                           : '';

            const indicatorColor = change.change_type === 'buff' ? '#4a9eff'
                                 : change.change_type === 'nerf' ? '#ff4444'
                                 : change.change_type === 'mixed' ? '#ff9933'
                                 : '#ccc';

            const changeText = changesGroup.append('text')
              .attr('x', 0)
              .attr('y', i * 18)
              .style('fill', '#ccc')
              .style('font-size', '13px');

            changeText.append('tspan')
              .style('fill', indicatorColor)
              .style('font-weight', 'bold')
              .text(indicator);

            changeText.append('tspan')
              .text(change.text);
          });
        }
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
            {tooltip.entity.changes.map((change: ProcessedChange, i: number) => {
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
      )}
    </div>
  );
}
