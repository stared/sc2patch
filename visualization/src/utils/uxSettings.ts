/**
 * Centralized UX configuration for the visualization
 * Colors, sizes, timings, and other visual constants
 */

// Race colors
export const raceColors = {
  terran: '#4a9eff',
  zerg: '#c874e9',
  protoss: '#ffd700',
  neutral: '#888'
} as const;

export type RaceType = keyof typeof raceColors;

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

// Animation timing (all values in milliseconds)
// Base durations for consistency
const baseFade = 300;
const baseMove = 400;

export const timing = {
  // Fades
  fadeOut: baseFade * 2,           // 600ms
  fadeIn: baseFade * 2,            // 600ms

  // Movements
  move: baseMove * 2,              // 800ms

  // Complex sequences
  changesDelay: baseFade * 2 + baseMove * 2,  // 1400ms (fade + move)

  // Patch animations
  patchFade: baseFade * 2,         // 600ms
  patchMove: baseMove * 2          // 800ms
} as const;

// Helper functions
export function getChangeColor(changeType: ChangeType | string): string {
  if (changeType in changeTypeConfig) {
    return changeTypeConfig[changeType as ChangeType].color;
  }
  return '#ccc';
}

export function getChangeIndicator(changeType: ChangeType | string): string {
  if (changeType in changeTypeConfig) {
    return changeTypeConfig[changeType as ChangeType].indicator;
  }
  return '';
}

export function getRaceColor(race: string): string {
  const normalizedRace = (race || 'neutral') as RaceType;
  return raceColors[normalizedRace] || raceColors.neutral;
}
