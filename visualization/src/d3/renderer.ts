import { select, type Selection } from 'd3-selection';
import { transition } from 'd3-transition';
import { easeCubicInOut } from 'd3-ease';
import { ProcessedPatchData, Change, Race, Unit, EntityWithPosition } from '../types';
import { layout, timing, raceColors, eraColors, getChangeIndicator, getChangeColor, getEraFromVersion, type ChangeType } from '../utils/uxSettings';
import {
  calculateLayout,
  type EntityLayout,
  type PatchRowLayout,
  type ChangeLayout,
  type LayoutResult,
  type LayoutInput,
  type HeaderLayout
} from './layout';

// Extend d3-selection to include transition
select.prototype.transition = transition;

// Types

interface RenderState {
  patches: ProcessedPatchData[];
  selectedEntityId: string | null;
  onEntitySelect: (entityId: string | null) => void;
  setTooltip: (tooltip: { entity: EntityWithPosition | null; visible: boolean }) => void;
  unitsMap: Map<string, Unit>;
  selectedRace: Race | null;
  sortOrder: 'newest' | 'oldest';
  setSortOrder?: (order: 'newest' | 'oldest') => void;
  setSelectedRace?: (race: Race | null) => void;
}

// Animation timing - phased: exit → move → enter
const PHASE = {
  EXIT_DURATION: timing.fade,      // 300ms - exiting elements fade out
  MOVE_DELAY: timing.fade,         // 300ms - wait for exits
  MOVE_DURATION: timing.move,      // 400ms - move to new positions
  ENTER_DELAY: timing.fade + timing.move,  // 700ms - wait for moves
  ENTER_DURATION: timing.fade      // 300ms - new elements fade in
};

export class PatchGridRenderer {
  private svg: Selection<SVGSVGElement, unknown, null, undefined>;
  private svgWidth: number = 1400;
  private isFirstRender: boolean = true;
  private isImmediate: boolean = false; // Set per render() call

  constructor(svgElement: SVGSVGElement) {
    this.svg = select(svgElement);
    this.initializeDefs();
  }

  render(state: RenderState, options: { immediate?: boolean } = {}): void {
    // Set immediate mode: first render or explicit request
    this.isImmediate = options.immediate || this.isFirstRender;

    // Update SVG width
    const svgElement = this.svg.node();
    const containerWidth = svgElement?.parentElement?.clientWidth || 1400;
    this.svgWidth = Math.min(containerWidth, 1400);

    // Build layout input (no prev state tracking!)
    const layoutInput: LayoutInput = {
      patches: state.patches,
      unitsMap: state.unitsMap,
      selectedEntityId: state.selectedEntityId,
      selectedRace: state.selectedRace
    };

    // Calculate layout (pure function - just target positions)
    const layoutResult = calculateLayout(layoutInput, this.svgWidth);

    // Update SVG dimensions
    this.svg.attr('width', this.svgWidth).attr('height', layoutResult.svgHeight);

    // Scroll to focus if needed
    if (layoutResult.focusTargetY !== null) {
      this.scrollToTargetPosition(layoutResult.focusTargetY);
    }

    // Render all layers with unified join pattern
    this.renderHeaders(layoutResult, state);
    this.renderPatches(layoutResult, state);
    this.renderEntities(layoutResult, state);
    this.renderChanges(layoutResult);

    // Clear first render flag
    this.isFirstRender = false;
  }

