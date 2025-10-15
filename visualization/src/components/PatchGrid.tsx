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
const PATCH_LABEL_WIDTH = 120;
const RACE_COLUMN_WIDTH = 250;

// Animation timing configuration (all values in milliseconds)
const ANIMATION_TIMING = {
  // When selecting a unit (grid → filtered view)
  FADE_OUT_DURATION: 600,        // Fade out irrelevant entities (2x 300ms)
  MOVE_DURATION: 800,            // Move to new positions (2x 400ms)
  CHANGES_DELAY: 1400,           // Delay before change notes appear (2x 700ms)
  CHANGES_FADE_IN: 600,          // Fade in change notes (2x 300ms)

  // When deselecting (filtered → grid view)
  DESELECT_MOVE_DURATION: 800,   // Move back to grid positions (2x 400ms)
  DESELECT_FADE_IN: 600,         // Fade in other entities (2x 300ms)

  // Patch transitions
  PATCH_FADE_DURATION: 600,      // Patch opacity transitions (2x 300ms)
  PATCH_MOVE_DURATION: 800,      // Patch position transitions (2x 400ms)
} as const;

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
    // Determine if we're selecting or deselecting
    const wasFiltered = prevSelectedIdRef.current !== null;
    const isFiltered = selectedEntityId !== null;
    const isDeselecting = wasFiltered && !isFiltered;
    const isSelecting = !wasFiltered && isFiltered;

    // Update ref for next render
    prevSelectedIdRef.current = selectedEntityId;
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 1400;

    // Calculate which patches to show and their heights
    const cellsPerRow = Math.floor(RACE_COLUMN_WIDTH / (CELL_SIZE + CELL_GAP));

    const visiblePatches = patches.map(patch => {
      const visible = !selectedEntityId || patch.entities.has(selectedEntityId);

      // Calculate height based on max rows in any race column
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

      const height = 40 + maxRows * (CELL_SIZE + CELL_GAP) + 10; // padding top + rows + padding bottom

      return {
        patch,
        visible,
        height
      };
    });

    // Calculate Y positions for patches (accounting for hidden ones)
    let currentY = 80;
    const patchRows: PatchRow[] = visiblePatches.map((item) => {
      const row = {
        ...item,
        y: item.visible ? currentY : -1000 // Off-screen if not visible
      };
      if (item.visible) {
        currentY += item.height;
      }
      return row;
    });

    const height = currentY + 100;
    svg.attr('width', width).attr('height', height);

    // Define gradients and clip paths once
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

      // Clip path for rounded corners on images
      const clipPath = defs.append('clipPath')
        .attr('id', 'roundedCorners');

      clipPath.append('rect')
        .attr('width', CELL_SIZE)
        .attr('height', CELL_SIZE)
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

    // Choreographed patch transitions:
    if (isDeselecting) {
      // When deselecting: previously visible patches move, new ones just fade in
      patchGroups.each(function(d) {
        const patch = d3.select(this);
        const wasVisible = prevSelectedIdRef.current && d.patch.entities.has(prevSelectedIdRef.current);

        if (wasVisible) {
          // Previously visible patch: move to new position
          patch
            .transition()
            .duration(ANIMATION_TIMING.DESELECT_MOVE_DURATION)
            .ease(d3.easeCubicOut)
            .attr('transform', `translate(0, ${d.y})`);
        } else {
          // Newly appearing patch: fade in at final position (no movement)
          patch
            .transition()
            .delay(ANIMATION_TIMING.DESELECT_MOVE_DURATION)
            .duration(ANIMATION_TIMING.PATCH_FADE_DURATION)
            .style('opacity', d.visible ? 1 : 0);
        }
      });
    } else {
      // When selecting or normal: fade out → move to new positions
      patchGroups
        .transition()
        .duration(ANIMATION_TIMING.PATCH_FADE_DURATION)
        .style('opacity', d => d.visible ? 1 : 0)
        .transition()
        .duration(ANIMATION_TIMING.PATCH_MOVE_DURATION)
        .ease(d3.easeCubicOut)
        .attr('transform', d => `translate(0, ${d.y})`);
    }

    // Render patch content
    patchGroups.each(function(rowData) {
      const g = d3.select(this);
      const { patch, visible } = rowData;

      if (!visible) return;

      // Patch label (create once or reuse)
      if (g.select('.patch-label').empty()) {
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
      }

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
            y: 0,  // Align with grid view positioning
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
            const row = Math.floor(entityIndex / cellsPerRow);
            const col = entityIndex % cellsPerRow;

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
              .style('opacity', isDeselecting ? 0 : 1);  // Start hidden when deselecting

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
              .attr('clip-path', 'url(#roundedCorners)')
              .attr('preserveAspectRatio', 'xMidYMid slice')
              .style('pointer-events', 'none');

            return eg;
          },
          update => update,
          exit => {
            // Fade out entities that are being removed
            return exit
              .transition()
              .duration(ANIMATION_TIMING.FADE_OUT_DURATION)
              .style('opacity', 0)
              .remove();
          }
        );

      // Update event handlers for all entity groups (must be outside join to capture current state)
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

      // Choreographed entity transitions:
      if (isSelecting) {
        // Selecting: Fade out → Move → Show changes
        const shouldFadeOut = (d: EntityItem) => d.entityId !== selectedEntityId;

        entityGroups
          .transition()
          .duration(ANIMATION_TIMING.FADE_OUT_DURATION)
          .style('opacity', d => shouldFadeOut(d) ? 0 : 1)
          .transition()
          .duration(ANIMATION_TIMING.MOVE_DURATION)
          .ease(d3.easeCubicOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`);
      } else if (isDeselecting) {
        // Deselecting: Selected unit moves back, others fade in at final position
        const wasSelected = (d: EntityItem) => d.entityId === prevSelectedIdRef.current;

        entityGroups.each(function(d) {
          const element = d3.select(this);

          if (wasSelected(d)) {
            // Previously selected entity: move to grid position, keep opacity 1
            element
              .transition()
              .duration(ANIMATION_TIMING.DESELECT_MOVE_DURATION)
              .ease(d3.easeCubicOut)
              .attr('transform', `translate(${d.x}, ${d.y})`);
          } else {
            // Newly appearing entities: fade in at current position (no movement)
            element
              .transition()
              .delay(ANIMATION_TIMING.DESELECT_MOVE_DURATION)
              .duration(ANIMATION_TIMING.DESELECT_FADE_IN)
              .style('opacity', 1);
          }
        });
      } else {
        // Normal update: just move
        entityGroups
          .transition()
          .duration(ANIMATION_TIMING.MOVE_DURATION)
          .ease(d3.easeCubicOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`);
      }

      // Render changes text if filtered
      // Step 3: Fade in after movement completes
      if (selectedEntityId) {
        const entity = patch.entities.get(selectedEntityId);
        if (entity && g.select('.changes-group').empty()) {
          // Create new changes group
          const changesGroup = g.append('g')
            .attr('class', 'changes-group')
            .attr('transform', `translate(${PATCH_LABEL_WIDTH + 140}, 10)`)
            .style('opacity', 0); // Start invisible

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

          // Fade in after fade out + movement complete
          changesGroup
            .transition()
            .delay(ANIMATION_TIMING.CHANGES_DELAY)
            .duration(ANIMATION_TIMING.CHANGES_FADE_IN)
            .style('opacity', 1);
        }
      } else {
        // Remove changes group when not filtering
        const existingChangesGroup = g.select('.changes-group');
        if (!existingChangesGroup.empty()) {
          existingChangesGroup.remove();
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
