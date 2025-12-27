import { PatchesDataSchema, type PatchesData, type Unit, type Patch } from '../schemas';
import { ProcessedPatchData, ProcessedEntity, ProcessedChange } from '../types';

/**
 * Load and validate all patch data from single JSON file.
 * Uses Zod for runtime validation.
 */
export async function loadPatchesData(): Promise<PatchesData> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/patches.json`);
  if (!response.ok) {
    throw new Error(`Failed to load patches.json: ${response.statusText}`);
  }

  const rawData = await response.json();

  // Validate with Zod - throws if invalid
  const data = PatchesDataSchema.parse(rawData);
  console.log(`Loaded ${data.patches.length} patches, ${data.units.length} units`);

  return data;
}

/**
 * Convert units array to Map for quick lookup.
 */
export function createUnitsMap(units: Unit[]): Map<string, Unit> {
  const unitsMap = new Map<string, Unit>();
  units.forEach(unit => {
    unitsMap.set(unit.id, unit);
  });
  return unitsMap;
}

// Calculate entity status based on changes
function calculateStatus(changes: ProcessedChange[]): 'buff' | 'nerf' | 'mixed' | null {
  const types = changes.map(c => c.change_type);

  const hasBuffs = types.some(t => t === 'buff');
  const hasNerfs = types.some(t => t === 'nerf');
  const hasMixed = types.some(t => t === 'mixed');

  if (hasMixed || (hasBuffs && hasNerfs)) {
    return 'mixed';
  } else if (hasBuffs) {
    return 'buff';
  } else if (hasNerfs) {
    return 'nerf';
  }
  return null;
}

/**
 * Process patch data for visualization.
 * Converts Patch[] to ProcessedPatchData[] format used by renderer.
 */
export function processPatches(patches: Patch[], units: Map<string, Unit>): ProcessedPatchData[] {
  return patches.map(patch => {
    const entities = new Map<string, ProcessedEntity>();

    // Process each entity's changes
    patch.entities.forEach(entityChanges => {
      const entityId = entityChanges.entity_id;
      const unit = units.get(entityId);

      // Convert to ProcessedChange format
      const changes: ProcessedChange[] = entityChanges.changes.map(c => ({
        text: c.raw_text,
        change_type: c.change_type
      }));

      const status = calculateStatus(changes);

      if (unit) {
        entities.set(entityId, {
          id: entityId,
          name: unit.name,
          race: unit.race,
          type: unit.type,
          changes: changes,
          status: status
        });
      } else {
        // Handle unknown entities (assign to neutral)
        entities.set(entityId, {
          id: entityId,
          name: entityId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          race: 'neutral',
          type: 'unknown',
          changes: changes,
          status: status
        });
      }
    });

    return {
      version: patch.version,
      date: patch.date,
      url: patch.url,
      entities: entities
    };
  });
}

// Get all unique units that have been changed across all patches
export function getChangedUnits(processedPatches: ProcessedPatchData[]): Set<string> {
  const changedUnits = new Set<string>();

  processedPatches.forEach(patch => {
    patch.entities.forEach((_, entityId) => {
      changedUnits.add(entityId);
    });
  });

  return changedUnits;
}

/**
 * Group units by race (Terran, Zerg, Protoss order).
 */
export function groupUnitsByRace(unitIds: Set<string>, unitsData: Map<string, Unit>) {
  const grouped = {
    terran: [] as string[],
    zerg: [] as string[],
    protoss: [] as string[],
    neutral: [] as string[]
  };

  unitIds.forEach(unitId => {
    const unit = unitsData.get(unitId);
    if (unit) {
      const race = unit.race as keyof typeof grouped;
      if (grouped[race]) {
        grouped[race].push(unitId);
      }
    }
  });

  // Sort units within each race alphabetically by name
  (Object.keys(grouped) as Array<keyof typeof grouped>).forEach(race => {
    grouped[race].sort((a, b) => {
      const unitA = unitsData.get(a);
      const unitB = unitsData.get(b);
      return (unitA?.name || '').localeCompare(unitB?.name || '');
    });
  });

  return grouped;
}