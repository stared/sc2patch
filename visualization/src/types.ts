// Types for SC2 patch data

export interface Unit {
  id: string;
  name: string;
  race: 'terran' | 'protoss' | 'zerg';
  type: 'unit' | 'building' | 'upgrade' | 'ability' | 'mechanic';
}

export interface PatchChange {
  id: string;
  patch_version: string;
  entity_id: string;
  raw_text: string;
  change_type: 'buff' | 'nerf' | 'mixed';
}

export interface PatchMetadata {
  version: string;
  date: string;
  title: string;
  url: string;
}

export interface PatchData {
  metadata: PatchMetadata;
  changes: PatchChange[];
}

export interface ProcessedPatchData {
  version: string;
  date: string;
  url: string;
  entities: Map<string, ProcessedEntity>;
}

export interface ProcessedChange {
  text: string;
  change_type: 'buff' | 'nerf' | 'mixed';
}

export interface ProcessedEntity {
  id: string;
  name: string;
  race: string;
  type?: string;  // 'unit' | 'building' | 'upgrade' | 'ability' | 'unknown'
  changes: ProcessedChange[];
  status: 'buff' | 'nerf' | 'mixed' | null;
}

// Entity with position for tooltip display
export type EntityWithPosition = ProcessedEntity & { x: number; y: number };

export type ViewMode = 'by-patch' | 'by-unit';

// Race types
export const RACES = ['terran', 'zerg', 'protoss', 'neutral'] as const;
export type Race = typeof RACES[number];

// Component interfaces
export interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  selectedEntityId: string | null;
  onEntitySelect: (entityId: string | null) => void;
}

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