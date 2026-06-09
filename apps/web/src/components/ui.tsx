import { useMemo, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Cloud,
  CloudOff,
  Info,
  Loader2,
  ShieldCheck,
  Wifi
} from 'lucide-react';
import { syncOfflineQueue } from '../lib/apiClient';
import { cn, statusColor, trustColor } from '../lib/format';
import { useAppStore } from '../store/appStore';
import type { IntelligenceResult, StatusLevel, TrustLevel } from '../types';
import i18n, { languageLabels } from '../i18n';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={cn('min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-card', className)}>{children}</section>;
}

export function SectionHeader({
  title,
  eyebrow,
  actions
}: {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-wide text-gov-teal">{eyebrow}</p> : null}
        <h1 className="text-xl font-semibold text-gov-primary">{title}</h1>
      </div>
      {actions}
    </div>
  );
}

export function ReasonPopover({ reason, children }: { reason: string; children?: ReactNode }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-label={`Reason: ${reason}`}
        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-gov-teal"
      >
        {children || <Info className="h-3.5 w-3.5" />}
      </button>
      <span className="pointer-events-none absolute right-0 top-8 z-30 hidden w-72 rounded-lg border border-slate-200 bg-white p-3 text-left text-xs leading-relaxed text-slate-700 shadow-lg group-hover:block group-focus-within:block">
        {reason}
      </span>
    </span>
  );
}

export function TrustBadge({ score, level, reason }: { score: number; level: TrustLevel; reason: string }) {
  const colorBlind = useAppStore((state) => state.colorBlind);
  return (
    <span className={cn('inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', trustColor(level, colorBlind))}>
      <ShieldCheck className="h-3.5 w-3.5" />
      {level} {score}
      <ReasonPopover reason={reason} />
    </span>
  );
}

export function StatusChip({ status, label, reason }: { status: StatusLevel; label: string; reason: string }) {
  const colorBlind = useAppStore((state) => state.colorBlind);
  const Icon = status === 'pass' ? CheckCircle2 : status === 'warn' ? AlertTriangle : CircleAlert;
  return (
    <span className={cn('inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', statusColor(status, colorBlind))}>
      <Icon className="h-3.5 w-3.5" />
      {label}
      <ReasonPopover reason={reason} />
    </span>
  );
}

