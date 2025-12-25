/**
 * Centralized UX configuration for the visualization
 * Colors, sizes, timings, and other visual constants
 */

import type { Race } from '../types';

// Race colors and order (T, Z, P - standard SC2 order)
export const raceColors: Record<Race, string> = {
  terran: '#4a9eff',
  zerg: '#A335EE',
  protoss: '#FFD700',
  neutral: '#888'
};

export const filterableRaces: Array<Exclude<Race, 'neutral'>> = ['terran', 'zerg', 'protoss'];

// Era colors and data
// Each major version is its own era
export type Era = 'wol' | 'hots' | 'lotv' | 'f2p' | 'anniversary';

export const eraColors: Record<Era, string> = {
  wol: raceColors.terran,   // Wings of Liberty = Terran blue
  hots: raceColors.zerg,    // Heart of the Swarm = Zerg purple
  lotv: raceColors.protoss, // Legacy of the Void = Protoss gold
  f2p: '#C0A000',           // Free-to-Play = darker gold
  anniversary: '#E8C500'    // 10th Anniversary = bright gold
};

export const eraOrder: Era[] = ['wol', 'hots', 'lotv', 'f2p', 'anniversary'];

export const eraData: Record<Era, {
  name: string;
  short: string;
  version: string;
  releaseDate: string;
}> = {
  wol: { name: 'Wings of Liberty', short: 'WoL', version: '1.x', releaseDate: 'Jul 2010' },
  hots: { name: 'Heart of the Swarm', short: 'HotS', version: '2.x', releaseDate: 'Mar 2013' },
  lotv: { name: 'Legacy of the Void', short: 'LotV', version: '3.x', releaseDate: 'Nov 2015' },
  f2p: { name: 'Free-to-Play', short: 'F2P', version: '4.x', releaseDate: 'Nov 2017' },
  anniversary: { name: '10th Anniversary', short: '10th', version: '5.x', releaseDate: 'Jul 2020' }
};

// Map major version to era
const versionToEra: Record<string, Era> = {
  '1': 'wol',
  '2': 'hots',
  '3': 'lotv',
  '4': 'f2p',
  '5': 'anniversary'
};

export function getEraFromVersion(version: string): Era {
  const major = version[0];
  const era = versionToEra[major];
  if (!era) {
    throw new Error(`Unknown version major: ${major} (from version: ${version})`);
  }
  return era;
}

// Change type colors, labels, and indicators
// Buff uses teal to avoid overlap with Terran blue
export const changeTypeConfig = {
  buff: {
    color: '#00D18C',  // Teal - distinct from race/expansion colors
    label: 'buffs',
    indicator: '+ '
  },
  nerf: {
    color: '#ff4444',
    label: 'nerfs',
    indicator: '− '
  },
  mixed: {
    color: '#ff9933',
    label: 'mixed',
    indicator: '± '
  }
} as const;

export type ChangeType = keyof typeof changeTypeConfig;

export const changeTypeOrder: ChangeType[] = ['buff', 'nerf', 'mixed'];

// Layout constants
export const layout = {
  cellSize: 48,
  cellGap: 6,
  patchLabelWidth: 120,
  raceColumnWidth: 250,
  // Header positioning
  headerY: 12,        // Y position of header row (sort button + race labels)
  gridStartY: 55,     // Y position where first patch row starts
  // Change notes layout (for filtered view)
  changeNoteLineHeight: 18,
  changeNotePadding: 16
} as const;

// Animation timing (milliseconds)
export const timing = {
  fade: 600,
  move: 800
} as const;

// Helper functions
export function getChangeColor(changeType: ChangeType): string {
  return changeTypeConfig[changeType].color;
}

export function getChangeIndicator(changeType: ChangeType): string {
  return changeTypeConfig[changeType].indicator;
}

export function getRaceColor(race: Race): string {
  return raceColors[race];
}
