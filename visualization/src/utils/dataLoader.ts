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
  const patches: PatchData[] = [];

  // First, get the list of available patch files
  // We'll use a known patch to get the directory listing
  try {
    // Try to fetch patch URLs to get the list of available patches
    const urlsResponse = await fetch('/data/patch_urls.json');
    const urlsData = await urlsResponse.json();

    // Extract versions from URLs
    const versions = new Set<string>();
    Object.values(urlsData).forEach((url: any) => {
      // Extract version from URL like "5.0.12" from the URL
      const match = url.match(/(\d+\.\d+(?:\.\d+)?)/);
      if (match) {
        versions.add(match[1]);
      }
    });

    // Also try to load patches directly by checking known patterns
    const knownPatches = [
      '2.0.8', '2.1.9', '3.10', '3.13.0', '3.14.0', '3.4.0', '3.8.0', '4.0',
      '4.1.4', '4.10.4', '4.11.0', '4.12.0', '4.2.2', '4.2.4', '4.3.2', '4.4.0',
      '4.5.0', '4.6.1', '4.7.0', '4.7.1', '4.8.2', '4.8.4', '5.0.12', '5.0.13',
      '5.0.14', '5.0.15'
    ];

    // Try to load each known patch
    for (const version of knownPatches) {
      try {
        const response = await fetch(`/data/processed/patches/${version}.json`);
        if (response.ok) {
          const data = await response.json();
          patches.push(data);
        }
      } catch (error) {
        console.error(`Failed to load patch ${version}:`, error);
      }
    }
  } catch (error) {
    console.error('Failed to get patch list:', error);
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

    // Create processed entities - now including ALL types (units, buildings, upgrades, etc.)
    changesByEntity.forEach((changes, entityId) => {
      const unit = units.get(entityId);

      if (unit) {
        entities.set(entityId, {
          id: entityId,
          name: unit.name,
          race: unit.race,
          type: unit.type,  // Keep the type information
          changes: changes,
          status: null  // For now, all status is null as requested
        });
      } else {
        // Handle unknown entities (assign them to neutral)
        entities.set(entityId, {
          id: entityId,
          name: entityId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          race: 'neutral',
          type: 'unknown',
          changes: changes,
          status: null
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