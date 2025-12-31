import {
  PatchesDataSchema,
  type PatchesData,
  type Unit,
  type Patch,
  type Change,
  type ChangeType,
  type ProcessedPatchData,
  type ProcessedEntity,
} from '../types';

/**
 * Load and validate patch data from JSON.
 */
export async function loadPatchesData(): Promise<PatchesData> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/patches.json`);
  if (!response.ok) {
    throw new Error(`Failed to load patches.json: ${response.statusText}`);
  }
  return PatchesDataSchema.parse(await response.json());
}

/**
 * Convert units array to Map for quick lookup.
 */
export function createUnitsMap(units: Unit[]): Map<string, Unit> {
  return new Map(units.map(u => [u.id, u]));
}

/**
 * Calculate overall status from changes.
 */
function calculateStatus(changes: Change[]): ChangeType | null {
  const types = new Set(changes.map(c => c.change_type));

  if (types.has('mixed') || (types.has('buff') && types.has('nerf'))) return 'mixed';
  if (types.has('buff')) return 'buff';
  if (types.has('nerf')) return 'nerf';
  return null;
}

/**
 * Process patches for visualization.
 */
export function processPatches(patches: Patch[], units: Map<string, Unit>): ProcessedPatchData[] {
  return patches.map(patch => {
    const entities = new Map<string, ProcessedEntity>();

    for (const { entity_id, changes } of patch.entities) {
      const unit = units.get(entity_id);
      if (!unit) {
        throw new Error(`Unknown entity_id "${entity_id}" in patch ${patch.version}`);
      }

      entities.set(entity_id, {
        ...unit,
        changes,
        status: calculateStatus(changes),
      });
    }

    return {
      version: patch.version,
      date: patch.date,
      url: patch.url,
      entities,
    };
  });
}
