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
  raceColumnWidth: 250
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
