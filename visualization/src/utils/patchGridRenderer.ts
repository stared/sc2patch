import { select, type Selection } from 'd3-selection';
import { transition } from 'd3-transition';
import { easeCubicOut } from 'd3-ease';
import { ProcessedPatchData, ProcessedChange, EntityItem, PatchRow, RACES, Race, Unit, EntityWithPosition } from '../types';
import { layout, timing, raceColors, eraColors, getChangeIndicator, getChangeColor, getEraFromVersion, type ChangeType } from './uxSettings';

// Extend d3-selection to include transition
select.prototype.transition = transition;

// ============================================================================
// TYPES
// ============================================================================

type AnimationState = 'IDLE' | 'SELECTING' | 'DESELECTING';

type AnimationGroup = 'SELECTED' | 'FADE_OUT' | 'MOVE_BACK' | 'FADE_IN' | 'NORMAL';

interface EntityItemWithAnimation extends EntityItem {
  animationGroup: AnimationGroup;
  targetX?: number;
  targetY?: number;
}

type ChangeItem = {
  id: string;
  x: number;
  y: number;
  changes: ProcessedChange[];
};

interface RenderState {
  patches: ProcessedPatchData[];
  selectedEntityId: string | null;
  prevSelectedId: string | null;
  onEntitySelect: (entityId: string | null) => void;
  setTooltip: (tooltip: { entity: EntityWithPosition | null; visible: boolean }) => void;
  unitsMap: Map<string, Unit>;
  selectedRace: Race | null;
  sortOrder: 'newest' | 'oldest';
  setSortOrder?: (order: 'newest' | 'oldest') => void;
  setSelectedRace?: (race: Race | null) => void;
}

interface LayoutData {
  patchRows: PatchRow[];
  entities: EntityItemWithAnimation[];
  svgHeight: number;
}

// ============================================================================
// RENDERER CLASS
// ============================================================================

export class PatchGridRenderer {
  private svg: Selection<SVGSVGElement, unknown, null, undefined>;
  private svgWidth: number = 1400;
  private animationState: AnimationState = 'IDLE';
  private isAnimating: boolean = false;

  constructor(svgElement: SVGSVGElement) {
    this.svg = select(svgElement);
    this.initializeDefs();
  }

  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  async render(state: RenderState): Promise<void> {
    // Update SVG width (needed for header positioning)
    const svgElement = this.svg.node();
    const containerWidth = svgElement?.parentElement?.clientWidth || 1400;
    this.svgWidth = Math.min(containerWidth, 1400);

    // Always update headers immediately (they don't animate, so safe during ongoing animations)
    this.renderHeaders(state);

    // Prevent re-renders during animation
    if (this.isAnimating) {
      return Promise.resolve();
    }

    // Determine animation type
    const animType = this.determineAnimationType(state);
    this.animationState = animType;

    // Calculate layout (pure data, no DOM)
    const layoutData = this.calculateLayout(state);

    // Update SVG height
    this.svg.attr('width', this.svgWidth).attr('height', layoutData.svgHeight);

    // Sync DOM structure (immediate, no animations)
    const entities = this.syncEntities(layoutData.entities, state);
    const patches = this.syncPatches(layoutData.patchRows, state);
    const changes = this.syncChanges(layoutData.patchRows, state);

    // Apply animations
    this.isAnimating = true;
    await this.applyAnimation(animType, entities, patches, changes, state);
    this.isAnimating = false;
    this.animationState = 'IDLE';

    // For SELECTING, update DOM to show only filtered entities
    if (animType === 'SELECTING' && state.selectedEntityId) {
      const filteredLayout = this.calculateLayout(state);
      this.syncEntities(filteredLayout.entities, state);
      // D3 join will automatically remove non-selected entities
    }
  }

  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

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

  // ==========================================================================
  // DATA LAYER - Calculate positions and animation groups
  // ==========================================================================

  private determineAnimationType(state: RenderState): AnimationState {
    if (state.prevSelectedId === null && state.selectedEntityId !== null) {
      return 'SELECTING';
    } else if (state.prevSelectedId !== null && state.selectedEntityId === null) {
      return 'DESELECTING';
    }
    return 'IDLE';
  }

