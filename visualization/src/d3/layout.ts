/**
 * Layout Module - Pure functional calculations for visualization positioning
 *
 * This module calculates WHERE everything should be based on current state.
 * It knows nothing about animations, transitions, or previous state.
 *
 * Key principle: f(CurrentState, ScreenWidth) → TargetPositions
 *
 * The renderer handles all animation logic - layout just says "where things belong."
 */

import { ProcessedPatchData, Change, ProcessedEntity, Race, Unit } from '../types';
import type { LayoutConfig } from '../utils/uxSettings';
import { wrapText } from '../utils/textMeasurement';

// Types

/** Header layout data */
export interface HeaderLayout {
  race: Race;
  x: number;
  opacity: number;
  text: string;
}

/** Patch row layout data */
export interface PatchRowLayout {
  version: string;
  date: string;
  url: string;
  y: number;
  height: number;
  patch: ProcessedPatchData;
}

/** Entity layout data */
export interface EntityLayout {
  id: string;
  entityId: string;
  patchVersion: string;
  entity: ProcessedEntity;
  x: number;
  y: number;
}

/** Change with pre-calculated wrapped lines for rendering */
export interface WrappedChange extends Change {
  lines: string[];
}

/** Change note layout data */
export interface ChangeLayout {
  id: string;
  x: number;
  y: number;
  changes: WrappedChange[];
}

/** Entity layout in patch view (shows entity with its changes) */
export interface PatchViewEntityLayout {
  entityId: string;
  entity: ProcessedEntity;
  x: number;
  y: number;
  nameX: number;
  nameY: number;
  changes: WrappedChange[];
  changesX: number;
  changesY: number;
}

/** Complete layout result */
export interface LayoutResult {
  svgHeight: number;
  headers: HeaderLayout[];
  patchRows: PatchRowLayout[];
  entities: EntityLayout[];
  changes: ChangeLayout[];
  /** Whether we're in "focus" mode (unit selected) vs "overview" mode */
  isFocusMode: boolean;
  /** Whether we're in "patch" mode (patch selected) */
  isPatchMode: boolean;
  /** Selected patch data (for patch view) */
  selectedPatch: ProcessedPatchData | null;
  /** Entity layouts for patch view */
  patchViewEntities: PatchViewEntityLayout[];
  /** Target scroll position for focusing */
  focusTargetY: number | null;
  /** Whether this is mobile layout (labels above icons) */
  isMobile: boolean;
}

/** Input state for layout calculation */
export interface LayoutInput {
  patches: ProcessedPatchData[];
  unitsMap: Map<string, Unit>;
  selectedEntityId: string | null;
  selectedRace: Race | null;
  selectedPatchVersion: string | null;
}

/**
 * Factory function that creates a layout calculator with the given config.
 * All helpers read layout/races from closure scope - no prop drilling needed.
 */
