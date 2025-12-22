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

// Expansion colors and data
export type Expansion = 'wol' | 'hots' | 'lotv';

export const expansionColors: Record<Expansion, string> = {
  wol: '#00AEEF',   // Wings of Liberty - cyan
  hots: '#A000D8',  // Heart of the Swarm - purple
  lotv: '#00D18C'   // Legacy of the Void - green
};

export const expansionOrder: Expansion[] = ['wol', 'hots', 'lotv'];

export const expansionData: Record<Expansion, {
  name: string;
  short: string;
  patches: number;
  percent: number;
  releaseDate: string;
}> = {
  wol: { name: 'Wings of Liberty', short: 'WoL', patches: 8, percent: 13, releaseDate: 'Jul 2010' },
  hots: { name: 'Heart of the Swarm', short: 'HotS', patches: 7, percent: 13, releaseDate: 'Mar 2013' },
  lotv: { name: 'Legacy of the Void', short: 'LotV', patches: 27, percent: 74, releaseDate: 'Nov 2015' }
};

// Change type colors, labels, and indicators
export const changeTypeConfig = {
  buff: {
    color: '#4a9eff',
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