  private calculateLayout(state: RenderState): LayoutData {
    const patchRows = this.calculatePatchRows(state.patches, state.selectedEntityId, state.selectedRace);

    // Calculate dynamic Y positions for filtered view (used for target positions)
    // This needs to be done even during SELECTING so entities know where to animate to
    const filteredY = new Map<string, number>();
    if (state.selectedEntityId) {
      let cumulativeY = 80;
      patchRows.forEach(patchRow => {
        if (patchRow.visible) {
          const entity = patchRow.patch.entities.get(state.selectedEntityId!);
          if (entity) {
            filteredY.set(patchRow.patch.version, cumulativeY);
            const changeCount = entity.changes?.length || 0;
            const changeNotesHeight = changeCount * layout.changeNoteLineHeight;
            cumulativeY += layout.cellSize + changeNotesHeight + layout.changeNotePadding;
          }
        }
      });

      // Apply dynamic positions to patchRows so patches animate to correct targets
      patchRows.forEach(patchRow => {
        const y = filteredY.get(patchRow.patch.version);
        if (y !== undefined) {
          patchRow.y = y;
        }
      });
    }

    const entities = this.buildEntitiesList(patchRows, state, filteredY);
    const svgHeight = 80 + patchRows.reduce((sum, item) => sum + item.height, 0) + 200;

    return { patchRows, entities, svgHeight };
  }

