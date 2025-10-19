import { select, type Selection } from 'd3-selection';
import { transition } from 'd3-transition';
import { easeCubicOut } from 'd3-ease';
import { ProcessedPatchData, ProcessedChange, EntityItem, PatchRow, RACES, Race, Unit, EntityWithPosition } from '../types';
import { layout, timing, raceColors, getChangeIndicator, getChangeColor, type ChangeType } from './uxSettings';

type TooltipState = {
  entity: EntityWithPosition | null;
  visible: boolean;
};

// Extend d3-selection to include transition
select.prototype.transition = transition;

export class PatchGridRenderer {
  private svg: Selection<SVGSVGElement, unknown, null, undefined>;

  constructor(svgElement: SVGSVGElement) {
    this.svg = select(svgElement);
    this.initializeDefs();
  }

  private initializeDefs(): void {
    if (!this.svg.select('defs').empty()) return;

    const defs = this.svg.append('defs');
    const gradient = defs.append('linearGradient')
      .attr('id', 'cellGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '100%').attr('y2', '100%');

    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#1a1a1a');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#151515');

    defs.append('clipPath').attr('id', 'roundedCorners')
      .append('rect')
      .attr('width', layout.cellSize)
      .attr('height', layout.cellSize)
      .attr('rx', 4).attr('ry', 4);
  }

  render(
    patches: ProcessedPatchData[],
    selectedEntityId: string | null,
    prevSelectedId: string | null,
    onEntitySelect: (entityId: string | null) => void,
    setTooltip: (tooltip: TooltipState) => void,
    unitsMap: Map<string, Unit>,
    selectedRace: Race | null = null
  ): void {
    const svgElement = this.svg.node();
    const containerWidth = svgElement?.parentElement?.clientWidth || 1400;
    const svgWidth = Math.min(containerWidth, 1400);

    const patchRows = this.calculateLayout(patches, selectedEntityId, svgWidth);
    const svgHeight = 80 + patchRows.reduce((sum, item) => sum + item.height, 0) + 200;
    this.svg.attr('width', svgWidth).attr('height', svgHeight);

    if (this.svg.select('.patch-container').empty()) {
      this.svg.append('g').attr('class', 'patch-container');
    }

    const isDeselecting = prevSelectedId !== null && selectedEntityId === null;
    const isSelecting = prevSelectedId === null && selectedEntityId !== null;

    const container = this.svg.select<SVGGElement>('.patch-container');
    const patchGroups = container
      .selectAll<SVGGElement, PatchRow>('.patch-row-group')
      .data(patchRows, d => d.patch.version)
      .join(
        enter => enter.append('g')
          .attr('class', 'patch-row-group')
          .attr('transform', d => `translate(0, ${d.y})`)
          .style('opacity', d => isDeselecting ? 0 : (d.visible ? 1 : 0)),
        update => update,
        exit => exit.transition().duration(300).style('opacity', 0).remove()
      );

    // Animate patches
    if (isDeselecting) {
      patchGroups.each(function(d) {
        const patch = select(this);
        const wasVisible = prevSelectedId && d.patch.entities.has(prevSelectedId);
        if (wasVisible) {
          patch.transition().duration(timing.move).ease(easeCubicOut)
            .attr('transform', `translate(0, ${d.y})`);
        } else {
          patch.attr('transform', `translate(0, ${d.y})`)
            .transition().delay(timing.move).duration(timing.fade)
            .style('opacity', d.visible ? 1 : 0);
        }
      });
    } else {
      patchGroups.transition().duration(timing.fade).style('opacity', d => d.visible ? 1 : 0)
        .transition().duration(timing.move).ease(easeCubicOut)
        .attr('transform', d => `translate(0, ${d.y})`);
    }

    // Render patch content
    patchGroups.each((rowData: PatchRow, i, nodes) => {
      const node = nodes[i];
      if (!node) return;
      const g = select<SVGGElement, PatchRow>(node);
      const { patch, visible } = rowData;
      if (!visible) return;

      this.renderPatchLabel(g, patch);
      this.renderEntities(g, patch, selectedEntityId, prevSelectedId, isSelecting, isDeselecting, onEntitySelect, setTooltip, unitsMap, svgWidth);
      this.renderChanges(g, patch, selectedEntityId);
    });
  }

  private calculateLayout(patches: ProcessedPatchData[], selectedEntityId: string | null, svgWidth: number): PatchRow[] {
    const availableWidth = svgWidth - layout.patchLabelWidth;
    const raceColumnWidth = selectedEntityId ? availableWidth : Math.floor(availableWidth / RACES.length);
    const cellsPerRow = Math.floor(raceColumnWidth / (layout.cellSize + layout.cellGap));

    const visiblePatches = patches.map(patch => {
      const visible = !selectedEntityId || patch.entities.has(selectedEntityId);
      let maxRows = 1;

      if (visible && !selectedEntityId) {
        RACES.forEach(race => {
          const count = Array.from(patch.entities.values())
            .filter(entity => (entity.race || 'neutral') === race).length;
          maxRows = Math.max(maxRows, Math.ceil(count / cellsPerRow));
        });
      }

      return { patch, visible, height: 40 + maxRows * (layout.cellSize + layout.cellGap) + 10 };
    });

    let currentY = 80;
    return visiblePatches.map(item => {
      const row = { ...item, y: item.visible ? currentY : -1000 };
      if (item.visible) currentY += item.height;
      return row;
    });
  }

  private renderPatchLabel(g: Selection<SVGGElement, PatchRow, null, undefined>, patch: ProcessedPatchData): void {
    if (!g.select('.patch-label').empty()) return;

    const label = g.append('g').attr('class', 'patch-label').attr('transform', 'translate(0, 20)');

    label.append('text')
      .attr('x', 10).attr('y', 0)
      .style('fill', raceColors.terran)
      .style('font-size', '14px')
      .style('font-weight', '600')
      .style('cursor', 'pointer')
      .text(patch.version)
      .on('click', () => window.open(patch.url, '_blank'));

    label.append('text')
      .attr('x', 10).attr('y', 16)
      .style('fill', '#666')
      .style('font-size', '11px')
      .text(patch.date.split('-').slice(0, 2).join('-'));
  }

  private renderEntities(
    g: Selection<SVGGElement, PatchRow, null, undefined>,
    patch: ProcessedPatchData,
    selectedEntityId: string | null,
    prevSelectedId: string | null,
    isSelecting: boolean,
    isDeselecting: boolean,
    onEntitySelect: (entityId: string | null) => void,
    setTooltip: (tooltip: TooltipState) => void,
    unitsMap: Map<string, Unit>,
    svgWidth: number
  ): void {
    const entities = this.buildEntityList(patch, selectedEntityId, svgWidth);

    const entityGroups = g.selectAll<SVGGElement, EntityItem>('.entity-cell-group')
      .data(entities, (d: EntityItem) => d.id)
      .join(
        enter => {
          const eg = enter.append('g')
            .attr('class', 'entity-cell-group')
            .attr('transform', (d: EntityItem) => `translate(${d.x}, ${d.y})`)
            .style('opacity', isDeselecting ? 0 : 1);

          eg.append('rect')
            .attr('width', layout.cellSize)
            .attr('height', layout.cellSize)
            .attr('rx', 4)
            .style('fill', 'url(#cellGradient)')
            .style('stroke', (d: EntityItem) => {
              const { status } = d.entity;
              return status ? getChangeColor(status as ChangeType) : raceColors[(d.entity.race || 'neutral') as Race];
            })
            .style('stroke-width', 2)
            .style('cursor', 'pointer');

          eg.append('image')
            .attr('width', layout.cellSize)
            .attr('height', layout.cellSize)
            .attr('href', (d: EntityItem) => `${import.meta.env.BASE_URL}assets/units/${d.entityId}.png`)
            .attr('clip-path', 'url(#roundedCorners)')
            .attr('preserveAspectRatio', 'xMidYMid slice')
            .style('pointer-events', 'none');

          return eg;
        },
        update => update,
        exit => exit.transition().duration(timing.fade).style('opacity', 0).remove()
      );

    // Event handlers
    entityGroups
      .on('click', (event, d) => {
        event.stopPropagation();
        onEntitySelect(selectedEntityId === d.entityId ? null : d.entityId);
      })
      .on('mouseenter', (event, d) => {
        if (!selectedEntityId) {
          const rect = (event.target as SVGElement).getBoundingClientRect();
          setTooltip({
            entity: {
              ...d.entity,
              name: unitsMap.get(d.entityId)?.name || d.entity.name || d.entityId,
              x: rect.left + rect.width / 2 + window.scrollX,
              y: rect.top + window.scrollY
            },
            visible: true
          });
        }
      })
      .on('mouseleave', () => setTooltip({ entity: null, visible: false }));

    // Animations
    if (isSelecting) {
      entityGroups
        .transition().duration(timing.fade)
        .style('opacity', d => d.entityId !== selectedEntityId ? 0 : 1)
        .transition().duration(timing.move).ease(easeCubicOut)
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    } else if (isDeselecting) {
      entityGroups.each(function(d) {
        const el = select(this);
        if (d.entityId === prevSelectedId) {
          el.transition().duration(timing.move).ease(easeCubicOut).attr('transform', `translate(${d.x}, ${d.y})`);
        } else {
          el.transition().delay(timing.move).duration(timing.fade).style('opacity', 1);
        }
      });
    } else {
      entityGroups.transition().duration(timing.move).ease(easeCubicOut).attr('transform', d => `translate(${d.x}, ${d.y})`);
    }
  }

  private buildEntityList(patch: ProcessedPatchData, selectedEntityId: string | null, svgWidth: number): EntityItem[] {
    const availableWidth = svgWidth - layout.patchLabelWidth;
    const raceColumnWidth = selectedEntityId ? availableWidth : Math.floor(availableWidth / RACES.length);
    const cellsPerRow = Math.floor(raceColumnWidth / (layout.cellSize + layout.cellGap));
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
      RACES.forEach((race, raceIndex) => {
        const raceEntities = Array.from(patch.entities.entries())
          .filter(([_, entity]) => (entity.race || 'neutral') === race);

        raceEntities.forEach(([entityId, entity], entityIndex) => {
          const row = Math.floor(entityIndex / cellsPerRow);
          const col = entityIndex % cellsPerRow;

          entities.push({
            id: `${entityId}-${patch.version}`,
            entityId,
            patchVersion: patch.version,
            entity,
            x: layout.patchLabelWidth + raceIndex * raceColumnWidth + col * (layout.cellSize + layout.cellGap),
            y: row * (layout.cellSize + layout.cellGap),
            visible: true
          });
        });
      });
    }

    return entities;
  }

  private renderChanges(g: Selection<SVGGElement, PatchRow, null, undefined>, patch: ProcessedPatchData, selectedEntityId: string | null): void {
    if (!selectedEntityId) {
      g.select('.changes-group').remove();
      return;
    }

    const entity = patch.entities.get(selectedEntityId);
    if (!entity || !g.select('.changes-group').empty()) return;

    const changesGroup = g.append('g')
      .attr('class', 'changes-group')
      .attr('transform', `translate(${layout.patchLabelWidth + 140}, 10)`)
      .style('opacity', 0);

    entity.changes.forEach((change: ProcessedChange, i: number) => {
      const text = changesGroup.append('text')
        .attr('x', 0).attr('y', i * 18)
        .style('fill', '#ccc')
        .style('font-size', '13px');

      text.append('tspan')
        .style('fill', getChangeColor(change.change_type as ChangeType))
        .style('font-weight', 'bold')
        .text(getChangeIndicator(change.change_type as ChangeType));

      text.append('tspan').text(change.text);
    });

    changesGroup.transition()
      .delay(timing.fade + timing.move)
      .duration(timing.fade)
      .style('opacity', 1);
  }
}
