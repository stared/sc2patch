import { Unit, PatchData, ProcessedPatchData, ProcessedEntity, ProcessedChange, PatchChange } from '../types';

// Load units data
export async function loadUnits(): Promise<Map<string, Unit>> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/units.json`);
  const units: Unit[] = await response.json();

  const unitsMap = new Map<string, Unit>();
  units.forEach(unit => {
    unitsMap.set(unit.id, unit);
  });

  return unitsMap;
}

// Load all patch data
export async function loadPatches(): Promise<PatchData[]> {
  const patches: PatchData[] = [];

  try {
    // Load the patch manifest generated from processed patches
    const manifestResponse = await fetch(`${import.meta.env.BASE_URL}data/patches_manifest.json`);
    const manifest = await manifestResponse.json();

    console.log(`Loading ${manifest.total} patches from manifest`);

    // Load each patch from the manifest
    for (const patchInfo of manifest.patches) {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}data/processed/patches/${patchInfo.file}`);
        if (response.ok) {
          const data = await response.json();
          patches.push(data);
        }
      } catch (error) {
        console.error(`Failed to load patch ${patchInfo.version}:`, error);
      }
    }
  } catch (error) {
    console.error('Failed to load patch manifest:', error);
  }

  return patches.sort((a, b) => {
    // Sort by date
    return new Date(a.metadata.date).getTime() - new Date(b.metadata.date).getTime();
  });
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

// Process patch data for visualization
export function processPatches(patches: PatchData[], units: Map<string, Unit>): ProcessedPatchData[] {
  return patches.map(patch => {
    const entities = new Map<string, ProcessedEntity>();

    // Group changes by entity (now preserving change_type)
    const changesByEntity = new Map<string, ProcessedChange[]>();

    patch.changes.forEach((change: PatchChange) => {
      // HARD VALIDATION: Fail if change_type is missing
      if (!change.change_type) {
        throw new Error(
          `CRITICAL ERROR: Change missing change_type!\n` +
          `Patch: ${patch.metadata.version}\n` +
          `Entity: ${change.entity_id}\n` +
          `Text: ${change.raw_text}\n\n` +
          `ALL changes MUST have change_type (buff/nerf/mixed).\n` +
          `Run parse_with_llm_v2.py to re-parse this patch.`
        );
      }

      if (!changesByEntity.has(change.entity_id)) {
        changesByEntity.set(change.entity_id, []);
      }
      changesByEntity.get(change.entity_id)!.push({
        text: change.raw_text,
        change_type: change.change_type
      });
    });

    // Create processed entities - now including ALL types (units, buildings, upgrades, etc.)
    changesByEntity.forEach((changes, entityId) => {
      const unit = units.get(entityId);
      const status = calculateStatus(changes);

      if (unit) {
        entities.set(entityId, {
          id: entityId,
          name: unit.name,
          race: unit.race,
          type: unit.type,  // Keep the type information
          changes: changes,
          status: status
        });
      } else {
        // Handle unknown entities (assign them to neutral)
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
      version: patch.metadata.version,
      date: patch.metadata.date,
      url: patch.metadata.url,
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

// Group units by race (Terran, Zerg, Protoss order)
export function groupUnitsByRace(units: Set<string>, unitsData: Map<string, Unit>) {
  const grouped = {
    terran: [] as string[],
    zerg: [] as string[],    // Changed order: Zerg before Protoss
    protoss: [] as string[]
  };

  units.forEach(unitId => {
    const unit = unitsData.get(unitId);
    if (unit && unit.type === 'unit') {
      grouped[unit.race].push(unitId);
    }
  });

  // Sort units within each race alphabetically by name
  Object.keys(grouped).forEach(race => {
    grouped[race as keyof typeof grouped].sort((a, b) => {
      const unitA = unitsData.get(a);
      const unitB = unitsData.get(b);
      return (unitA?.name || '').localeCompare(unitB?.name || '');
    });
  });

  return grouped;
}