  private calculatePatchRows(
    patches: ProcessedPatchData[],
    selectedEntityId: string | null,
    selectedRace: Race | null
  ): PatchRow[] {
    const availableWidth = this.svgWidth - layout.patchLabelWidth;
    const raceColumnWidth = (selectedEntityId || selectedRace) ? availableWidth : Math.floor(availableWidth / RACES.length);
    const cellsPerRow = Math.floor(raceColumnWidth / (layout.cellSize + layout.cellGap));

    const visiblePatches = patches.map(patch => {
      const visible = !selectedEntityId || patch.entities.has(selectedEntityId);
      let maxRows = 1;

      if (visible && !selectedEntityId) {
        const racesToCheck = selectedRace ? [selectedRace] : RACES;
        racesToCheck.forEach(race => {
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

  private buildEntitiesList(
    patchRows: PatchRow[],
    state: RenderState,
    filteredPositions: Map<string, number>
  ): EntityItemWithAnimation[] {
    const availableWidth = this.svgWidth - layout.patchLabelWidth;
    const raceColumnWidth = (state.selectedEntityId || state.selectedRace) ? availableWidth : Math.floor(availableWidth / RACES.length);
    const cellsPerRow = Math.floor(raceColumnWidth / (layout.cellSize + layout.cellGap));

    const entities: EntityItemWithAnimation[] = [];

    patchRows.filter(row => row.visible).forEach(patchRow => {
      const { patch, y: patchY } = patchRow;

      // During SELECTING, show grid even though selectedEntityId is set
      if (state.selectedEntityId && this.animationState !== 'SELECTING') {
        // Filtered view - only selected entity with dynamic positioning
        const entity = patch.entities.get(state.selectedEntityId);
        if (entity) {
          const filteredY = filteredPositions.get(patch.version) || patchY;
          entities.push({
            id: `${state.selectedEntityId}-${patch.version}`,
            entityId: state.selectedEntityId,
            patchVersion: patch.version,
            entity,
            x: layout.patchLabelWidth + 40,
            y: filteredY,
            targetX: layout.patchLabelWidth + 40,
            targetY: filteredY,
            visible: true,
            animationGroup: 'SELECTED'
          });
        }
      } else {
        // Grid view - all entities
        const racesToShow = state.selectedRace ? [state.selectedRace] : RACES;
        racesToShow.forEach((race, raceIndex) => {
          const raceEntities = Array.from(patch.entities.entries())
            .filter(([_, entity]) => (entity.race || 'neutral') === race);

          raceEntities.forEach(([entityId, entity], entityIndex) => {
            const row = Math.floor(entityIndex / cellsPerRow);
            const col = entityIndex % cellsPerRow;
            const x = layout.patchLabelWidth + raceIndex * raceColumnWidth + col * (layout.cellSize + layout.cellGap);
            const y = patchY + row * (layout.cellSize + layout.cellGap);

            // Determine animation group based on state
            let animationGroup: AnimationGroup = 'NORMAL';
            let targetX: number | undefined;
            let targetY: number | undefined;

            if (this.animationState === 'DESELECTING') {
              // Only the previously selected entity was visible during filtered view
              if (entityId === state.prevSelectedId) {
                animationGroup = 'MOVE_BACK';
              } else {
                // All other entities were hidden, so they should fade in at final position
                animationGroup = 'FADE_IN';
              }
            } else if (this.animationState === 'SELECTING' && entityId === state.selectedEntityId) {
              // Mark selected entities during selection animation
              animationGroup = 'SELECTED';
              // Set target position for animation (filtered view position with dynamic spacing)
              targetX = layout.patchLabelWidth + 40;
              targetY = filteredPositions.get(patch.version) || patchY;
            }

            entities.push({
              id: `${entityId}-${patch.version}`,
              entityId,
              patchVersion: patch.version,
              entity,
              x,
              y,
              visible: true,
              animationGroup,
              targetX,
              targetY
            });
          });
        });
      }
    });

    return entities;
  }

  // ==========================================================================
  // DOM LAYER - Structure only, no animations
  // ==========================================================================

  private syncEntities(
    entities: EntityItemWithAnimation[],
    state: RenderState
  ): Selection<SVGGElement, EntityItemWithAnimation, SVGGElement, unknown> {
    let entitiesContainer = this.svg.select<SVGGElement>('.entities-container');
    if (entitiesContainer.empty()) {
      entitiesContainer = this.svg.append('g').attr('class', 'entities-container');
    }

    const entityGroups = entitiesContainer
      .selectAll<SVGGElement, EntityItemWithAnimation>('.entity-cell-group')
      .data(entities, d => d.id)
      .join(
        enter => {
          const eg = enter.append('g')
            .attr('class', 'entity-cell-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('opacity', d => d.animationGroup === 'FADE_IN' ? 0 : 1);

          eg.append('rect')
            .attr('width', layout.cellSize)
            .attr('height', layout.cellSize)
            .attr('rx', 4)
            .style('fill', 'url(#cellGradient)')
            .style('stroke', d => {
              const { status } = d.entity;
              return status ? getChangeColor(status as ChangeType) : raceColors[(d.entity.race || 'neutral') as Race];
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
        exit => exit.remove()
      );

    // Event handlers
    entityGroups
      .on('click', (event, d) => {
        event.stopPropagation();
        state.onEntitySelect(state.selectedEntityId === d.entityId ? null : d.entityId);
      })
      .on('mouseenter', (event, d) => {
        if (!state.selectedEntityId) {
          const rect = (event.target as SVGElement).getBoundingClientRect();
          state.setTooltip({
            entity: {
              ...d.entity,
              name: state.unitsMap.get(d.entityId)?.name || d.entity.name || d.entityId,
              x: rect.left + rect.width / 2 + window.scrollX,
              y: rect.top + window.scrollY
            },
            visible: true
          });
        }
      })
      .on('mouseleave', () => state.setTooltip({ entity: null, visible: false }));

    return entityGroups;
  }

  private syncPatches(
    patchRows: PatchRow[],
    _state: RenderState
  ): Selection<SVGGElement, PatchRow, SVGGElement, unknown> {
    let patchesContainer = this.svg.select<SVGGElement>('.patches-container');
    if (patchesContainer.empty()) {
      patchesContainer = this.svg.append('g').attr('class', 'patches-container');
    }

    const patchGroups = patchesContainer
      .selectAll<SVGGElement, PatchRow>('.patch-group')
      .data(patchRows, d => d.patch.version)
      .join(
        enter => {
          const pg = enter.append('g')
            .attr('class', 'patch-group')
            .attr('transform', d => `translate(0, ${d.y})`)
            .style('opacity', d => d.visible ? 1 : 0);

          // Render patch label
          const label = pg.append('g')
            .attr('class', 'patch-label')
            .attr('transform', 'translate(0, 20)');

          label.append('text')
            .attr('x', 10).attr('y', 0)
            .style('fill', d => eraColors[getEraFromVersion(d.patch.version)])
            .style('font-size', '14px')
            .style('font-weight', '600')
            .style('cursor', 'pointer')
            .text(d => d.patch.version)
            .on('click', (_e, d) => window.open(d.patch.url, '_blank'));

          label.append('text')
            .attr('x', 10).attr('y', 16)
            .style('fill', '#666')
            .style('font-size', '11px')
            .text(d => d.patch.date.split('-').slice(0, 2).join('-'));

          return pg;
        },
        update => update,
        exit => exit.transition().duration(300).style('opacity', 0).remove()
      );

    return patchGroups;
  }

  private syncChanges(
    patchRows: PatchRow[],
    state: RenderState
  ): Selection<SVGGElement, ChangeItem, SVGGElement, unknown> {
    if (!state.selectedEntityId) {
      this.svg.select('.changes-container').remove();
      return this.svg.selectAll('.changes-group');
    }

    let changesContainer = this.svg.select<SVGGElement>('.changes-container');
    if (changesContainer.empty()) {
      changesContainer = this.svg.append('g').attr('class', 'changes-container');
    }

    const changesData: ChangeItem[] = patchRows
      .filter(row => row.visible && row.patch.entities.has(state.selectedEntityId!))
      .map(row => {
        const entity = row.patch.entities.get(state.selectedEntityId!);
        return {
          id: `${state.selectedEntityId}-${row.patch.version}`,
          x: layout.patchLabelWidth + 140,
          y: row.y + 10,
          changes: entity?.changes || []
        };
      });

    const changesGroups = changesContainer
      .selectAll<SVGGElement, ChangeItem>('.changes-group')
      .data(changesData, d => d.id)
      .join(
        enter => {
          const cg = enter.append('g')
            .attr('class', 'changes-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('opacity', 0);

          cg.each(function(d) {
            const group = select(this);
            d.changes.forEach((change: ProcessedChange, i: number) => {
              const text = group.append('text')
                .attr('x', 0).attr('y', i * 18)
                .style('fill', '#ccc')
                .style('font-size', '13px');

              text.append('tspan')
                .style('fill', getChangeColor(change.change_type as ChangeType))
                .style('font-weight', 'bold')
                .text(getChangeIndicator(change.change_type as ChangeType));

              text.append('tspan').text(change.text);
            });
          });

          return cg;
        },
        update => update,
        exit => exit.transition().duration(timing.fade).style('opacity', 0).remove()
      );

    return changesGroups;
  }

  // ==========================================================================
  // ANIMATION LAYER - Separated, clean
  // ==========================================================================

  private async applyAnimation(
    type: AnimationState,
    entities: Selection<SVGGElement, EntityItemWithAnimation, SVGGElement, unknown>,
    patches: Selection<SVGGElement, PatchRow, SVGGElement, unknown>,
    changes: Selection<SVGGElement, ChangeItem, SVGGElement, unknown>,
    _state: RenderState
  ): Promise<void> {
    switch (type) {
      case 'SELECTING':
        return this.applySelectAnimation(entities, patches, changes);
      case 'DESELECTING':
        return this.applyDeselectAnimation(entities, patches);
      case 'IDLE':
        return this.applyIdleAnimation(entities, patches);
    }
  }

  private async applySelectAnimation(
    entities: Selection<SVGGElement, EntityItemWithAnimation, SVGGElement, unknown>,
    patches: Selection<SVGGElement, PatchRow, SVGGElement, unknown>,
    changes: Selection<SVGGElement, ChangeItem, SVGGElement, unknown>
  ): Promise<void> {
    // Get selected entity ID from entities data
    const selectedEntity = entities.data().find(d => d.animationGroup === 'SELECTED');
    const selectedEntityId = selectedEntity?.entityId;

    // Phase 1 (0-600ms): Fade non-selected entities and irrelevant patch labels
    const fadePromises = Promise.all([
      entities
        .filter(d => d.animationGroup !== 'SELECTED')
        .transition('select-fade')
        .duration(timing.fade)
        .style('opacity', 0)
        .end()
        .catch(() => {}),

      // Only fade out patch labels for patches that don't contain the selected entity
      patches
        .filter(d => !selectedEntityId || !d.patch.entities.has(selectedEntityId))
        .select('.patch-label')
        .transition('select-fade-labels')
        .duration(timing.fade)
        .style('opacity', 0)
        .end()
        .catch(() => {})
    ]);

    // Phase 2 (600-1400ms): Move selected entities and patches
    await fadePromises;

    const movePromises = Promise.all([
      entities
        .filter(d => d.animationGroup === 'SELECTED')
        .transition('select-move')
        .duration(timing.move)
        .ease(easeCubicOut)
        .attr('transform', d => `translate(${d.targetX ?? d.x}, ${d.targetY ?? d.y})`)
        .end()
        .catch(() => {}),

      patches
        .filter(d => d.visible)
        .transition('select-move-patches')
        .duration(timing.move)
        .ease(easeCubicOut)
        .attr('transform', d => `translate(0, ${d.y})`)
        .end()
        .catch(() => {})
    ]);

    await movePromises;

    // Phase 3 (1400ms+): Show change notes
    await changes
      .transition('select-changes')
      .duration(timing.fade)
      .style('opacity', 1)
      .end()
      .catch(() => {});
  }

  private async applyDeselectAnimation(
    entities: Selection<SVGGElement, EntityItemWithAnimation, SVGGElement, unknown>,
    patches: Selection<SVGGElement, PatchRow, SVGGElement, unknown>
  ): Promise<void> {
    // Phase 1 (0-800ms): Move entities and patches back to grid
    const movePromises = Promise.all([
      entities
        .filter(d => d.animationGroup === 'MOVE_BACK')
        .transition('deselect-move')
        .duration(timing.move)
        .ease(easeCubicOut)
        .attr('transform', d => `translate(${d.x}, ${d.y})`)
        .end()
        .catch(() => {}),

      patches
        .data()
        .forEach(d => {
          const wasVisible = d.patch.entities.size > 0;
          const patch = patches.filter(pd => pd.patch.version === d.patch.version);

          if (wasVisible) {
            patch
              .transition('deselect-move-patches')
              .duration(timing.move)
              .ease(easeCubicOut)
              .attr('transform', `translate(0, ${d.y})`);
          } else {
            patch
              .attr('transform', `translate(0, ${d.y})`)
              .transition('deselect-fade-patches')
              .delay(timing.move)
              .duration(timing.fade)
              .style('opacity', d.visible ? 1 : 0);
          }
        })
    ]);

    await movePromises;

    // Phase 2 (800-1400ms): Fade in newly appearing entities and patch labels
    await Promise.all([
      entities
        .filter(d => d.animationGroup === 'FADE_IN')
        .transition('deselect-fade')
        .duration(timing.fade)
        .style('opacity', 1)
        .end()
        .catch(() => {}),

      patches
        .select('.patch-label')
        .transition('deselect-fade-labels')
        .duration(timing.fade)
        .style('opacity', 1)
        .end()
        .catch(() => {})
    ]);

    // Remove exiting elements
    entities.filter(d => !d.visible).remove();
  }

  private async applyIdleAnimation(
    entities: Selection<SVGGElement, EntityItemWithAnimation, SVGGElement, unknown>,
    patches: Selection<SVGGElement, PatchRow, SVGGElement, unknown>
  ): Promise<void> {
    // For IDLE state (no selection change), just set positions immediately
    entities
      .style('opacity', 1)
      .attr('transform', d => `translate(${d.x}, ${d.y})`);

    patches
      .style('opacity', d => d.visible ? 1 : 0)
      .attr('transform', d => `translate(0, ${d.y})`);

    return Promise.resolve();
  }

  // ==========================================================================
  // HEADERS
  // ==========================================================================

  private renderHeaders(state: RenderState): void {
    let headersContainer = this.svg.select<SVGGElement>('.headers-container');
    if (headersContainer.empty()) {
      headersContainer = this.svg.append('g').attr('class', 'headers-container');
    }

    const availableWidth = this.svgWidth - layout.patchLabelWidth;

    // Show only the relevant race: selected race, or race of selected entity, or all races
    const selectedUnitRace = state.selectedEntityId ? state.unitsMap.get(state.selectedEntityId)?.race as Race | undefined : undefined;
    const racesToShow = state.selectedRace
      ? [state.selectedRace]
      : selectedUnitRace
        ? [selectedUnitRace]
        : RACES;

    const raceColumnWidth = (state.selectedRace || state.selectedEntityId) ? availableWidth : Math.floor(availableWidth / RACES.length);

    // Sort control
    const sortGroup = headersContainer.selectAll<SVGGElement, SortOrder>('.sort-control').data([state.sortOrder]);
    const sortEnter = sortGroup.enter().append('g').attr('class', 'sort-control');
    const sortMerge = sortEnter.merge(sortGroup);

    type SortOrder = 'newest' | 'oldest';

    sortMerge.attr('transform', 'translate(10, 50)');

    sortEnter.append('rect').attr('class', 'sort-bg');
    sortEnter.append('text').attr('class', 'sort-text');

    sortMerge.select('.sort-bg')
      .attr('width', 90).attr('height', 24).attr('rx', 4)
      .style('fill', 'rgba(255, 255, 255, 0.03)')
      .style('stroke', '#4a9eff').style('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('click', () => {
        if (state.setSortOrder) {
          state.setSortOrder(state.sortOrder === 'newest' ? 'oldest' : 'newest');
        }
      });

    sortMerge.select('.sort-text')
      .attr('x', 45).attr('y', 16).attr('text-anchor', 'middle')
      .style('fill', '#4a9eff').style('font-size', '12px').style('font-weight', '600')
      .style('cursor', 'pointer').style('pointer-events', 'none')
      .text(state.sortOrder === 'newest' ? '↓ Newest' : '↑ Oldest');

    // Race headers
    const raceHeaders = headersContainer.selectAll<SVGGElement, Race>('.race-header')
      .data(racesToShow, d => d);

    // Detect if we're deselecting (going from 1 race to all races)
    const isDeselecting = state.prevSelectedId && !state.selectedEntityId && !state.selectedRace;

    const raceEnter = raceHeaders.enter().append('g').attr('class', 'race-header');

    // Position entering headers at their final grid location
    raceEnter.attr('transform', (race: Race) => {
      const i = RACES.indexOf(race);
      const x = layout.patchLabelWidth + i * raceColumnWidth + raceColumnWidth / 2;
      return `translate(${x}, 50)`;
    });

    raceEnter.append('rect').attr('class', 'race-bg');
    raceEnter.append('text').attr('class', 'race-text');

    // Newly appearing headers fade in at their final position (no movement)
    if (isDeselecting) {
      raceEnter.style('opacity', 0)
        .transition().duration(timing.fade)
        .style('opacity', 1);
    }

    // Update all headers (existing ones will animate position changes)
    raceHeaders
      .transition().duration(timing.move)
      .attr('transform', (race: Race) => {
        const i = RACES.indexOf(race);
        const x = (state.selectedRace || state.selectedEntityId)
          ? layout.patchLabelWidth + raceColumnWidth / 2
          : layout.patchLabelWidth + i * raceColumnWidth + raceColumnWidth / 2;
        return `translate(${x}, 50)`;
      });

    const raceMerge = raceEnter.merge(raceHeaders);

    raceMerge.select('.race-bg')
      .attr('x', -40).attr('width', 80).attr('height', 24).attr('rx', 4)
      .style('fill', (race) => {
        const isActive = state.selectedRace === race || selectedUnitRace === race;
        return isActive ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.03)';
      })
      .style('stroke', (race) => {
        const isActive = state.selectedRace === race || selectedUnitRace === race;
        return isActive ? raceColors[race] : 'rgba(255, 255, 255, 0.08)';
      })
      .style('stroke-width', 1).style('cursor', 'pointer')
      .on('click', (_event, race) => {
        if (state.setSelectedRace) {
          state.setSelectedRace(state.selectedRace === race ? null : race);
        }
      });

    raceMerge.select('.race-text')
      .attr('text-anchor', 'middle').attr('y', 16)
      .style('fill', (race) => {
        const isActive = state.selectedRace === race || selectedUnitRace === race;
        return isActive ? raceColors[race] : '#999';
      })
      .style('font-size', '12px')
      .style('font-weight', (race) => {
        const isActive = state.selectedRace === race || selectedUnitRace === race;
        return isActive ? '600' : '500';
      })
      .style('cursor', 'pointer').style('pointer-events', 'none')
      .text((race) => race.charAt(0).toUpperCase() + race.slice(1));

    raceHeaders.exit()
      .transition().duration(timing.fade).style('opacity', 0).remove();
  }
}
