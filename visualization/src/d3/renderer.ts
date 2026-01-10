import { select, type Selection } from 'd3-selection';
import { transition } from 'd3-transition';
import { easeCubicInOut } from 'd3-ease';
import { ProcessedPatchData, Race, Unit, EntityWithPosition } from '../types';
import { layout, timing, raceColors, eraColors, getChangeIndicator, getChangeColor, getEraFromVersion, getLayoutConfig, MOBILE_BREAKPOINT, type ChangeType, type LayoutConfig } from '../utils/uxSettings';
import {
  createLayoutEngine,
  type EntityLayout,
  type PatchRowLayout,
  type ChangeLayout,
  type WrappedChange,
  type LayoutResult,
  type LayoutInput,
  type HeaderLayout,
  type PatchViewEntityLayout
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
  selectedPatchVersion: string | null;
  onPatchSelect: (version: string | null) => void;
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
  private svgWidth: number = layout.maxWidth;
  private isFirstRender: boolean = true;
  private isImmediate: boolean = false; // Set per render() call
  private currentCellSize: number = layout.cellSize; // Track for clipPath updates

  constructor(svgElement: SVGSVGElement) {
    this.svg = select(svgElement);
    this.initializeDefs();
  }

  render(state: RenderState, options: { immediate?: boolean } = {}): void {
    // Set immediate mode: first render or explicit request
    this.isImmediate = options.immediate || this.isFirstRender;

    // Update SVG width
    const svgElement = this.svg.node();
    const containerWidth = svgElement?.parentElement?.clientWidth || layout.maxWidth;
    this.svgWidth = Math.min(containerWidth, layout.maxWidth);

    // Get mobile-aware layout config
    const isMobile = containerWidth < MOBILE_BREAKPOINT;
    const config = getLayoutConfig(isMobile);
    const engine = createLayoutEngine(config.layout, config.races);

    // Update clipPath if cellSize changed
    const cellSize = engine.getCellSize();
    if (cellSize !== this.currentCellSize) {
      this.currentCellSize = cellSize;
      this.updateClipPath(cellSize);
    }

    // Build layout input (no prev state tracking!)
    const layoutInput: LayoutInput = {
      patches: state.patches,
      unitsMap: state.unitsMap,
      selectedEntityId: state.selectedEntityId,
      selectedRace: state.selectedRace,
      selectedPatchVersion: state.selectedPatchVersion
    };

    // Calculate layout (pure function - just target positions)
    const layoutResult = engine.calculateLayout(layoutInput, this.svgWidth);

    // Update SVG dimensions
    this.svg.attr('width', this.svgWidth).attr('height', layoutResult.svgHeight);

    // Scroll to focus if needed
    if (layoutResult.focusTargetY !== null) {
      this.scrollToTargetPosition(layoutResult.focusTargetY);
    }

    // Render based on mode
    if (layoutResult.isPatchMode) {
      // Clear normal view elements
      this.svg.select('.headers-container').selectAll('*').remove();
      this.svg.select('.patches-container').selectAll('*').remove();
      this.svg.selectAll('.unit-links').remove(); // Clear unit links

      // Render simple patch header + external link
      this.renderPatchViewHeader(layoutResult);
      this.renderExternalLink(state, layoutResult);

      // Use standard entity and changes rendering for smooth animations
      this.renderEntities(layoutResult, state);
      this.renderChanges(layoutResult, true); // isPatchMode = true: sync timing with entity names

      // Render entity names (only in patch mode)
      this.renderPatchViewEntityNames(layoutResult, state);
    } else {
      // Clear patch view containers
      this.svg.selectAll('.patch-view-header').remove();
      this.svg.selectAll('.patch-entity-names').remove();

      // Render all layers with unified join pattern
      this.renderHeaders(layoutResult, state);
      this.renderPatches(layoutResult, state, config.layout);
      this.renderEntities(layoutResult, state);
      this.renderChanges(layoutResult);

      // Render external link (unit view)
      this.renderExternalLink(state, layoutResult);
    }

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
      .attr('width', this.currentCellSize)
      .attr('height', this.currentCellSize)
      .attr('rx', 4).attr('ry', 4);
  }

  private updateClipPath(cellSize: number): void {
    this.svg.select('#roundedCorners rect')
      .attr('width', cellSize)
      .attr('height', cellSize);
  }

  private scrollToTargetPosition(targetY: number): void {
    const svgElement = this.svg.node();
    if (!svgElement) return;

    const svgRect = svgElement.getBoundingClientRect();
    const pageY = svgRect.top + window.scrollY + targetY;
    const headerHeight = layout.scrollHeaderOffset;
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

    // Sort control (hide on mobile)
    this.renderSortControl(headersContainer, state, layoutResult.isMobile);

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
            .attr('height', 24).attr('rx', 4);

          g.append('text')
            .attr('class', 'race-text')
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

        // Update text and measure width
        const textEl = g.select<SVGTextElement>('.race-text')
          .text(d.text)
          .style('fill', raceColors[d.race]);

        const textWidth = textEl.node()?.getComputedTextLength() ?? 60;
        const padding = 32; // 16px each side
        const rectWidth = textWidth + padding;

        // Update rect to fit text
        g.select('.race-bg')
          .attr('width', rectWidth)
          .attr('x', -rectWidth / 2)
          .style('stroke', d.opacity > 0 ? raceColors[d.race] : 'rgba(255, 255, 255, 0.08)');
      })
      .style('--race-color', d => raceColors[d.race])
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        if (state.selectedEntityId) {
          state.onEntitySelect(null);
        } else if (state.setSelectedRace) {
          state.setSelectedRace(state.selectedRace === d.race ? null : d.race);
        }
      });

  }

  private renderSortControl(container: Selection<SVGGElement, unknown, null, undefined>, state: RenderState, isMobile: boolean): void {
    // Hide sort control on mobile
    const sortData = isMobile ? [] : [state.sortOrder];
    container.selectAll<SVGGElement, string>('.sort-control')
      .data(sortData)
      .join(
        enter => {
          const g = enter.append('g').attr('class', 'sort-control').attr('transform', 'translate(30, 0)');
          g.append('text')
            .attr('class', 'sort-text')
            .attr('x', 0).attr('y', 16);
          return g;
        },
        update => update,
        exit => exit.remove()
      )
      .select('.sort-text')
      .text(state.sortOrder === 'newest' ? '↑' : '↓')
      .on('click', (event) => {
        event.stopPropagation();
        if (state.setSortOrder) {
          state.setSortOrder(state.sortOrder === 'newest' ? 'oldest' : 'newest');
        }
      });
  }

  /**
   * Unified external link - same position for patch view (Blizzard) and unit view (Liquipedia)
   */
  private renderExternalLink(state: RenderState, layoutResult: LayoutResult): void {
    const isPatchMode = layoutResult.isPatchMode;
    const patch = layoutResult.selectedPatch;
    const hasLink = isPatchMode ? !!patch : !!state.selectedEntityId;

    const linkData = hasLink ? ['link'] : [];

    this.svg.selectAll<SVGGElement, string>('.external-link')
      .data(linkData)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('class', 'external-link wiki-link')
            .attr('transform', `translate(${this.svgWidth - 20}, 16)`)
            .style('opacity', 0)
            .style('cursor', 'pointer');

          g.append('text')
            .attr('class', 'external-link-name')
            .attr('text-anchor', 'end')
            .attr('y', 0);

          g.append('text')
            .attr('class', 'external-link-source')
            .attr('text-anchor', 'end')
            .attr('y', 14);

          g.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return g;
        },
        update => update
          .attr('transform', `translate(${this.svgWidth - 20}, 16)`)
          .style('opacity', 1),
        exit => exit.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
      )
      .on('click', (event) => {
        event.stopPropagation();
        if (isPatchMode && patch) {
          window.open(patch.url, '_blank');
        } else if (state.selectedEntityId) {
          const unit = state.unitsMap.get(state.selectedEntityId);
          if (unit) window.open(unit.liquipedia_url, '_blank');
        }
      });

    // Update text content
    const linkGroup = this.svg.select<SVGGElement>('.external-link');
    if (!linkGroup.empty()) {
      if (isPatchMode && patch) {
        linkGroup.select('.external-link-name').text(`more on Patch ${patch.version}`);
        linkGroup.select('.external-link-source').text('on Blizzard');
      } else if (state.selectedEntityId) {
        const unit = state.unitsMap.get(state.selectedEntityId);
        linkGroup.select('.external-link-name').text(unit ? `more on ${unit.name}` : '');
        linkGroup.select('.external-link-source').text('on Liquipedia');
      }
    }
  }

  private renderPatches(layoutResult: LayoutResult, state: RenderState, currentLayout: LayoutConfig): void {
    let patchesContainer = this.svg.select<SVGGElement>('.patches-container');
    if (patchesContainer.empty()) {
      patchesContainer = this.svg.append('g').attr('class', 'patches-container');
    }

    const { patchLabelTranslateX, patchLabelTranslateY, patchDateOffsetY, patchVersionOffsetX, patchVersionOffsetY } = currentLayout;

    patchesContainer
      .selectAll<SVGGElement, PatchRowLayout>('.patch-group')
      .data(layoutResult.patchRows, d => d.version)
      .join(
        enter => {
          const pg = enter.append('g')
            .attr('class', 'patch-group')
            .attr('transform', d => `translate(0, ${d.y})`)
            .style('opacity', 0);

          const label = pg.append('g')
            .attr('class', 'patch-label')
            .attr('transform', `translate(${patchLabelTranslateX}, ${patchLabelTranslateY})`)
            .style('cursor', 'pointer');

          label.append('text')
            .attr('class', 'patch-date')
            .attr('x', 0)
            .attr('y', patchDateOffsetY)
            .each(function(d) {
              select(this)
                .style('fill', eraColors[getEraFromVersion(d.version)])
                .text(d.date.split('-').slice(0, 2).join('-'));
            });

          label.append('text')
            .attr('class', 'patch-version')
            .attr('x', patchVersionOffsetX)
            .attr('y', patchVersionOffsetY)
            .text(d => d.version);

          pg.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return pg;
        },

        update => update.call(u => u.transition()
          .delay((_d, i, nodes) => {
            const wasExiting = +select(nodes[i]).style('opacity') < 0.5;
            return this.t(wasExiting ? PHASE.ENTER_DELAY : PHASE.MOVE_DELAY);
          })
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(0, ${d.y})`)
          .style('opacity', 1)
        ),

        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      );

    // Click handler
    patchesContainer
      .selectAll<SVGGElement, PatchRowLayout>('.patch-label')
      .on('click', (e, d) => {
        e.stopPropagation();
        state.onPatchSelect(d.version);
      });
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
            .attr('width', this.currentCellSize)
            .attr('height', this.currentCellSize)
            .attr('rx', 4)
            .style('fill', 'url(#cellGradient)')
            .style('stroke', d => {
              const { status } = d.entity;
              return status ? getChangeColor(status as ChangeType) : raceColors[(d.entity.race || 'neutral') as Race];
            });

          eg.append('image')
            .attr('width', this.currentCellSize)
            .attr('height', this.currentCellSize)
            .attr('href', d => `${import.meta.env.BASE_URL}assets/units/${d.entityId}.png`)
            .attr('clip-path', 'url(#roundedCorners)')
            .attr('preserveAspectRatio', 'xMidYMid slice');

          // Fade in after move phase
          // Named transition prevents UPDATE from cancelling this on React re-render
          eg.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return eg;
        },

        // UPDATE: Existing entities move to new position and update size
        // If element was mid-exit (low opacity), wait for ENTER phase instead of MOVE
        update => {
          // Update sizes immediately (for breakpoint crossing)
          update.select('rect')
            .attr('width', this.currentCellSize)
            .attr('height', this.currentCellSize);
          update.select('image')
            .attr('width', this.currentCellSize)
            .attr('height', this.currentCellSize);

          return update.call(u => u.transition()
            .delay((_d, i, nodes) => {
              const wasExiting = +select(nodes[i]).style('opacity') < 0.5;
              return this.t(wasExiting ? PHASE.ENTER_DELAY : PHASE.MOVE_DELAY);
            })
            .duration(this.t(PHASE.MOVE_DURATION))
            .ease(easeCubicInOut)
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('opacity', 1)
          );
        },

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
        state.setTooltip({ entity: null, visible: false }); // Hide tooltip instantly on click

        // Disable interactions during transition animation
        const container = document.querySelector('.patch-grid-container');
        if (container) {
          container.classList.add('transitioning');
          const totalAnimationTime = PHASE.ENTER_DELAY + PHASE.ENTER_DURATION + 50; // ~1050ms
          setTimeout(() => container.classList.remove('transitioning'), totalAnimationTime);
        }

        state.onEntitySelect(state.selectedEntityId === d.entityId ? null : d.entityId);
      })
      .on('mouseenter', (event, d) => {
        if (layoutResult.isMobile) return; // No tooltips on mobile (no hover)
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
      .on('mouseleave', (event, d) => {
        const group = event.currentTarget as SVGGElement;
        const rect = group.getBoundingClientRect();
        state.setTooltip({
          entity: {
            ...d.entity,
            name: state.unitsMap.get(d.entityId)?.name || d.entity.name || d.entityId,
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
          },
          visible: false
        });
      });
  }

  private renderChanges(layoutResult: LayoutResult, isPatchMode: boolean = false): void {
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
            let currentY = 0;
            const lineHeight = layout.changeNoteLineHeight;
            const indentX = 14; // Hanging indent for wrapped lines (matches indicator width)

            d.changes.forEach((change: WrappedChange) => {
              const textElement = group.append('text')
                .attr('class', 'change-note')
                .attr('y', currentY);

              change.lines.forEach((line, lineIndex) => {
                if (lineIndex === 0) {
                  // First line: indicator + text at x=0
                  textElement.append('tspan')
                    .attr('class', 'change-indicator')
                    .style('fill', getChangeColor(change.change_type as ChangeType))
                    .text(getChangeIndicator(change.change_type as ChangeType));

                  textElement.append('tspan')
                    .text(line);
                } else {
                  // Wrapped lines: indented, below previous
                  textElement.append('tspan')
                    .attr('x', indentX)
                    .attr('dy', lineHeight)
                    .text(line);
                }
              });

              // Move Y position for next change block
              currentY += change.lines.length * lineHeight;
            });
          });

          // Fade in: patch mode = same time as names, unit mode = after icon settles
          // Named transition prevents UPDATE from cancelling this on React re-render
          const enterDelay = isPatchMode ? PHASE.ENTER_DELAY : PHASE.ENTER_DELAY + PHASE.ENTER_DURATION;
          cg.transition('enter')
            .delay(this.t(enterDelay))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1);

          return cg;
        },

        // UPDATE: Move to new position (don't touch opacity - ENTER handles that)
        update => update.call(u => u.transition()
          .delay(this.t(PHASE.MOVE_DELAY))
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('transform', d => `translate(${d.x}, ${d.y})`)
        ),

        // EXIT: Fade out
        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      );
  }

  private renderPatchViewHeader(layoutResult: LayoutResult): void {
    if (!layoutResult.selectedPatch) return;

    let headerContainer = this.svg.select<SVGGElement>('.patch-view-header');
    if (headerContainer.empty()) {
      headerContainer = this.svg.append('g').attr('class', 'patch-view-header');
    }

    const patch = layoutResult.selectedPatch;
    const headerY = layout.headerY;
    const eraColor = eraColors[getEraFromVersion(patch.version)];

    // Title: "Patch 5.0.9" (main, bold, era-colored)
    const titleData = [patch.version];
    headerContainer
      .selectAll<SVGTextElement, string>('.patch-view-title')
      .data(titleData)
      .join(
        enter => enter.append('text')
          .attr('class', 'patch-view-title')
          .attr('x', this.svgWidth / 2)
          .attr('y', headerY + 12)
          .attr('text-anchor', 'middle')
          .style('fill', eraColor)
          .style('opacity', 0)
          .text(`Patch ${patch.version}`)
          .call(e => e.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1)
          ),
        update => update
          .attr('x', this.svgWidth / 2)
          .text(`Patch ${patch.version}`),
        exit => exit.remove()
      );

    // Date below (smaller, muted)
    const dateData = [patch.date];
    headerContainer
      .selectAll<SVGTextElement, string>('.patch-view-date')
      .data(dateData)
      .join(
        enter => enter.append('text')
          .attr('class', 'patch-view-date')
          .attr('x', this.svgWidth / 2)
          .attr('y', headerY + 28)
          .attr('text-anchor', 'middle')
          .style('fill', '#888')
          .style('font-size', '12px')
          .style('opacity', 0)
          .text(patch.date)
          .call(e => e.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1)
          ),
        update => update
          .attr('x', this.svgWidth / 2)
          .text(patch.date),
        exit => exit.remove()
      );

  }

  /**
   * Render entity names for patch view (overlaid on the standard entities)
   * These names appear next to each entity icon and link to unit view
   */
  private renderPatchViewEntityNames(layoutResult: LayoutResult, state: RenderState): void {
    let namesContainer = this.svg.select<SVGGElement>('.patch-entity-names');
    if (namesContainer.empty()) {
      namesContainer = this.svg.append('g').attr('class', 'patch-entity-names');
    }

    namesContainer
      .selectAll<SVGTextElement, PatchViewEntityLayout>('.patch-entity-name')
      .data(layoutResult.patchViewEntities, d => d.entityId)
      .join(
        enter => enter.append('text')
          .attr('class', 'patch-entity-name')
          .attr('x', d => d.nameX)
          .attr('y', d => d.y + d.nameY)  // Absolute Y = row Y + relative nameY
          .style('fill', d => raceColors[(d.entity.race || 'neutral') as Race])
          .style('cursor', 'pointer')
          .style('opacity', 0)
          .text(d => state.unitsMap.get(d.entityId)?.name || d.entity.name || d.entityId)
          .on('click', (event, d) => {
            event.stopPropagation();

            // Disable interactions during transition
            const container = document.querySelector('.patch-grid-container');
            if (container) {
              container.classList.add('transitioning');
              const totalAnimationTime = PHASE.ENTER_DELAY + PHASE.ENTER_DURATION + 50;
              setTimeout(() => container.classList.remove('transitioning'), totalAnimationTime);
            }

            state.onEntitySelect(d.entityId);
          })
          .call(e => e.transition('enter')
            .delay(this.t(PHASE.ENTER_DELAY))
            .duration(this.t(PHASE.ENTER_DURATION))
            .style('opacity', 1)
          ),

        update => update.call(u => u.transition()
          .delay(this.t(PHASE.MOVE_DELAY))
          .duration(this.t(PHASE.MOVE_DURATION))
          .ease(easeCubicInOut)
          .attr('x', d => d.nameX)
          .attr('y', d => d.y + d.nameY)
          .style('opacity', 1)
        ),

        exit => exit.call(e => e.transition()
          .duration(this.t(PHASE.EXIT_DURATION))
          .style('opacity', 0)
          .remove()
        )
      );
  }
}
