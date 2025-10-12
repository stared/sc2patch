import { Unit, PatchData, ProcessedPatchData, ProcessedEntity } from '../types';

// Load units data
export async function loadUnits(): Promise<Map<string, Unit>> {
  const response = await fetch('/data/units.json');
  const units: Unit[] = await response.json();

  const unitsMap = new Map<string, Unit>();
  units.forEach(unit => {
    unitsMap.set(unit.id, unit);
  });

  return unitsMap;
}

// Load all patch data
export async function loadPatches(): Promise<PatchData[]> {
  // List of all patch versions from actual files
  const patchVersions = [
    '2.0.8', '2.1.9', '3.10', '3.13.0', '3.14.0', '3.4.0', '3.8.0', '4.0',
    '4.1.4', '4.10.4', '4.11.0', '4.12.0', '4.2.2', '4.2.4', '4.3.2', '4.4.0',
    '4.5.0', '4.6.1', '4.7.0', '4.7.1', '4.8.2', '4.8.4', '5.0.12', '5.0.13',
    '5.0.14', '5.0.15'
  ];

  const patches: PatchData[] = [];

  for (const version of patchVersions) {
    try {
      const response = await fetch(`/data/processed/patches/${version}.json`);
      const data = await response.json();
      patches.push(data);
    } catch (error) {
      console.error(`Failed to load patch ${version}:`, error);
    }
  }

  return patches.sort((a, b) => {
    // Sort by date
    return new Date(a.metadata.date).getTime() - new Date(b.metadata.date).getTime();
  });
}

// Process patch data for visualization
export function processPatches(patches: PatchData[], units: Map<string, Unit>): ProcessedPatchData[] {
  return patches.map(patch => {
    const entities = new Map<string, ProcessedEntity>();

    // Group changes by entity
    const changesByEntity = new Map<string, string[]>();

    patch.changes.forEach(change => {
      if (!changesByEntity.has(change.entity_id)) {
        changesByEntity.set(change.entity_id, []);
      }
      changesByEntity.get(change.entity_id)!.push(change.raw_text);
    });

    // Create processed entities
    changesByEntity.forEach((changes, entityId) => {
      const unit = units.get(entityId);

      // Only process actual units (not buildings, upgrades, etc)
      if (unit && unit.type === 'unit') {
        entities.set(entityId, {
          id: entityId,
          name: unit.name,
          race: unit.race,
          changes: changes,
          status: null  // For now, all status is null as requested
        });
      }
    });

    return {
      version: patch.metadata.version,
      date: patch.metadata.date,
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

// Group units by race
export function groupUnitsByRace(units: Set<string>, unitsData: Map<string, Unit>) {
  const grouped = {
    terran: [] as string[],
    protoss: [] as string[],
    zerg: [] as string[]
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