/**
 * TypeScript types for SC2 patch visualization.
 *
 * Data types (Unit, Patch, etc.) are defined in schemas.ts via Zod.
 * This file contains visualization-specific types.
 */

// Re-export data types from Zod schemas
export type {
  Race,
  ChangeType,
  UnitType,
  Unit,
  Change,
  EntityChanges,
  Patch,
  PatchesData,
} from './schemas';

// Re-export race enum for iteration
export { RaceSchema } from './schemas';
export const RACES = ['terran', 'zerg', 'protoss', 'neutral'] as const;

// Visualization types (post-processing)

export interface ProcessedChange {
  text: string;
  change_type: 'buff' | 'nerf' | 'mixed';
}

export interface ProcessedEntity {
  id: string;
  name: string;
  race: string;
  type: 'unit' | 'building' | 'upgrade' | 'ability' | 'mechanic' | 'unknown';
  changes: ProcessedChange[];
  status: 'buff' | 'nerf' | 'mixed' | null;
}

export interface ProcessedPatchData {
  version: string;
  date: string;
  url: string;
  entities: Map<string, ProcessedEntity>;
}

// Entity with position for tooltip display
export type EntityWithPosition = ProcessedEntity & { x: number; y: number };

export type ViewMode = 'by-patch' | 'by-unit';

// D3 rendering interfaces
export interface EntityItem {
  id: string;
  entityId: string;
  patchVersion: string;
  entity: ProcessedEntity;
  x: number;
  y: number;
  visible: boolean;
}

export interface PatchRow {
  patch: ProcessedPatchData;
  y: number;
  visible: boolean;
  height: number;
}