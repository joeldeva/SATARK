import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, Send, UserPlus } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, DataTable, SectionHeader, Sparkline, TrustBadge } from '../components/ui';
import { getEnumerators } from '../lib/apiClient';
import { useAppStore } from '../store/appStore';
import type { Enumerator } from '../types';

export function FodWorkspace() {
  const storeEnumerators = useAppStore((state) => state.enumerators);
  const liveFlags = useAppStore((state) => state.liveFlags);
  const query = useQuery({ queryKey: ['enumerators', storeEnumerators], queryFn: getEnumerators });
  const enumerators = query.data?.data.enumerators || storeEnumerators;
  const [selectedId, setSelectedId] = useState(enumerators[0]?.id || 'ENUM-A');
  const selected = enumerators.find((item) => item.id === selectedId) || enumerators[0];

  const trendData = useMemo(
    () => selected.trustTrend.map((value, index) => ({ day: `D-${selected.trustTrend.length - index - 1}`, trust: value })),
    [selected.trustTrend]
  );

  return (
    <div className="space-y-6">
      <SectionHeader title="Collection operations" eyebrow="FOD workspace" />

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.9fr]">
        <Card>
          <SectionHeader title="Enumerator roster" eyebrow="Field supervision" />
          <DataTable
            rows={enumerators}
            rowKey={(row) => row.id}
            onRowClick={(row) => setSelectedId(row.id)}
            columns={[
              {
                key: 'name',
                header: 'Name',
                render: (row) => (
                  <div>
                    <p className="font-semibold text-slate-900">{row.name}</p>
                    <p className="text-xs text-slate-500">{row.region}</p>
                  </div>
                ),
                sortValue: (row) => row.name
              },
              { key: 'assigned', header: 'Assigned', render: (row) => row.assigned, sortValue: (row) => row.assigned },
              { key: 'completed', header: 'Completed', render: (row) => row.completed, sortValue: (row) => row.completed },
              {
                key: 'trust',
                header: 'Trust',
                render: (row) => (
                  <TrustBadge score={row.trustScore} level={row.trustLevel} reason={`${row.name} trust is based on validation, fraud, evidence, and behaviour weights.`} />
                ),
                sortValue: (row) => row.trustScore
              },
              {
                key: 'trend',
                header: '7-day trust',
                render: (row) => <Sparkline values={row.trustTrend} tone={row.trustLevel === 'Red' ? 'red' : 'green'} />
              }
            ]}
          />
        </Card>

        <Card className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase text-gov-teal">Enumerator detail</p>
              <h2 className="text-lg font-semibold text-gov-primary">{selected.name}</h2>
              <p className="text-sm text-slate-500">{selected.region}</p>
            </div>
            <TrustBadge score={selected.trustScore} level={selected.trustLevel} reason="Trust changes when live validation flags are created or resolved." />
          </div>

          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="trust" stroke={selected.trustLevel === 'Red' ? '#E24B4A' : '#1D9E75'} strokeWidth={3} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-800">Recent flags</h3>
            <div className="mt-2 space-y-2">
              {liveFlags
                .filter((flag) => flag.enumeratorId === selected.id)
                .slice(0, 4)
                .map((flag) => (
                  <div key={flag.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-medium text-slate-900">{flag.survey}</p>
                    <p className="mt-1 text-xs text-slate-600">{flag.reason}</p>
                  </div>
                ))}
              {!liveFlags.some((flag) => flag.enumeratorId === selected.id) ? (
                <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-500">No recent flags for this enumerator.</p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-gov-teal" type="button">
              <UserPlus className="h-4 w-4" />
              Assign survey
            </button>
            <button className="inline-flex items-center justify-center gap-2 rounded-lg border border-gov-primary px-3 py-2 text-sm font-semibold text-gov-primary focus:outline-none focus:ring-2 focus:ring-gov-teal" type="button">
              <MessageSquare className="h-4 w-4" />
              Message
            </button>
          </div>
        </Card>
      </div>

      <Assignments enumerators={enumerators} />
    </div>
  );
}

function Assignments({ enumerators }: { enumerators: Enumerator[] }) {
  const rows = enumerators.flatMap((enumerator) => [
    { id: `${enumerator.id}-1`, enumerator: enumerator.name, district: 'Chennai', survey: 'Household Employment Survey', status: enumerator.trustLevel === 'Red' ? 'Review' : 'On track' },
    { id: `${enumerator.id}-2`, enumerator: enumerator.name, district: 'Kancheepuram', survey: 'Labour supplement', status: 'Pending sync' }
  ]);

  return (
    <Card>
      <SectionHeader
        title="Assignments"
        eyebrow="Workload"
        actions={
          <button className="inline-flex items-center gap-2 rounded-lg bg-gov-teal px-3 py-2 text-sm font-semibold text-white" type="button">
            <Send className="h-4 w-4" />
            Message selected
          </button>
        }
      />
      <DataTable
        rows={rows}
        rowKey={(row) => row.id}
        columns={[
          { key: 'enumerator', header: 'Enumerator', render: (row) => row.enumerator, sortValue: (row) => row.enumerator },
          { key: 'district', header: 'District', render: (row) => row.district, sortValue: (row) => row.district },
          { key: 'survey', header: 'Survey', render: (row) => row.survey, sortValue: (row) => row.survey },
          { key: 'status', header: 'Status', render: (row) => row.status, sortValue: (row) => row.status }
        ]}
      />
    </Card>
  );
}
