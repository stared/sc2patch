/**
 * Zod schemas for SC2 patches data.
 * These mirror the Pydantic models in src/sc2patches/models.py
 */

import { z } from 'zod';

// Enums
export const RaceSchema = z.enum(['terran', 'protoss', 'zerg', 'neutral']);
export const ChangeTypeSchema = z.enum(['buff', 'nerf', 'mixed']);
export const UnitTypeSchema = z.enum(['unit', 'building', 'upgrade', 'ability', 'mechanic']);

// Unit schema
export const UnitSchema = z.object({
  id: z.string(),
  name: z.string(),
  race: RaceSchema,
  type: UnitTypeSchema.default('unit'),
});

// Change schema
export const ChangeSchema = z.object({
  raw_text: z.string(),
  change_type: ChangeTypeSchema,
});

// Entity changes schema
export const EntityChangesSchema = z.object({
  entity_id: z.string(),
  changes: z.array(ChangeSchema),
});

// Patch schema
export const PatchSchema = z.object({
  version: z.string(),
  date: z.string(),
  url: z.string(),
  entities: z.array(EntityChangesSchema),
});

// Root schema
export const PatchesDataSchema = z.object({
  patches: z.array(PatchSchema),
  units: z.array(UnitSchema),
  generated_at: z.string(),
});

// Inferred types
export type Race = z.infer<typeof RaceSchema>;
export type ChangeType = z.infer<typeof ChangeTypeSchema>;
export type UnitType = z.infer<typeof UnitTypeSchema>;
export type Unit = z.infer<typeof UnitSchema>;
export type Change = z.infer<typeof ChangeSchema>;
export type EntityChanges = z.infer<typeof EntityChangesSchema>;
export type Patch = z.infer<typeof PatchSchema>;
export type PatchesData = z.infer<typeof PatchesDataSchema>;
