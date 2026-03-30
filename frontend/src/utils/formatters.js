/**
 * Formatting utilities for the dashboard.
 */

export function formatBps(value) {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(2)} bps`;
}

export function formatCurrency(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatShares(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US').format(Math.round(value));
}

export function formatPercent(value) {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatScientific(value) {
  if (value === null || value === undefined) return '—';
  if (Math.abs(value) < 0.001 || Math.abs(value) > 10000) {
    return value.toExponential(2);
  }
  return value.toFixed(4);
}

export function formatLambda(value) {
  return value.toExponential(1);
}

export const STRATEGY_COLORS = {
  ac: '#C9A84C',   // gold
  ow: '#4C7AE0',   // blue
  ppo: '#4CAF8C',   // green
  twap: '#8B9CB6',  // grey
  vwap: '#8B9CB6',  // grey
};

export const STRATEGY_NAMES = {
  ac: 'Almgren-Chriss',
  ow: 'Obizhaeva-Wang',
  ppo: 'PPO Agent',
  twap: 'TWAP',
  vwap: 'VWAP',
};
