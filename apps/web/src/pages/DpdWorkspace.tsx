import { useMemo, useState } from 'react';
import { Check, DatabaseZap, Search, ShieldAlert, Undo2 } from 'lucide-react';
import { Card, ConfidenceGauge, DataTable, ReasonPopover, SectionHeader, StatusChip } from '../components/ui';
import { seedData } from '../data/seed';
import { findCodeSuggestion, initialIntelligence, evaluateIntelligence } from '../lib/intelligence';

interface CodingRow {
  id: string;
  raw: string;
  suggested: NonNullable<ReturnType<typeof findCodeSuggestion>>;
}

export function DpdWorkspace() {
  const [expanded, setExpanded] = useState('RESP-FLAG-1');
  const codingRows = useMemo<CodingRow[]>(
    () =>
      ['auto driver', 'gehu ki kheti', 'software dev', 'uber driver']
        .map((raw, index) => {
          const suggested = findCodeSuggestion(raw);
          return suggested ? { id: `CODE-${index + 1}`, raw, suggested } : null;
        })
        .filter(Boolean) as CodingRow[],
    []
  );

  const suspiciousResult = evaluateIntelligence({
    answers: seedData.personas.suspicious.answers,
    activeQuestionId: 'income',
    persona: 'suspicious',
    speedMode: 'too-fast',
    elapsedSeconds: 4
  });

  const validationRows = [
    {
      id: 'RESP-FLAG-1',
      respondent: 'HH-TN-0042',
      enumerator: 'Suspect Enumerator',
      confidence: suspiciousResult.confidence,
      layers: suspiciousResult.layers,
      paradata: 'Question path completed in 18 seconds, GPS stable, no evidence attachment',
      action: 'Send for re-interview'
    },
    {
      id: 'RESP-OK-8',
      respondent: 'HH-TN-0048',
      enumerator: 'Lakshmi R',
      confidence: 96,
      layers: initialIntelligence.layers,
      paradata: 'Question path completed in 82 seconds, GPS stable, consent captured',
      action: 'Approve'
    }
  ];

  return (
    <div className="space-y-6">
      <SectionHeader title="Processing and coding" eyebrow="DPD workspace" />

      <Card>
        <SectionHeader
          title="Coding review queue"
          eyebrow="Semantic classification"
          actions={
            <span className="inline-flex items-center gap-2 rounded-full border border-gov-teal bg-green-50 px-3 py-1 text-xs font-semibold text-gov-teal">
              <DatabaseZap className="h-3.5 w-3.5" />
              Powered by MoSPI NIC semantic search
            </span>
          }
        />
        <DataTable
          rows={codingRows}
          rowKey={(row) => row.id}
          columns={[
            { key: 'raw', header: 'Raw response', render: (row) => <span className="font-medium text-slate-900">{row.raw}</span>, sortValue: (row) => row.raw },
            {
              key: 'suggested',
              header: 'Suggested code',
              render: (row) => (
                <span>
                  <strong className="text-gov-primary">{row.suggested.type} {row.suggested.code}</strong>
                  <span className="ml-2 text-slate-500">{row.suggested.label}</span>
                </span>
              ),
              sortValue: (row) => row.suggested.code
            },
            {
              key: 'confidence',
              header: 'Confidence',
              render: (row) => (
                <span className="inline-flex items-center gap-2">
                  {row.suggested.confidence}%
                  <ReasonPopover reason={row.suggested.reason} />
                </span>
              ),
              sortValue: (row) => row.suggested.confidence
            },
            { key: 'source', header: 'Source', render: (row) => row.suggested.source },
            {
              key: 'actions',
              header: 'Actions',
              render: (row) => (
                <div className="flex flex-wrap gap-2">
                  <button className="inline-flex items-center gap-1 rounded-lg bg-gov-primary px-2 py-1 text-xs font-semibold text-white" type="button">
                    <Check className="h-3 w-3" />
                    Approve
                  </button>
                  <button className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700" type="button">
                    <Search className="h-3 w-3" />
                    Change code
                  </button>
                </div>
              )
            }
          ]}
        />
      </Card>

      <Card>
        <SectionHeader title="Validation queue" eyebrow="Flag review" />
        <div className="space-y-3">
          {validationRows.map((row) => (
            <div key={row.id} className="rounded-lg border border-slate-200 bg-white">
              <button
                type="button"
                onClick={() => setExpanded(expanded === row.id ? '' : row.id)}
                className="flex w-full flex-wrap items-center justify-between gap-3 p-4 text-left focus:outline-none focus:ring-2 focus:ring-gov-teal"
              >
                <div>
                  <p className="font-semibold text-slate-900">{row.id} · {row.respondent}</p>
                  <p className="text-sm text-slate-500">{row.enumerator}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusChip status={row.confidence < 55 ? 'fail' : 'pass'} label={`${row.confidence}% confidence`} reason="Confidence is calculated from validation, fraud, evidence, and behaviour scores." />
                  <ShieldAlert className="h-5 w-5 text-gov-primary" />
                </div>
              </button>

              {expanded === row.id ? (
                <div className="grid gap-4 border-t border-slate-100 p-4 lg:grid-cols-[16rem_1fr]">
                  <div>
                    <ConfidenceGauge value={row.confidence} reason="Expanded score shows why this response is trusted or escalated." />
                    <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{row.paradata}</p>
                  </div>
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      {row.layers.map((layer) => (
                        <StatusChip key={layer.layer} status={layer.status} label={layer.layer} reason={layer.reason} />
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white" type="button">
                        <Check className="h-4 w-4" />
                        Approve
                      </button>
                      <button className="inline-flex items-center gap-2 rounded-lg border border-gov-red px-3 py-2 text-sm font-semibold text-gov-red" type="button">
                        <Undo2 className="h-4 w-4" />
                        Send for re-interview
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
