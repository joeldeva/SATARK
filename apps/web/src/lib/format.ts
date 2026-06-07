import type { TrustLevel } from '../types';

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function formatCurrency(value: number | string) {
  const numeric = typeof value === 'string' ? Number(value) : value;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(Number.isFinite(numeric) ? numeric : 0);
}

export function trustLevelForScore(score: number): TrustLevel {
  if (score >= 75) return 'Green';
  if (score >= 55) return 'Amber';
  return 'Red';
}

export function trustColor(level: TrustLevel, colorBlind = false) {
  if (colorBlind) {
    return {
      Green: 'bg-slate-100 text-slate-800 border-slate-500',
      Amber: 'bg-white text-slate-800 border-dashed border-slate-500',
      Red: 'bg-slate-900 text-white border-slate-900'
    }[level];
  }
  return {
    Green: 'bg-green-50 text-gov-green border-gov-green',
    Amber: 'bg-amber-50 text-gov-amber border-gov-amber',
    Red: 'bg-red-50 text-gov-red border-gov-red'
  }[level];
}

export function statusColor(status: 'pass' | 'warn' | 'fail', colorBlind = false) {
  if (colorBlind) {
    return {
      pass: 'bg-slate-100 text-slate-800 border-slate-500',
      warn: 'bg-white text-slate-800 border-dashed border-slate-500',
      fail: 'bg-slate-900 text-white border-slate-900'
    }[status];
  }
  return {
    pass: 'bg-green-50 text-gov-green border-gov-green',
    warn: 'bg-amber-50 text-gov-amber border-gov-amber',
    fail: 'bg-red-50 text-gov-red border-gov-red'
  }[status];
}

export function shortTime(iso: string) {
  return new Intl.DateTimeFormat('en-IN', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(iso));
}
