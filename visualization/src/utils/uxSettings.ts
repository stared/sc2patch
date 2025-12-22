/**
 * Centralized UX configuration for the visualization
 * Colors, sizes, timings, and other visual constants
 */

import type { Race } from '../types';

// Race colors
export const raceColors: Record<Race, string> = {
  terran: '#4a9eff',
  zerg: '#c874e9',
  protoss: '#ffd700',
  neutral: '#888'
};

// Expansion colors and data
export type Expansion = 'wol' | 'hots' | 'lotv';

export const expansionColors: Record<Expansion, string> = {
  wol: '#00AEEF',   // Wings of Liberty - blue
  hots: '#A000D8',  // Heart of the Swarm - purple
  lotv: '#00D18C'   // Legacy of the Void - teal
};

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

// Change type colors and indicators
export const changeTypeConfig = {
  buff: {
    color: '#4a9eff',
    indicator: '+ '
  },
  nerf: {
    color: '#ff4444',
    indicator: '− '
  },
  mixed: {
    color: '#ff9933',
    indicator: '± '
  }
} as const;

export type ChangeType = keyof typeof changeTypeConfig;

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