export function ConfidenceGauge({ value, reason }: { value: number; reason: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped >= 75 ? '#1D9E75' : clamped >= 55 ? '#BA7517' : '#E24B4A';
  const dash = `${clamped} ${100 - clamped}`;
  return (
    <div className="flex items-center gap-4">
      <div className="relative h-24 w-24">
        <svg viewBox="0 0 36 36" className="h-24 w-24 -rotate-90" aria-hidden="true">
          <path
            d="M18 2.1a15.9 15.9 0 1 1 0 31.8a15.9 15.9 0 1 1 0-31.8"
            fill="none"
            stroke="#E5E7EB"
            strokeWidth="3"
          />
          <path
            d="M18 2.1a15.9 15.9 0 1 1 0 31.8a15.9 15.9 0 1 1 0-31.8"
            fill="none"
            stroke={color}
            strokeDasharray={dash}
            strokeLinecap="round"
            strokeWidth="3"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <strong className="text-xl text-slate-900">{clamped}</strong>
          <span className="text-[10px] uppercase text-slate-500">score</span>
        </div>
      </div>
      <ReasonPopover reason={reason}>
        <span className="inline-flex items-center gap-1">
          <Info className="h-3.5 w-3.5" />
          why
        </span>
      </ReasonPopover>
    </div>
  );
}

export function ScoreBar({ label, value, reason }: { label: string; value: number; reason: string }) {
  const color = value >= 75 ? 'bg-gov-green' : value >= 55 ? 'bg-gov-amber' : 'bg-gov-red';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="inline-flex items-center gap-1 text-slate-500">
          {value}
          <ReasonPopover reason={reason} />
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={cn('h-2 rounded-full transition-all duration-500', color)} style={{ width: `${Math.max(4, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

interface DataColumn<T> {
  key: string;
  header: string;
  render: (row: T, index: number) => ReactNode;
  sortValue?: (row: T) => string | number;
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  onRowClick,
  empty = 'No records'
}: {
  rows: T[];
  columns: DataColumn<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  empty?: string;
}) {
  const [sortKey, setSortKey] = useState(columns[0]?.key);
  const sortedRows = useMemo(() => {
    const column = columns.find((item) => item.key === sortKey);
    if (!column?.sortValue) return rows;
    return [...rows].sort((a, b) => {
      const left = column.sortValue?.(a) ?? '';
      const right = column.sortValue?.(b) ?? '';
      return left > right ? 1 : left < right ? -1 : 0;
    });
  }, [columns, rows, sortKey]);

  if (!rows.length) {
    return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">{empty}</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-gov-primary text-left text-xs uppercase text-white">
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col" className="px-4 py-3 font-semibold">
                  <button
                    type="button"
                    onClick={() => setSortKey(column.key)}
                    className="inline-flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-white"
                  >
                    {column.header}
                    {column.sortValue ? <ChevronDown className="h-3 w-3" /> : null}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sortedRows.map((row, rowIndex) => (
              <tr
                key={rowKey(row)}
                tabIndex={onRowClick ? 0 : undefined}
                onClick={() => onRowClick?.(row)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') onRowClick?.(row);
                }}
                className={cn(onRowClick && 'cursor-pointer hover:bg-slate-50 focus:bg-slate-50 focus:outline-none')}
              >
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3 text-slate-700">
                    {column.render(row, rowIndex + 1)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Sparkline({ values, tone = 'green' }: { values: number[]; tone?: 'green' | 'red' | 'blue' }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(1, values.length - 1)) * 100;
      const y = 30 - ((value - min) / Math.max(1, max - min)) * 26;
      return `${x},${y}`;
    })
    .join(' ');
  const stroke = tone === 'red' ? '#E24B4A' : tone === 'blue' ? '#1A2A6C' : '#1D9E75';
  return (
    <svg viewBox="0 0 100 32" className="h-8 w-28" aria-label="Trust trend">
      <polyline fill="none" stroke={stroke} strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" points={points} />
    </svg>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  reason,
  tone = 'blue'
}: {
  label: string;
  value: ReactNode;
  detail: string;
  reason: string;
  tone?: 'blue' | 'green' | 'amber' | 'red';
}) {
  const textColor = {
    blue: 'text-gov-primary',
    green: 'text-gov-green',
    amber: 'text-gov-amber',
    red: 'text-gov-red'
  }[tone];
  return (
    <Card className="min-h-28">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">{label}</p>
          <p className={cn('mt-2 break-words text-2xl font-semibold leading-tight 2xl:text-3xl', textColor)}>{value}</p>
          <p className="mt-2 text-xs text-slate-500">{detail}</p>
        </div>
        <ReasonPopover reason={reason} />
      </div>
    </Card>
  );
}

export function OfflineBanner() {
  const { t } = useTranslation();
  const simulatedOffline = useAppStore((state) => state.simulatedOffline);
  const isOffline = simulatedOffline || (typeof navigator !== 'undefined' && !navigator.onLine);
  if (!isOffline) return null;
  return (
    <div className="flex items-center justify-center gap-2 bg-slate-900 px-4 py-2 text-sm font-medium text-white">
      <CloudOff className="h-4 w-4" />
      {t('offline')}
    </div>
  );
}

export function SyncIndicator() {
  const { t } = useTranslation();
  const queuedCount = useAppStore((state) => state.queuedCount);
  const simulatedOffline = useAppStore((state) => state.simulatedOffline);
  const setSimulatedOffline = useAppStore((state) => state.setSimulatedOffline);
  const [syncing, setSyncing] = useState(false);

  async function handleSync() {
    setSyncing(true);
    try {
      await syncOfflineQueue();
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => setSimulatedOffline(!simulatedOffline)}
        className={cn(
          'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-white',
          simulatedOffline ? 'border-white/40 bg-white text-gov-primary' : 'border-white/30 bg-white/10 text-white'
        )}
        aria-pressed={simulatedOffline}
      >
        {simulatedOffline ? <CloudOff className="h-3.5 w-3.5" /> : <Wifi className="h-3.5 w-3.5" />}
        Offline collection
      </button>
      <button
        type="button"
        onClick={handleSync}
        className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white"
      >
        {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cloud className="h-3.5 w-3.5" />}
        {t('queued', { count: queuedCount })}
      </button>
    </div>
  );
}

export function LanguageSwitcher() {
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);

  function changeLanguage(nextLanguage: keyof typeof languageLabels) {
    setLanguage(nextLanguage);
    void i18n.changeLanguage(nextLanguage);
  }

  return (
    <div className="inline-flex rounded-full border border-white/30 bg-white/10 p-0.5" aria-label="Language switcher">
      {(Object.keys(languageLabels) as Array<keyof typeof languageLabels>).map((item) => (
        <button
          type="button"
          key={item}
          onClick={() => changeLanguage(item)}
          className={cn(
            'rounded-full px-2.5 py-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white',
            language === item && 'bg-white text-gov-primary'
          )}
        >
          {languageLabels[item]}
        </button>
      ))}
    </div>
  );
}

export function IntelligencePanel({ result }: { result: IntelligenceResult }) {
  const steps = [
    {
      title: 'Behaviour analysis',
      content: (
        <div className="space-y-3">
          <ScoreBar label="Engagement" value={result.scores.engagement} reason="Measured from response speed and completion consistency" />
          <ScoreBar label="Fatigue" value={result.scores.fatigue} reason="Lower score means possible rushed or inattentive answering" />
          <ScoreBar label="Dropout" value={result.scores.dropout} reason="Estimated completion risk from answer pattern" />
          <ScoreBar label="Quality" value={result.scores.quality} reason="Weighted survey quality score" />
        </div>
      )
    },
    {
      title: 'Adaptive decision',
      content: (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
          <span className="font-semibold text-gov-primary">{result.decision}</span>
          <p className="mt-1 text-slate-600">{result.reason}</p>
        </div>
      )
    },
    {
      title: 'Validation',
      content: (
        <div className="flex flex-wrap gap-2">
          {result.layers.map((layer) => (
            <StatusChip key={layer.layer} status={layer.status} label={layer.layer} reason={layer.reason} />
          ))}
        </div>
      )
    },
    {
      title: 'Trust and confidence',
      content: (
        <div className="space-y-4">
          <ConfidenceGauge value={result.confidence} reason={result.reason} />
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(result.breakdown).map(([label, value]) => (
              <ScoreBar key={label} label={label} value={value} reason={`${label} contributes to the weighted confidence score`} />
            ))}
          </div>
        </div>
      )
    },
    {
      title: 'Next question',
      content: <p className="text-sm text-slate-600">{result.nextQuestionId || 'Continue the current adaptive path'} carries forward because {result.reason.toLowerCase()}.</p>
    },
    {
      title: 'Stored',
      content: <StatusChip status={result.stored ? 'pass' : 'warn'} label={result.stored ? 'Stored' : 'Pending'} reason={result.stored ? 'Response committed or queued for sync' : 'Response has not been submitted yet'} />
    }
  ];

  return (
    <Card className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-gov-teal">Shared intelligence layer</p>
        <h2 className="text-lg font-semibold text-gov-primary">Live pipeline</h2>
      </div>
      <div className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.title} className="grid grid-cols-[2rem_1fr] gap-3">
            <div className="flex flex-col items-center">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gov-primary text-xs font-semibold text-white">{index + 1}</span>
              {index < steps.length - 1 ? <span className="h-full min-h-6 w-px bg-slate-200" /> : null}
            </div>
            <div className="pb-3">
              <h3 className="text-sm font-semibold text-slate-900">{step.title}</h3>
              <div className="mt-2">{step.content}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