  // Helper: returns 0 if immediate mode, else the provided value
  private t(value: number): number {
    return this.isImmediate ? 0 : value;
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

  private scrollToTargetPosition(targetY: number): void {
    const svgElement = this.svg.node();
    if (!svgElement) return;

    const svgRect = svgElement.getBoundingClientRect();
    const pageY = svgRect.top + window.scrollY + targetY;
    const headerHeight = 200;
    const viewportHeight = window.innerHeight;
    const visibleTop = window.scrollY + headerHeight;
    const visibleBottom = window.scrollY + viewportHeight - 50;
    const isVisible = pageY > visibleTop && pageY < visibleBottom;

    if (!isVisible) {
      const targetScrollY = pageY - headerHeight - 50;
      window.scrollTo({ top: Math.max(0, targetScrollY), behavior: 'smooth' });
    }
  }

  private renderHeaders(layoutResult: LayoutResult, state: RenderState): void {
    let headersContainer = this.svg.select<SVGGElement>('.headers-container');
    if (headersContainer.empty()) {
      headersContainer = this.svg.append('g').attr('class', 'headers-container');
    }
    headersContainer.attr('transform', `translate(0, ${layout.headerY})`);

    // Sort control
    this.renderSortControl(headersContainer, state);

    // Race headers with unified join
    headersContainer
      .selectAll<SVGGElement, HeaderLayout>('.race-header')
      .data(layoutResult.headers, d => d.race)
      .join(
        // ENTER: New headers (first render)
        enter => {
          const g = enter.append('g')
            .attr('class', 'race-header')
            .attr('transform', d => `translate(${d.x}, 0)`)
            .style('opacity', d => d.opacity)
            .style('pointer-events', d => d.opacity > 0 ? 'all' : 'none');

          g.append('rect')
            .attr('class', 'race-bg')
            .attr('x', -40).attr('width', 80)
            .attr('height', 24).attr('rx', 4)
            .style('fill', 'rgba(255, 255, 255, 0.03)')
            .style('stroke', 'rgba(255, 255, 255, 0.08)')
            .style('stroke-width', 1)
            .style('cursor', 'pointer');

          g.append('text')
            .attr('class', 'race-text')
            .attr('text-anchor', 'middle')
            .attr('x', 0)
            .attr('y', 16);

          return g;
        },

        // UPDATE: Existing headers - animate to new position/opacity
        update => update.call(u => u.transition()
          .duration(this.t(PHASE.MOVE_DURATION))
          .delay(this.t(PHASE.MOVE_DELAY))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(${d.x}, 0)`)
          .style('opacity', d => d.opacity)
          .style('pointer-events', d => d.opacity > 0 ? 'all' : 'none')
        ),

        // EXIT: Headers being removed (shouldn't happen, but handle gracefully)
        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      )
      // Update content for all (enter + update)
      .each(function(d) {
        const g = select(this);
        g.select('.race-text')
          .text(d.text)
          .style('fill', raceColors[d.race]);

        g.select('.race-bg')
          .style('stroke', d.opacity > 0 ? raceColors[d.race] : 'rgba(255, 255, 255, 0.08)');
      })
      .style('--race-color', d => raceColors[d.race])
      .style('cursor', 'pointer')
      .on('click', (_event, d) => {
        if (state.selectedEntityId) {
          state.onEntitySelect(null);
        } else if (state.setSelectedRace) {
          state.setSelectedRace(state.selectedRace === d.race ? null : d.race);
        }
      });

    // Liquipedia link
    this.renderUnitLink(headersContainer, state);
  }

  private renderSortControl(container: Selection<SVGGElement, unknown, null, undefined>, state: RenderState): void {
    const sortData = [state.sortOrder];
    container.selectAll<SVGGElement, string>('.sort-control')
      .data(sortData)
      .join(
        enter => {
          const g = enter.append('g').attr('class', 'sort-control').attr('transform', 'translate(30, 0)');
          g.append('text')
            .attr('class', 'sort-text')
            .attr('x', 0).attr('y', 16).attr('text-anchor', 'middle')
            .style('fill', '#666').style('font-size', '16px').style('cursor', 'pointer');
          return g;
        },
        update => update
      )
      .select('.sort-text')
      .text(state.sortOrder === 'newest' ? '↑' : '↓')
      .on('click', () => {
        if (state.setSortOrder) {
          state.setSortOrder(state.sortOrder === 'newest' ? 'oldest' : 'newest');
        }
      });
  }

  private renderUnitLink(container: Selection<SVGGElement, unknown, null, undefined>, state: RenderState): void {
    const linksData = state.selectedEntityId ? [state.selectedEntityId] : [];
    container.selectAll<SVGTextElement, string>('.unit-links')
      .data(linksData)
      .join(
        enter => enter.append('text')
          .attr('class', 'unit-links wiki-link')
          .style('opacity', 0)
          .call(e => e.transition().delay(this.t(PHASE.ENTER_DELAY)).duration(this.t(PHASE.ENTER_DURATION)).style('opacity', 1)),
        update => update,
        exit => exit.transition().duration(this.t(PHASE.EXIT_DURATION)).style('opacity', 0).remove()
      )
      .attr('x', this.svgWidth - 20).attr('y', 16).attr('text-anchor', 'end')
      .style('fill', '#666').style('font-size', '11px').style('cursor', 'pointer')
      .text(() => {
        if (!state.selectedEntityId) return '';
        const unit = state.unitsMap.get(state.selectedEntityId);
        return unit ? `more on ${unit.name}` : '';
      })
      .on('click', () => {
        if (state.selectedEntityId) {
          const unit = state.unitsMap.get(state.selectedEntityId);
          if (unit) window.open(unit.liquipedia_url, '_blank');
        }
      });
  }

  private renderPatches(layoutResult: LayoutResult, _state: RenderState): void {
    let patchesContainer = this.svg.select<SVGGElement>('.patches-container');
    if (patchesContainer.empty()) {
      patchesContainer = this.svg.append('g').attr('class', 'patches-container');
    }

    patchesContainer
      .selectAll<SVGGElement, PatchRowLayout>('.patch-group')
      .data(layoutResult.patchRows, d => d.version)
      .join(
        // ENTER: New patches appear
        enter => {
          const pg = enter.append('g')
            .attr('class', 'patch-group')
            .attr('transform', d => `translate(0, ${d.y})`)
            .style('opacity', 0);

          const label = pg.append('g')
            .attr('class', 'patch-label')
            .attr('transform', 'translate(0, 20)');

          label.append('text')
            .attr('x', 10).attr('y', 0)
            .style('font-size', '13px')
            .style('font-weight', '600')
            .style('cursor', 'pointer')
            .each(function(d) {
              select(this)
                .style('fill', eraColors[getEraFromVersion(d.version)])
                .text(d.date.split('-').slice(0, 2).join('-'));
            })
            .on('click', (_e, d) => window.open(d.url, '_blank'));

          label.append('text')
            .attr('x', 10).attr('y', 14)
            .style('fill', '#777')
            .style('font-size', '11px')
            .style('cursor', 'pointer')
            .text(d => d.version)
            .on('click', (_e, d) => window.open(d.url, '_blank'));

          // Fade in after move phase
          pg.transition()
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return pg;
        },

        // UPDATE: Existing patches move to new position
        update => update.call(u => u.transition()
          .delay(this.t(PHASE.MOVE_DELAY))
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(0, ${d.y})`)
          .style('opacity', 1)
        ),

        // EXIT: Patches fade out
        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      );
  }

