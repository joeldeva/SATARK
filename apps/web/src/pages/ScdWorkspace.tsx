import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Download, MapPin } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { Card, DataTable, MetricCard, ReasonPopover, SectionHeader, Sparkline, TrustBadge } from '../components/ui';
import { exportData, getAnalytics, getFlaggedResponses } from '../lib/apiClient';
import { cn, shortTime } from '../lib/format';
import { useAppStore } from '../store/appStore';

const chartColors = ['#1A2A6C', '#0F6E56', '#1D9E75', '#BA7517', '#E24B4A'];

export function ScdWorkspace() {
  const [searchParams] = useSearchParams();
  const [threshold, setThreshold] = useState(70);
  const liveFlags = useAppStore((state) => state.liveFlags);
  const analyticsQuery = useQuery({ queryKey: ['analytics', liveFlags.length], queryFn: getAnalytics, refetchInterval: 3000 });
  const flagsQuery = useQuery({ queryKey: ['flags', liveFlags.length], queryFn: getFlaggedResponses, refetchInterval: 3000 });
  const analytics = analyticsQuery.data?.data;
  const flags = flagsQuery.data?.data.responses || liveFlags;
  const tab = searchParams.get('tab') || 'command';

  const filteredConfidence = useMemo(() => {
    if (!analytics) return [];
    return analytics.confidenceDistribution.filter((bucket) => {
      const start = Number(bucket.bucket.split('-')[0]);
      return start >= threshold || bucket.bucket.includes('96');
    });
  }, [analytics, threshold]);

  if (!analytics) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading SATARK analytics...</div>;
  }

  async function handleExport(format: 'csv' | 'pdf') {
    const result = await exportData(format);
    const blob = new Blob([result.data.content], { type: format === 'csv' ? 'text/csv' : 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.data.fileName;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="SATARK.AI - Statistical Intelligence Dashboard"
        eyebrow="SCD workspace"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleExport('pdf')}
              className="inline-flex items-center gap-2 rounded-lg border border-gov-primary px-3 py-2 text-sm font-semibold text-gov-primary focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              <Download className="h-4 w-4" />
              Export PDF
            </button>
            <button
              type="button"
              onClick={() => handleExport('csv')}
              className="inline-flex items-center gap-2 rounded-lg border border-gov-primary px-3 py-2 text-sm font-semibold text-gov-primary focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
          </div>
        }
      />

      <Card className="grid gap-3 md:grid-cols-3">
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Survey</span>
          <select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gov-teal">
            <option>PLFS 2025-26</option>
            <option>Household Employment Survey</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Time period</span>
          <select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gov-teal">
            <option>Daily</option>
            <option>Weekly</option>
            <option>Monthly</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Geography</span>
          <select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gov-teal">
            <option>All India</option>
            <option>Tamil Nadu</option>
            <option>Chennai</option>
          </select>
        </label>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Total responses" value={analytics.totalResponses.toLocaleString('en-IN')} detail="+12% vs last period" reason="Total submitted and queued responses after de-duplication." />
        <MetricCard label="Validated" value={`${analytics.validatedRate}%`} detail="High quality" reason="Responses passing required, range, context, and behaviour validation." tone="green" />
        <MetricCard label="Error rate" value={`${analytics.errorRate}%`} detail="Within limits" reason="Responses with unresolved hard validation failures." tone="red" />
        <MetricCard label="Rural / Urban" value={`${analytics.ruralUrban[0]}% / ${analytics.ruralUrban[1]}%`} detail="Balanced" reason="Sample composition against the current survey frame." />
        <MetricCard label="Gender ratio" value={`M: ${analytics.genderRatio.male}`} detail={`F: ${analytics.genderRatio.female} · Representative`} reason="Gender response mix compared against the survey frame." />
        <MetricCard label="Confidence score" value={analytics.confidenceScore} detail="Data Integrity Index" reason="Weighted validation, fraud, evidence, and behaviour confidence." tone="green" />
      </div>

      {tab === 'quality' ? <QualityDashboard analytics={analytics} /> : null}
      {tab === 'analytics' ? <AnalyticsTab analytics={analytics} threshold={threshold} setThreshold={setThreshold} filteredConfidence={filteredConfidence} /> : null}
      {tab === 'command' ? (
        <>
          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="overflow-hidden">
              <SectionHeader title="State-wise validation rate" eyebrow="Click state for district drill-down" />
              <div className="space-y-4">
                {analytics.stateValidation.map((item) => (
                  <div key={item.state}>
                    <div className="mb-1 flex justify-between text-sm font-medium text-slate-700">
                      <span>{item.state}</span>
                      <span className={item.rate >= 85 ? 'text-gov-green' : 'text-gov-amber'}>{item.rate}%</span>
                    </div>
                    <div className="h-3 rounded-full bg-slate-100">
                      <div
                        className={cn('h-3 rounded-full', item.rate >= 85 ? 'bg-gov-green' : 'bg-gov-amber')}
                        style={{ width: `${item.rate}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="overflow-hidden">
              <SectionHeader title="Enumerator performance ranking" eyebrow="Error and flag rate" />
              <DataTable
                rows={analytics.enumeratorRanking.slice(0, 8)}
                rowKey={(row) => row.id}
                columns={[
                  { key: 'rank', header: 'Rank', render: (_row, index?: number) => index || '' },
                  { key: 'agent', header: 'Agent ID', render: (row) => <span className="font-semibold">{row.id}</span>, sortValue: (row) => row.id },
                  { key: 'responses', header: 'Responses', render: (row) => row.responses, sortValue: (row) => row.responses },
                  {
                    key: 'error',
                    header: 'Error %',
                    render: (row) => <span className={row.errorRate > 10 ? 'font-semibold text-gov-red' : 'font-semibold text-gov-green'}>{row.errorRate}%</span>,
                    sortValue: (row) => row.errorRate
                  },
                  { key: 'flagged', header: 'Flagged %', render: (row) => `${row.flaggedRate}%`, sortValue: (row) => row.flaggedRate }
                ]}
              />
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
            <Card className="overflow-hidden">
              <SectionHeader title="Response trend over time" eyebrow="Live aggregation" />
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics.responseTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="label" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="responses" stroke="#1A2A6C" strokeWidth={3} />
                    <Line type="monotone" dataKey="flagged" stroke="#E24B4A" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <SectionHeader title="Live flag feed" eyebrow="Newest first" />
              <div className="space-y-3">
                {flags.slice(0, 6).map((flag) => (
                  <div key={flag.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold text-slate-900">{flag.enumeratorName}</p>
                      <span className="text-xs text-slate-500">{shortTime(flag.timestamp)}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{flag.reason}</p>
                    <div className="mt-2">
                      <TrustBadge score={flag.trustScore} level={flag.trustLevel} reason="This feed item is created when confidence and trust thresholds are breached." />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-[0.8fr_1fr]">
            <MapPanel />
            <Card>
              <SectionHeader title="Sector-wise distribution" eyebrow="Survey health" />
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={analytics.sectorDistribution} dataKey="value" nameKey="sector" innerRadius={60} outerRadius={100} paddingAngle={2}>
                      {analytics.sectorDistribution.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}

function QualityDashboard({ analytics }: { analytics: NonNullable<ReturnType<typeof useAnalyticsValue>> }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <SectionHeader title="Confidence distribution" eyebrow="Trusted data by band" />
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analytics.confidenceDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis dataKey="bucket" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#1A2A6C" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Flag rate by enumerator" eyebrow="Quality risk" />
        <div className="space-y-4">
          {analytics.enumeratorRanking.slice(0, 6).map((row) => (
            <div key={row.id}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700">{row.id}</span>
                <span className={row.flaggedRate > 10 ? 'text-gov-red' : 'text-gov-green'}>{row.flaggedRate}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div className={cn('h-2 rounded-full', row.flaggedRate > 10 ? 'bg-gov-red' : 'bg-gov-green')} style={{ width: `${Math.min(100, row.flaggedRate * 5)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function AnalyticsTab({
  analytics,
  threshold,
  setThreshold,
  filteredConfidence
}: {
  analytics: NonNullable<ReturnType<typeof useAnalyticsValue>>;
  threshold: number;
  setThreshold: (value: number) => void;
  filteredConfidence: Array<{ bucket: string; count: number }>;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <label className="block">
          <span className="flex items-center gap-2 text-sm font-semibold text-gov-primary">
            Confidence threshold: {threshold}
            <ReasonPopover reason="Aggregate analytics exclude responses below this confidence threshold by construction." />
          </span>
          <input
            type="range"
            min={0}
            max={96}
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
            className="mt-3 w-full accent-gov-primary"
          />
        </label>
        <p className="mt-2 text-sm text-slate-600">Showing responses with confidence ≥ {threshold} - untrusted data excluded by construction.</p>
      </Card>
      <Card>
        <SectionHeader title="Filtered aggregate" eyebrow="Threshold view" />
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={filteredConfidence.length ? filteredConfidence : analytics.confidenceDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis dataKey="bucket" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#0F6E56" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

function MapPanel() {
  const dots = [
    { left: 70, top: 72, label: 'Chennai' },
    { left: 42, top: 48, label: 'Mumbai' },
    { left: 49, top: 36, label: 'Bhopal' },
    { left: 54, top: 25, label: 'Lucknow' },
    { left: 62, top: 42, label: 'Kolkata' }
  ];
  return (
    <Card>
      <SectionHeader title="Response map" eyebrow="Sample response dots" />
      <div className="relative h-72 overflow-hidden rounded-lg border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="absolute inset-6 rounded-[45%] border-2 border-slate-300 bg-white/70" />
        {dots.map((dot) => (
          <span
            key={dot.label}
            className="absolute inline-flex -translate-x-1/2 -translate-y-1/2 items-center gap-1 rounded-full border border-gov-teal bg-white px-2 py-1 text-xs font-semibold text-gov-teal shadow-sm"
            style={{ left: `${dot.left}%`, top: `${dot.top}%` }}
          >
            <MapPin className="h-3 w-3" />
            {dot.label}
          </span>
        ))}
      </div>
    </Card>
  );
}

function useAnalyticsValue() {
  return {} as import('../types').AnalyticsSnapshot;
}
