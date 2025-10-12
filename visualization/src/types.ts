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

export interface ProcessedEntity {
  id: string;
  name: string;
  race: string;
  type?: string;  // 'unit' | 'building' | 'upgrade' | 'ability' | 'unknown'
  changes: string[];
  status: 'buff' | 'nerf' | 'redesign' | null;
}

export type ViewMode = 'by-patch' | 'by-unit';