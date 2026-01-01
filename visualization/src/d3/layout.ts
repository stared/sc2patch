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

/** Change note layout data */
export interface ChangeLayout {
  id: string;
  x: number;
  y: number;
  changes: Change[];
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
      // Mobile: same calculation as entity positions
      const tempAvailable = svgWidth - 2 * MOBILE_MARGIN - (raceCount - 1) * MOBILE_RACE_GAP;
      const tempColumnWidth = tempAvailable / raceCount;
      const cellsPerRaceRow = Math.max(1, Math.floor(tempColumnWidth / (layout.cellSize + layout.cellGap)));
      const actualRaceWidth = cellsPerRaceRow * layout.cellSize + (cellsPerRaceRow - 1) * layout.cellGap;
      const totalContentWidth = raceCount * actualRaceWidth;
      const extraSpace = svgWidth - totalContentWidth - 2 * MOBILE_MARGIN;
      const raceGap = extraSpace / (raceCount - 1);

      headerXPositions = races.map((_, index) => {
        const raceStartX = MOBILE_MARGIN + index * (actualRaceWidth + raceGap);
        return raceStartX + actualRaceWidth / 2; // Center of race column
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
  const MOBILE_LABEL_HEIGHT = 24; // Height for date+version label row on mobile
  const MOBILE_ROW_GAP = 6; // Small gap between patch rows on mobile

  function calculatePatchRows(input: LayoutInput, columnWidth: number, isMobile: boolean): PatchRowLayout[] {
    const cellsPerRow = getCellsPerRow(columnWidth);

    // Filter patches to only those that are visible
    const visiblePatches = input.selectedEntityId
      ? input.patches.filter(p => p.entities.has(input.selectedEntityId!))
      : input.patches;

    let currentY = layout.gridStartY;

    return visiblePatches.map(patch => {
      let height: number;

      if (input.selectedEntityId) {
        // Focus mode: height based on change notes
        const entity = patch.entities.get(input.selectedEntityId);
        const changeCount = entity?.changes?.length || 0;
        const changeNotesHeight = changeCount * layout.changeNoteLineHeight;
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
  const MOBILE_MARGIN = 6; // Small edge margin on mobile
  const MOBILE_RACE_GAP = 12; // Visible gap between race columns on mobile

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
          // Mobile: small edge margins, bigger gaps between races
          const edgeMargin = MOBILE_MARGIN; // Small edge margin (less than patch label margin)
          const tempAvailable = svgWidth - 2 * edgeMargin - (raceCount - 1) * MOBILE_RACE_GAP;
          const tempColumnWidth = tempAvailable / raceCount;
          const cellsPerRaceRow = Math.max(1, Math.floor(tempColumnWidth / (layout.cellSize + layout.cellGap)));

          // Actual width used by icons in each race column
          const actualRaceWidth = cellsPerRaceRow * layout.cellSize + (cellsPerRaceRow - 1) * layout.cellGap;
          // Total content width
          const totalContentWidth = raceCount * actualRaceWidth;
          // Extra space goes into race gaps (not edge margins)
          const extraSpace = svgWidth - totalContentWidth - 2 * edgeMargin;
          const raceGap = extraSpace / (raceCount - 1);

          racesToShow.forEach((race, raceIndex) => {
            const raceEntities = Array.from(patch.entities.entries())
              .filter(([_, entity]) => (entity.race || 'neutral') === race);

            // Position: edge margin + previous races + previous gaps
            const raceStartX = edgeMargin + raceIndex * (actualRaceWidth + raceGap);

            raceEntities.forEach(([entityId, entity], entityIndex) => {
              const rowNum = Math.floor(entityIndex / cellsPerRaceRow);
              const col = entityIndex % cellsPerRaceRow;
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
  const MOBILE_CHANGE_GAP = 10; // Small gap between icon and text on mobile

  function calculateChangesLayout(
    rows: PatchRowLayout[],
    selectedEntityId: string,
    isMobile: boolean
  ): ChangeLayout[] {
    return rows
      .filter(row => row.patch.entities.has(selectedEntityId))
      .map(row => {
        const entity = row.patch.entities.get(selectedEntityId)!;
        // Mobile: text starts right after icon with small gap
        // Desktop: text at fixed offset from patch label
        const x = isMobile
          ? MOBILE_MARGIN + layout.cellSize + MOBILE_CHANGE_GAP
          : layout.patchLabelWidth + layout.changeNoteOffsetX;
        // Mobile: slightly below icon top (icon starts at MOBILE_LABEL_HEIGHT)
        // Desktop: small offset from row
        const y = isMobile
          ? row.y + MOBILE_LABEL_HEIGHT + 6  // 6px down from icon top
          : row.y + 10;
        return {
          id: `${selectedEntityId}-${row.version}`,
          x,
          y,
          changes: entity.changes || []
        };
      });
  }

  // Main entry point

  /**
   * Calculate complete layout for the visualization.
   * Pure function: same inputs = same outputs.
   */
  function calculateLayout(input: LayoutInput, svgWidth: number): LayoutResult {
    // Detect mobile by patchLabelWidth (0 = mobile, labels go above icons)
    const isMobile = layout.patchLabelWidth === 0;

    // Priority: unit selection > race filter
    const isFocusMode = input.selectedEntityId !== null;

    // Calculate column width based on mode
    const columnWidth = getColumnWidth(svgWidth, isFocusMode || input.selectedRace !== null);

    // Calculate visible patch rows
    const patchRows = calculatePatchRows(input, columnWidth, isMobile);

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
      focusTargetY,
      isMobile
    };
  }

  // Return only what renderer needs
  return { calculateLayout, getCellSize: () => layout.cellSize };
}
