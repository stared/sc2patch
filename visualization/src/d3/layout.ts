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

import { ProcessedPatchData, Change, ProcessedEntity, RACES, Race, Unit } from '../types';
import { layout } from '../utils/uxSettings';

// ============================================================================
// TYPES
// ============================================================================

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
}

/** Input state for layout calculation */
export interface LayoutInput {
  patches: ProcessedPatchData[];
  unitsMap: Map<string, Unit>;
  selectedEntityId: string | null;
  selectedRace: Race | null;
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

/**
 * Calculate complete layout for the visualization.
 * Pure function: same inputs = same outputs.
 * No tracking of previous state - just calculates where things should be NOW.
 */
export function calculateLayout(input: LayoutInput, svgWidth: number): LayoutResult {
  // Priority: unit selection > race filter
  const isFocusMode = input.selectedEntityId !== null;

  // Calculate column width based on mode
  const columnWidth = getColumnWidth(svgWidth, isFocusMode || input.selectedRace !== null);

  // Calculate visible patch rows
  const patchRows = calculatePatchRows(input, columnWidth);

  // Calculate visible entities
  const entities = calculateEntityPositions(input, patchRows, columnWidth, svgWidth);

  // Calculate headers
  const headers = calculateHeaderPositions(input, svgWidth);

  // Calculate changes (only in focus mode)
  const changes = isFocusMode
    ? calculateChangesLayout(patchRows, input.selectedEntityId!)
    : [];

  // Calculate total height
  const svgHeight = 80 + patchRows.reduce((sum, row) => sum + row.height, 0) + 200;

  // Calculate focus target for scrolling
  const focusTargetY = isFocusMode && entities.length > 0 ? entities[0].y : null;

  return {
    svgHeight,
    headers,
    patchRows,
    entities,
    changes,
    isFocusMode,
    focusTargetY
  };
}

// ============================================================================
// HELPERS
// ============================================================================

function getColumnWidth(svgWidth: number, isFiltered: boolean): number {
  const available = svgWidth - layout.patchLabelWidth;
  return isFiltered ? available : available / RACES.length;
}

function getCellsPerRow(columnWidth: number): number {
  return Math.max(1, Math.floor(columnWidth / (layout.cellSize + layout.cellGap)));
}

function getHeaderX(_svgWidth: number, columnWidth: number, columnIndex: number): number {
  const cellsPerRow = getCellsPerRow(columnWidth);
  const contentWidth = cellsPerRow * layout.cellSize + (cellsPerRow - 1) * layout.cellGap;
  return layout.patchLabelWidth + columnIndex * columnWidth + contentWidth / 2;
}

// ============================================================================
// HEADER LAYOUT
// ============================================================================

function calculateHeaderPositions(input: LayoutInput, svgWidth: number): HeaderLayout[] {
  const availableWidth = svgWidth - layout.patchLabelWidth;
  const gridColumnWidth = availableWidth / RACES.length;

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

  return RACES.map((race, index) => {
    const isVisible = visibleRace === null || race === visibleRace;

    // Grid position (natural column position for 4-column layout)
    const gridX = getHeaderX(svgWidth, gridColumnWidth, index);

    // Position: selected header goes to center of available space (simple continuous function)
    // Others stay at their grid position (they fade out anyway)
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

// ============================================================================
// PATCH ROW LAYOUT
// ============================================================================

function calculatePatchRows(input: LayoutInput, columnWidth: number): PatchRowLayout[] {
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
    } else {
      // Overview mode: height based on entity rows
      let maxRows = 1;
      const racesToCheck = input.selectedRace ? [input.selectedRace] : RACES;
      racesToCheck.forEach(race => {
        const count = Array.from(patch.entities.values())
          .filter(entity => (entity.race || 'neutral') === race).length;
        maxRows = Math.max(maxRows, Math.ceil(count / cellsPerRow));
      });
      height = 40 + maxRows * (layout.cellSize + layout.cellGap) + 10;
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

// ============================================================================
// ENTITY LAYOUT
// ============================================================================

function calculateEntityPositions(
  input: LayoutInput,
  rows: PatchRowLayout[],
  columnWidth: number,
  svgWidth: number
): EntityLayout[] {
  const cellsPerRow = getCellsPerRow(columnWidth);
  const entities: EntityLayout[] = [];

  rows.forEach(row => {
    const patch = row.patch;

    if (input.selectedEntityId) {
      // Focus mode: only the selected entity
      const entity = patch.entities.get(input.selectedEntityId);
      if (entity) {
        entities.push({
          id: `${input.selectedEntityId}-${patch.version}`,
          entityId: input.selectedEntityId,
          patchVersion: patch.version,
          entity,
          x: layout.patchLabelWidth + layout.filteredEntityOffset,
          y: row.y
        });
      }
    } else {
      // Overview mode: entities in grid
      const racesToShow = input.selectedRace ? [input.selectedRace] : RACES;
      const raceColumnWidth = input.selectedRace
        ? (svgWidth - layout.patchLabelWidth)
        : (svgWidth - layout.patchLabelWidth) / RACES.length;

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
  });

  return entities;
}

// ============================================================================
// CHANGES LAYOUT
// ============================================================================

function calculateChangesLayout(
  rows: PatchRowLayout[],
  selectedEntityId: string
): ChangeLayout[] {
  return rows
    .filter(row => row.patch.entities.has(selectedEntityId))
    .map(row => {
      const entity = row.patch.entities.get(selectedEntityId)!;
      return {
        id: `${selectedEntityId}-${row.version}`,
        x: layout.patchLabelWidth + 140,
        y: row.y + 10,
        changes: entity.changes || []
      };
    });
}
