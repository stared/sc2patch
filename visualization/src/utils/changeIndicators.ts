import { ProcessedChange } from '../types';

export type ChangeType = ProcessedChange['change_type'];

/**
 * Get the indicator symbol for a change type
 * + for buffs, − for nerfs, ± for mixed changes
 */
export function getChangeIndicator(changeType: ChangeType): string {
  switch (changeType) {
    case 'buff':
      return '+ ';
    case 'nerf':
      return '− ';
    case 'mixed':
      return '± ';
    default:
      return '';
  }
}

/**
 * Get the color for a change type
 * Blue for buffs, red for nerfs, orange for mixed
 */
export function getChangeColor(changeType: ChangeType): string {
  switch (changeType) {
    case 'buff':
      return '#4a9eff';
    case 'nerf':
      return '#ff4444';
    case 'mixed':
      return '#ff9933';
    default:
      return '#ccc';
  }
}