  private renderEntities(layoutResult: LayoutResult, state: RenderState): void {
    let entitiesContainer = this.svg.select<SVGGElement>('.entities-container');
    if (entitiesContainer.empty()) {
      entitiesContainer = this.svg.append('g').attr('class', 'entities-container');
    }

    entitiesContainer
      .selectAll<SVGGElement, EntityLayout>('.entity-cell-group')
      .data(layoutResult.entities, d => d.id)
      .join(
        // ENTER: New entities appear at target position, fade in
        enter => {
          const eg = enter.append('g')
            .attr('class', 'entity-cell-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('opacity', 0)
            .style('--glow-color', d => {
              const { status } = d.entity;
              return status ? getChangeColor(status as ChangeType) : raceColors[(d.entity.race || 'neutral') as Race];
            });

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

          // Fade in after move phase
          eg.transition()
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return eg;
        },

        // UPDATE: Existing entities move to new position
        update => update.call(u => u.transition()
          .delay(this.t(PHASE.MOVE_DELAY))
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`)
          .style('opacity', 1)
        ),

        // EXIT: Entities fade out in place
        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      )
      // Event handlers for all
      .on('click', (event, d) => {
        event.stopPropagation();
        state.onEntitySelect(state.selectedEntityId === d.entityId ? null : d.entityId);
      })
      .on('mouseenter', (event, d) => {
        if (state.selectedEntityId) return;
        const group = event.currentTarget as SVGGElement;
        const rect = group.getBoundingClientRect();
        state.setTooltip({
          entity: {
            ...d.entity,
            name: state.unitsMap.get(d.entityId)?.name || d.entity.name || d.entityId,
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
          },
          visible: true
        });
      })
      .on('mouseleave', () => state.setTooltip({ entity: null, visible: false }));
  }

  private renderChanges(layoutResult: LayoutResult): void {
    // Remove container if no changes
    if (layoutResult.changes.length === 0) {
      this.svg.select('.changes-container').remove();
      return;
    }

    let changesContainer = this.svg.select<SVGGElement>('.changes-container');
    if (changesContainer.empty()) {
      changesContainer = this.svg.append('g').attr('class', 'changes-container');
    }

    changesContainer
      .selectAll<SVGGElement, ChangeLayout>('.changes-group')
      .data(layoutResult.changes, d => d.id)
      .join(
        // ENTER: Change notes appear last (after everything settles)
        enter => {
          const cg = enter.append('g')
            .attr('class', 'changes-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('opacity', 0);

          cg.each(function(d) {
            const group = select(this);
            d.changes.forEach((change: Change, i: number) => {
              const text = group.append('text')
                .attr('x', 0).attr('y', i * 18)
                .style('fill', '#ccc')
                .style('font-size', '13px');

              text.append('tspan')
                .style('fill', getChangeColor(change.change_type as ChangeType))
                .style('font-weight', 'bold')
                .text(getChangeIndicator(change.change_type as ChangeType));

              text.append('tspan').text(change.raw_text);
            });
          });

          // Fade in last
          cg.transition()
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return cg;
        },

        // UPDATE: Move to new position AND ensure visible
        update => update.call(u => u.transition()
          .delay(this.t(PHASE.MOVE_DELAY))
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`)
          .style('opacity', 1)  // CRITICAL: ensure visibility after interrupted ENTER
        ),

        // EXIT: Fade out
        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      );
  }
}