export function createLayoutEngine(
  layout: LayoutConfig,
  races: readonly Race[]
) {
  // Helpers - read layout/races from closure

  function getColumnWidth(svgWidth: number, isFiltered: boolean): number {
    const available = svgWidth - layout.patchLabelWidth;
    return isFiltered ? available : available / races.length;
  }

  function getCellsPerRow(columnWidth: number): number {
    return Math.max(1, Math.floor((columnWidth - layout.raceColumnPadding) / (layout.cellSize + layout.cellGap)));
  }

  function getHeaderX(_svgWidth: number, columnWidth: number, columnIndex: number): number {
    const cellsPerRow = getCellsPerRow(columnWidth);
    const contentWidth = cellsPerRow * layout.cellSize + (cellsPerRow - 1) * layout.cellGap;
    return layout.patchLabelWidth + columnIndex * columnWidth + contentWidth / 2;
  }

  // Mobile layout constants (centralized here for consistency)
  const MOBILE_MARGIN = 6;        // Small edge margin on mobile
  const MOBILE_RACE_GAP = 12;     // Visible gap between race columns
  const MOBILE_LABEL_HEIGHT = 24; // Height for date+version label row
  const MOBILE_ROW_GAP = 6;       // Small gap between patch rows
  const MOBILE_CHANGE_GAP = 10;   // Gap between icon and change notes text

  // Text wrapping constants
  const TEXT_RIGHT_PADDING = 16;  // Right edge padding
  const TEXT_FONT = '13px Inter, sans-serif';  // Must match .change-note in CSS
  const INDICATOR_WIDTH = 14;     // Width of "+/- " indicator

  // Cache for wrapped changes (shared between calculatePatchRows and calculateChangesLayout)
  const wrappedChangesCache = new Map<string, WrappedChange[]>();

  /** Get X position where change note text starts */
  function getChangeTextX(isMobile: boolean): number {
    return isMobile
      ? MOBILE_MARGIN + layout.cellSize + MOBILE_CHANGE_GAP
      : layout.patchLabelWidth + layout.changeNoteOffsetX;
  }

  /** Calculate mobile grid metrics - shared by headers and entities */
  function calculateMobileGridMetrics(svgWidth: number, raceCount: number) {
    const edgeMargin = MOBILE_MARGIN;
    const totalGapWidth = (raceCount - 1) * MOBILE_RACE_GAP;
    const availableWidth = svgWidth - 2 * edgeMargin - totalGapWidth;
    const rawColumnWidth = availableWidth / raceCount;
    const cellsPerRaceRow = Math.max(1, Math.floor(rawColumnWidth / (layout.cellSize + layout.cellGap)));
    const actualRaceWidth = cellsPerRaceRow * layout.cellSize + (cellsPerRaceRow - 1) * layout.cellGap;
    const totalContentWidth = raceCount * actualRaceWidth;
    const remainingSpace = svgWidth - totalContentWidth - 2 * edgeMargin;
    const actualRaceGap = raceCount > 1 ? remainingSpace / (raceCount - 1) : 0;

    return { edgeMargin, actualRaceWidth, actualRaceGap, cellsPerRaceRow };
  }

  // Header layout

  function calculateHeaderPositions(input: LayoutInput, svgWidth: number): HeaderLayout[] {
    const isMobile = layout.patchLabelWidth === 0;
    const raceCount = races.length;

    // Determine which race header to show
    let visibleRace: Race | null = null;
    let headerText: string | null = null;

    if (input.selectedEntityId) {
      // Unit selected - show that unit's race with unit name
      const unit = input.unitsMap.get(input.selectedEntityId);
      visibleRace = unit?.race || null;
      headerText = unit?.name || null;
    } else if (input.selectedRace) {
      // Race selected - show that race
      visibleRace = input.selectedRace;
      headerText = null; // Use race name
    }

    // Calculate header X positions - must match entity positioning logic
    let headerXPositions: number[];

    if (isMobile) {
      // Mobile: use shared grid metrics
      const grid = calculateMobileGridMetrics(svgWidth, raceCount);
      headerXPositions = races.map((_, index) => {
        const raceStartX = grid.edgeMargin + index * (grid.actualRaceWidth + grid.actualRaceGap);
        return raceStartX + grid.actualRaceWidth / 2; // Center of race column
      });
    } else {
      // Desktop: use original calculation
      const availableWidth = svgWidth - layout.patchLabelWidth;
      const gridColumnWidth = availableWidth / races.length;
      headerXPositions = races.map((_, index) => getHeaderX(svgWidth, gridColumnWidth, index));
    }

    return races.map((race, index) => {
      const isVisible = visibleRace === null || race === visibleRace;

      // Grid position
      const gridX = headerXPositions[index];

      // Position: selected header goes to center of available space
      const availableWidth = svgWidth - layout.patchLabelWidth;
      const centeredX = layout.patchLabelWidth + availableWidth / 2;
      const x = (race === visibleRace) ? centeredX : gridX;

      // Text: unit name if unit selected and this is its race, otherwise race name
      const text = (headerText && race === visibleRace)
        ? headerText
        : race.charAt(0).toUpperCase() + race.slice(1);

      return {
        race,
        x,
        opacity: isVisible ? 1 : 0,
        text
      };
    });
  }

  // Patch row layout

  function calculatePatchRows(input: LayoutInput, columnWidth: number, isMobile: boolean, svgWidth: number): PatchRowLayout[] {
    const cellsPerRow = getCellsPerRow(columnWidth);

    // Clear cache at start of each layout calculation
    wrappedChangesCache.clear();

    // Filter patches to only those that are visible
    const visiblePatches = input.selectedEntityId
      ? input.patches.filter(p => p.entities.has(input.selectedEntityId!))
      : input.patches;

    let currentY = layout.gridStartY;

    return visiblePatches.map(patch => {
      let height: number;

      if (input.selectedEntityId) {
        // Focus mode: height based on change notes with text wrapping
        const entity = patch.entities.get(input.selectedEntityId);
        const rawChanges = entity?.changes || [];

        // Available width = viewport - textStart - rightPadding - indicatorWidth
        const textStartX = getChangeTextX(isMobile);
        const availableWidth = svgWidth - textStartX - TEXT_RIGHT_PADDING - INDICATOR_WIDTH;

        // Pre-calculate wrapped lines for each change
        const wrappedChanges: WrappedChange[] = rawChanges.map(change => ({
          ...change,
          lines: wrapText(change.raw_text, availableWidth, TEXT_FONT)
        }));

        // Store in cache for calculateChangesLayout
        const cacheKey = `${input.selectedEntityId}-${patch.version}`;
        wrappedChangesCache.set(cacheKey, wrappedChanges);

        // Calculate total lines across all changes
        const totalLines = wrappedChanges.reduce((sum, c) => sum + c.lines.length, 0);
        const changeNotesHeight = totalLines * layout.changeNoteLineHeight;

        height = layout.cellSize + changeNotesHeight + layout.changeNotePadding;
        if (isMobile) height += MOBILE_LABEL_HEIGHT;
      } else {
        // Overview mode: height based on entity rows
        let maxRows = 1;
        const racesToCheck = input.selectedRace ? [input.selectedRace] : races;
        racesToCheck.forEach(race => {
          const count = Array.from(patch.entities.values())
            .filter(entity => (entity.race || 'neutral') === race).length;
          maxRows = Math.max(maxRows, Math.ceil(count / cellsPerRow));
        });
        if (isMobile) {
          // Mobile: label above + icons + small gap
          height = MOBILE_LABEL_HEIGHT + maxRows * (layout.cellSize + layout.cellGap) + MOBILE_ROW_GAP;
        } else {
          // Desktop: header area + icons + footer padding
          height = layout.patchHeaderHeight + maxRows * (layout.cellSize + layout.cellGap) + layout.patchFooterPadding;
        }
      }

      const y = currentY;
      currentY += height;

      return {
        version: patch.version,
        date: patch.date,
        url: patch.url,
        y,
        height,
        patch
      };
    });
  }

  // Entity layout

  function calculateEntityPositions(
    input: LayoutInput,
    rows: PatchRowLayout[],
    columnWidth: number,
    svgWidth: number,
    isMobile: boolean
  ): EntityLayout[] {
    const entities: EntityLayout[] = [];
    const yOffset = isMobile ? MOBILE_LABEL_HEIGHT : 0;

    rows.forEach(row => {
      const patch = row.patch;

      if (input.selectedEntityId) {
        // Focus mode: only the selected entity
        const entity = patch.entities.get(input.selectedEntityId);
        if (entity) {
          // Mobile: icon at left edge; Desktop: offset from patch label
          const x = isMobile
            ? MOBILE_MARGIN
            : layout.patchLabelWidth + layout.filteredEntityOffset;
          entities.push({
            id: `${input.selectedEntityId}-${patch.version}`,
            entityId: input.selectedEntityId,
            patchVersion: patch.version,
            entity,
            x,
            y: row.y + yOffset
          });
        }
      } else {
        // Overview mode: entities in grid
        const racesToShow = input.selectedRace ? [input.selectedRace] : races;
        const raceCount = racesToShow.length;

        if (isMobile) {
          // Mobile: use shared grid metrics
          const grid = calculateMobileGridMetrics(svgWidth, raceCount);

          racesToShow.forEach((race, raceIndex) => {
            const raceEntities = Array.from(patch.entities.entries())
              .filter(([_, entity]) => (entity.race || 'neutral') === race);

            const raceStartX = grid.edgeMargin + raceIndex * (grid.actualRaceWidth + grid.actualRaceGap);

            raceEntities.forEach(([entityId, entity], entityIndex) => {
              const rowNum = Math.floor(entityIndex / grid.cellsPerRaceRow);
              const col = entityIndex % grid.cellsPerRaceRow;
              const x = raceStartX + col * (layout.cellSize + layout.cellGap);
              const y = row.y + yOffset + rowNum * (layout.cellSize + layout.cellGap);

              entities.push({
                id: `${entityId}-${patch.version}`,
                entityId,
                patchVersion: patch.version,
                entity,
                x,
                y
              });
            });
          });
        } else {
          // Desktop: divide available width into race columns
          const cellsPerRow = getCellsPerRow(columnWidth);
          const availableWidth = svgWidth - layout.patchLabelWidth;
          const raceColumnWidth = input.selectedRace
            ? availableWidth
            : availableWidth / races.length;

          racesToShow.forEach((race, raceIndex) => {
            const raceEntities = Array.from(patch.entities.entries())
              .filter(([_, entity]) => (entity.race || 'neutral') === race);

            raceEntities.forEach(([entityId, entity], entityIndex) => {
              const rowNum = Math.floor(entityIndex / cellsPerRow);
              const col = entityIndex % cellsPerRow;
              const x = layout.patchLabelWidth + raceIndex * raceColumnWidth + col * (layout.cellSize + layout.cellGap);
              const y = row.y + rowNum * (layout.cellSize + layout.cellGap);

              entities.push({
                id: `${entityId}-${patch.version}`,
                entityId,
                patchVersion: patch.version,
                entity,
                x,
                y
              });
            });
          });
        }
      }
    });

    return entities;
  }

  // Changes layout

  function calculateChangesLayout(
    rows: PatchRowLayout[],
    selectedEntityId: string,
    isMobile: boolean
  ): ChangeLayout[] {
    return rows
      .filter(row => row.patch.entities.has(selectedEntityId))
      .map(row => {
        // Retrieve pre-calculated wrapped changes from cache
        const cacheKey = `${selectedEntityId}-${row.version}`;
        const wrappedChanges = wrappedChangesCache.get(cacheKey) || [];

        const x = getChangeTextX(isMobile);
        // Mobile: slightly below icon top (icon starts at MOBILE_LABEL_HEIGHT)
        // Desktop: small offset from row
        const y = isMobile
          ? row.y + MOBILE_LABEL_HEIGHT + 10  // ~0.25em more down from icon top
          : row.y + 10;
        return {
          id: cacheKey,
          x,
          y,
          changes: wrappedChanges
        };
      });
  }

  // Patch view layout
  // Structure: mirrors the unit view but with [Icon | Name + Changes] instead of [Date | Icon | Changes]

  function calculatePatchViewEntities(
    patch: ProcessedPatchData,
    svgWidth: number,
    isMobile: boolean
  ): {
    entities: PatchViewEntityLayout[];
    totalHeight: number;
    standardEntities: EntityLayout[];
    standardChanges: ChangeLayout[];
  } {
    const entities: PatchViewEntityLayout[] = [];
    const standardEntities: EntityLayout[] = [];
    const standardChanges: ChangeLayout[] = [];

    // Match unit view's text positioning
    const textStartX = getChangeTextX(isMobile);
    const availableWidth = svgWidth - textStartX - TEXT_RIGHT_PADDING - INDICATOR_WIDTH;
    const entityGap = 8; // Smaller gap between entities (like unit view)

    let currentY = layout.gridStartY;

    // Sort entities by race for consistent ordering
    const sortedEntities = Array.from(patch.entities.entries())
      .sort((a, b) => {
        const raceOrder: Record<string, number> = { terran: 0, zerg: 1, protoss: 2, neutral: 3 };
        const raceA = a[1].race || 'neutral';
        const raceB = b[1].race || 'neutral';
        return (raceOrder[raceA] ?? 4) - (raceOrder[raceB] ?? 4);
      });

    for (const [entityId, entity] of sortedEntities) {
      // Wrap change text
      const wrappedChanges: WrappedChange[] = entity.changes.map(change => ({
        ...change,
        lines: wrapText(change.raw_text, availableWidth, TEXT_FONT)
      }));

      // Calculate total lines for height
      const totalLines = wrappedChanges.reduce((sum, c) => sum + c.lines.length, 0);
      const changesHeight = totalLines * layout.changeNoteLineHeight;

      // Row height: name + changes + padding
      // nameY=14, then changes start at ~34, then add changesHeight
      const contentHeight = 14 + layout.changeNoteLineHeight + 2 + changesHeight + layout.changeNotePadding;
      const entityHeight = Math.max(layout.cellSize + 8, contentHeight);

      // Icon position - ABSOLUTE Y for the group
      const iconX = isMobile ? MOBILE_MARGIN : layout.patchLabelWidth + layout.filteredEntityOffset;

      // ALL OTHER POSITIONS ARE RELATIVE TO THE GROUP (relative to 0, not currentY)
      // Name: at top of row, to the right of icon
      const nameX = textStartX;  // Same X as change notes
      const nameY = 14;  // RELATIVE - near top of row

      // Changes: below the name, same X position
      const changesX = textStartX;
      const changesY = nameY + layout.changeNoteLineHeight + 2;  // RELATIVE - below name with small gap

      entities.push({
        entityId,
        entity,
        x: iconX,
        y: currentY,  // ABSOLUTE - used for group translation
        nameX,        // ABSOLUTE X (doesn't change with Y)
        nameY,        // RELATIVE Y (relative to group)
        changes: wrappedChanges,
        changesX,     // ABSOLUTE X
        changesY      // RELATIVE Y (relative to group)
      });

      // ALSO create standard EntityLayout for D3 animation
      // ID format matches overview: `entityId-patchVersion`
      standardEntities.push({
        id: `${entityId}-${patch.version}`,
        entityId,
        patchVersion: patch.version,
        entity,
        x: iconX,
        y: currentY
      });

      // ALSO create standard ChangeLayout for D3 animation
      standardChanges.push({
        id: `${entityId}-${patch.version}`,
        x: changesX,
        y: currentY + changesY, // Absolute Y for changes
        changes: wrappedChanges
      });

      currentY += entityHeight + entityGap;
    }

    return { entities, totalHeight: currentY, standardEntities, standardChanges };
  }

  // Main entry point

  /**
   * Calculate complete layout for the visualization.
   * Pure function: same inputs = same outputs.
   */
  function calculateLayout(input: LayoutInput, svgWidth: number): LayoutResult {
    // Detect mobile by patchLabelWidth (0 = mobile, labels go above icons)
    const isMobile = layout.patchLabelWidth === 0;

    // Mode detection: patch view takes priority over unit view
    const isPatchMode = input.selectedPatchVersion !== null;
    const isFocusMode = !isPatchMode && input.selectedEntityId !== null;

    // Find selected patch if in patch mode
    const selectedPatch = isPatchMode
      ? input.patches.find(p => p.version === input.selectedPatchVersion) || null
      : null;

    // Handle patch view mode
    // IMPORTANT: We return entities in the STANDARD format so D3 can animate them
    // from their grid positions to their patch view positions
    if (isPatchMode && selectedPatch) {
      const { entities: patchViewEntities, totalHeight, standardEntities, standardChanges } = calculatePatchViewEntities(
        selectedPatch,
        svgWidth,
        isMobile
      );

      const svgHeight = layout.marginTop + totalHeight + layout.marginBottom;

      return {
        svgHeight,
        headers: [], // No race headers in patch view
        patchRows: [], // No patch rows - header is separate
        entities: standardEntities, // Standard entities for animation
        changes: standardChanges,   // Standard changes for animation
        isFocusMode: false,
        isPatchMode: true,
        selectedPatch,
        patchViewEntities, // Additional data for entity names
        focusTargetY: layout.gridStartY,
        isMobile
      };
    }

    // Calculate column width based on mode
    const columnWidth = getColumnWidth(svgWidth, isFocusMode || input.selectedRace !== null);

    // Calculate visible patch rows (also pre-calculates wrapped text and caches it)
    const patchRows = calculatePatchRows(input, columnWidth, isMobile, svgWidth);

    // Calculate visible entities
    const entities = calculateEntityPositions(input, patchRows, columnWidth, svgWidth, isMobile);

    // Calculate headers
    const headers = calculateHeaderPositions(input, svgWidth);

    // Calculate changes (only in focus mode)
    const changes = isFocusMode
      ? calculateChangesLayout(patchRows, input.selectedEntityId!, isMobile)
      : [];

    // Calculate total height
    const svgHeight = layout.marginTop + patchRows.reduce((sum, row) => sum + row.height, 0) + layout.marginBottom;

    // Calculate focus target for scrolling
    const focusTargetY = isFocusMode && entities.length > 0 ? entities[0].y : null;

    return {
      svgHeight,
      headers,
      patchRows,
      entities,
      changes,
      isFocusMode,
      isPatchMode: false,
      selectedPatch: null,
      patchViewEntities: [],
      focusTargetY,
      isMobile
    };
  }

  // Return only what renderer needs
  return { calculateLayout, getCellSize: () => layout.cellSize };
}
