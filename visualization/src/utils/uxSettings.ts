/**
 * Centralized UX configuration for the visualization
 * Colors, sizes, timings, and other visual constants
 */

import type { Race } from '../types';

// Race colors and order (T, Z, P - standard SC2 order)
export const raceColors: Record<Race, string> = {
  terran: '#4a9eff',    // Marine Blue
  zerg: '#C46CFF',      // Swarm Purple (lighter for visibility)
  protoss: '#E6B800',   // Aiur Gold (slightly darker to separate from mixed)
  neutral: '#888'
};

// Era colors and data
// Each major version is its own era
export type Era = 'wol' | 'hots' | 'lotv' | 'f2p' | 'anniversary';

export const eraColors: Record<Era, string> = {
  wol: raceColors.terran,   // Wings of Liberty = Terran blue
  hots: raceColors.zerg,    // Heart of the Swarm = Zerg purple
  lotv: raceColors.protoss, // Legacy of the Void = Protoss gold
  f2p: '#CFD8DC',           // Free-to-Play = Platinum/Silver (accessible era)
  anniversary: '#26A69A'    // 10th Anniversary = Pacific Teal (modern, distinct from silver)
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
// Palette 1: High Contrast - safest and most readable
export const changeTypeConfig = {
  buff: {
    color: '#00E676',  // Bright Green - clear positive
    label: 'buffs',
    indicator: '+ '
  },
  nerf: {
    color: '#FF1744',  // Cold Red-Pink - distinct from orange/gold
    label: 'nerfs',
    indicator: '− '
  },
  mixed: {
    color: '#ff9933',  // Original Orange - distinct from cold red nerf
    label: 'mixed',
    indicator: '± '
  }
} as const;

export type ChangeType = keyof typeof changeTypeConfig;

export const changeTypeOrder: ChangeType[] = ['buff', 'nerf', 'mixed'];

// Layout config type (widened from literal types for mobile/desktop variants)
export interface LayoutConfig {
  cellSize: number;
  cellGap: number;
  raceColumnPadding: number;
  patchLabelWidth: number;
  raceColumnWidth: number;
  maxWidth: number;
  marginTop: number;
  marginBottom: number;
  headerY: number;
  gridStartY: number;
  scrollHeaderOffset: number;
  patchHeaderHeight: number;
  patchFooterPadding: number;
  filteredEntityOffset: number;
  changeNoteLineHeight: number;
  changeNotePadding: number;
  changeNoteOffsetX: number;
}

// Layout constants
export const layout: LayoutConfig = {
  // Cell grid
  cellSize: 48,
  cellGap: 6,
  raceColumnPadding: 16,  // Visual gap between race columns (~1/3 of cellSize)
  patchLabelWidth: 90,
  raceColumnWidth: 250,
  // Canvas
  maxWidth: 1400,
  marginTop: 80,
  marginBottom: 200,
  // Header positioning
  headerY: 12,
  gridStartY: 55,
  scrollHeaderOffset: 200,
  // Patch row
  patchHeaderHeight: 40,
  patchFooterPadding: 10,
  // Filtered view
  filteredEntityOffset: 40,
  // Change notes
  changeNoteLineHeight: 18,
  changeNotePadding: 16,
  changeNoteOffsetX: 140
};

// Mobile support
export const MOBILE_BREAKPOINT = 768;

const mobileLayout: LayoutConfig = {
  ...layout,
  cellSize: 36,         // 75% of 48
  cellGap: 4,
  patchLabelWidth: 0,   // No left column - labels go above icons
};

// Races to show (mobile hides neutral to save space)
export const DESKTOP_RACES: readonly Race[] = ['terran', 'zerg', 'protoss', 'neutral'];
export const MOBILE_RACES: readonly Race[] = ['terran', 'zerg', 'protoss'];

/** Get layout config for current viewport */
export function getLayoutConfig(isMobile: boolean) {
  return {
    layout: isMobile ? mobileLayout : layout,
    races: isMobile ? MOBILE_RACES : DESKTOP_RACES,
  };
}

// Animation timing (milliseconds)
export const timing = {
  fade: 600,
  move: 800,
  textCrossFade: 200  // Race/unit text cross-fade duration
} as const;

// Helper functions
export function getChangeColor(changeType: ChangeType): string {
  return changeTypeConfig[changeType].color;
}

export function getChangeIndicator(changeType: ChangeType): string {
  return changeTypeConfig[changeType].indicator;
}
