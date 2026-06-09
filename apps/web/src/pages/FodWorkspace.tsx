import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Send, UserPlus } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, DataTable, SectionHeader, Sparkline, TrustBadge } from '../components/ui';
import { createAssignment, getAssignments, getEnumerators, getHouseholds } from '../lib/apiClient';
import { useLiveEvents } from '../lib/useLiveEvents';
import { useAppStore } from '../store/appStore';
import type { Assignment, Enumerator, Household } from '../types';

export function FodWorkspace() {
  const storeEnumerators = useAppStore((state) => state.enumerators);
  const liveFlags = useAppStore((state) => state.liveFlags);
  const query = useQuery({ queryKey: ['enumerators', storeEnumerators], queryFn: getEnumerators });
  const enumerators = query.data?.data.enumerators || storeEnumerators;
  const [selectedId, setSelectedId] = useState(enumerators[0]?.id || 'ENUM-A');
  const selected = enumerators.find((item) => item.id === selectedId) || enumerators[0];
  const { events, connected } = useLiveEvents();

  const trendData = useMemo(
    () => (selected?.trustTrend || []).map((value, index) => ({ day: `D-${(selected?.trustTrend || []).length - index - 1}`, trust: value })),
    [selected?.trustTrend]
  );

  if (!selected) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading field operations...</div>;
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Collection operations"
        eyebrow="FOD workspace"
        actions={
          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${connected ? 'bg-green-100 text-gov-green' : 'bg-slate-100 text-slate-600'}`}>
            {connected ? 'Live - WebSocket connected' : 'Reconnecting - polling flags'}
          </span>
        }
      />

      {events.length > 0 ? (
        <Card>
          <SectionHeader title="Live events" eyebrow={`${events.length} recent - Redis pub/sub`} />
          <ul className="divide-y divide-slate-100 text-sm">
            {events.slice(0, 5).map((ev, idx) => (
              <li key={idx} className="flex items-center justify-between px-2 py-1.5">
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-gov-primary">{String(ev.event || 'event')}</span>
                <span className="truncate text-xs text-slate-500">{JSON.stringify(ev).slice(0, 120)}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

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

      <Assignments enumerators={enumerators} selectedEnumeratorId={selected.id} />
    </div>
  );
}

function Assignments({ enumerators, selectedEnumeratorId }: { enumerators: Enumerator[]; selectedEnumeratorId: string }) {
  const queryClient = useQueryClient();
  const [surveyId, setSurveyId] = useState('emp-2026');
  const [enumeratorId, setEnumeratorId] = useState(selectedEnumeratorId);
  const [householdId, setHouseholdId] = useState('');
  const assignmentQuery = useQuery({ queryKey: ['assignments'], queryFn: () => getAssignments() });
  const householdQuery = useQuery({ queryKey: ['households'], queryFn: () => getHouseholds() });
  const rows = assignmentQuery.data?.data.assignments || [];
  const households = householdQuery.data?.data.households || [];
  const selectedEnum = enumeratorId || selectedEnumeratorId;
  const selectedHousehold = householdId || households[0]?.id || '';
  const createMutation = useMutation({
    mutationFn: () =>
      createAssignment({
        surveyId,
        enumeratorId: selectedEnum,
        householdId: selectedHousehold || undefined
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      queryClient.invalidateQueries({ queryKey: ['enumerators'] });
    }
  });

  return (
    <Card>
      <SectionHeader
        title="Assignments"
        eyebrow="Published survey workload"
        actions={
          <button className="inline-flex items-center gap-2 rounded-lg bg-gov-teal px-3 py-2 text-sm font-semibold text-white" type="button">
            <Send className="h-4 w-4" />
            Message selected
          </button>
        }
      />
      <div className="mb-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 lg:grid-cols-[1fr_1fr_1fr_auto]">
        <label className="text-xs font-semibold uppercase text-slate-500">
          Survey ID
          <input
            value={surveyId}
            onChange={(event) => setSurveyId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case text-slate-900 focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
          />
        </label>
        <label className="text-xs font-semibold uppercase text-slate-500">
          Enumerator
          <select
            value={selectedEnum}
            onChange={(event) => setEnumeratorId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case text-slate-900 focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
          >
            {enumerators.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold uppercase text-slate-500">
          Household
          <select
            value={selectedHousehold}
            onChange={(event) => setHouseholdId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case text-slate-900 focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
          >
            {households.map((item: Household) => (
              <option key={item.id} value={item.id}>
                {item.id} - {item.prepop.district}
              </option>
            ))}
          </select>
        </label>
        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 lg:mt-5"
          type="button"
          disabled={!surveyId || !selectedEnum || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          <UserPlus className="h-4 w-4" />
          {createMutation.isPending ? 'Assigning' : 'Assign'}
        </button>
      </div>
      {createMutation.error ? <p className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-gov-red">{(createMutation.error as Error).message}</p> : null}
      <DataTable
        rows={rows}
        rowKey={(row) => row.id}
        empty={assignmentQuery.isLoading ? 'Loading assignments...' : 'No assignments have been created yet.'}
        columns={[
          { key: 'enumerator', header: 'Enumerator', render: (row: Assignment) => row.enumeratorName, sortValue: (row) => row.enumeratorName },
          { key: 'district', header: 'Household', render: (row) => row.householdId || 'Open', sortValue: (row) => row.householdId || '' },
          { key: 'survey', header: 'Survey', render: (row) => row.surveyTitle || row.surveyId, sortValue: (row) => row.surveyTitle || row.surveyId },
          { key: 'status', header: 'Status', render: (row) => row.status, sortValue: (row) => row.status }
        ]}
      />
    </Card>
  );
}
