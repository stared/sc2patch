/**
 * Types for SC2 patch visualization.
 * Zod schemas for runtime validation + derived TypeScript types.
 */

import { z } from 'zod';

// --- Zod Schemas (Source of Truth) ---

export const RaceSchema = z.enum(['terran', 'protoss', 'zerg', 'neutral']);
export const ChangeTypeSchema = z.enum(['buff', 'nerf', 'mixed']);
export const UnitTypeSchema = z.enum(['unit', 'building', 'upgrade', 'ability', 'mechanic']);

export const UnitSchema = z.object({
  id: z.string(),
  name: z.string(),
  race: RaceSchema,
  type: UnitTypeSchema.default('unit'),
  liquipedia_url: z.string().url(),
});

export const ChangeSchema = z.object({
  raw_text: z.string(),
  change_type: ChangeTypeSchema,
});

export const EntityChangesSchema = z.object({
  entity_id: z.string(),
  changes: z.array(ChangeSchema),
});

export const PatchSchema = z.object({
  version: z.string(),
  date: z.string(),
  url: z.string().url(),
  entities: z.array(EntityChangesSchema),
});

export const PatchesDataSchema = z.object({
  patches: z.array(PatchSchema),
  units: z.array(UnitSchema),
  generated_at: z.string(),
});

// --- Inferred Base Types ---

export type Race = z.infer<typeof RaceSchema>;
export type ChangeType = z.infer<typeof ChangeTypeSchema>;
export type UnitType = z.infer<typeof UnitTypeSchema>;
export type Unit = z.infer<typeof UnitSchema>;
export type Change = z.infer<typeof ChangeSchema>;
export type Patch = z.infer<typeof PatchSchema>;
export type PatchesData = z.infer<typeof PatchesDataSchema>;

// --- Visualization Types (derived from base) ---

// Race list derived from schema (single source of truth)
export const RACES = RaceSchema.options;

// ProcessedEntity extends Unit with visualization data
export type ProcessedEntity = Unit & {
  changes: Change[];
  status: ChangeType | null;
};

export interface ProcessedPatchData {
  version: string;
  date: string;
  url: string;
  entities: Map<string, ProcessedEntity>;
}

// Entity with screen position for tooltip
export type EntityWithPosition = ProcessedEntity & { x: number; y: number };
