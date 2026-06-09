import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, DatabaseZap, Search, ShieldAlert, Undo2 } from 'lucide-react';
import { Card, ConfidenceGauge, DataTable, ReasonPopover, SectionHeader, StatusChip } from '../components/ui';
import { getCodingReviewQueue, getFlaggedResponses, getResponseDetail, reviewCoding, reviewResponse } from '../lib/apiClient';
import type { CodingReviewItem, LiveFlag, ValidationLayer } from '../types';

function statusFromTrust(score: number) {
  return score < 55 ? 'fail' : score < 75 ? 'warn' : 'pass';
}

export function DpdWorkspace() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState('');
  const codingQuery = useQuery({ queryKey: ['coding-review'], queryFn: () => getCodingReviewQueue(true) });
  const flagQuery = useQuery({ queryKey: ['flagged-responses'], queryFn: getFlaggedResponses });
  const codingRows = codingQuery.data?.data.items || [];
  const validationRows = flagQuery.data?.data.responses || [];

  const approveCodingMutation = useMutation({
    mutationFn: (row: CodingReviewItem) =>
      reviewCoding({
        id: row.id,
        responseId: row.responseId,
        field: row.field,
        rawText: row.rawText,
        suggestions: row.suggestions,
        approvedCode: row.suggested?.code,
        approvedLabel: row.suggested?.label,
        approved: true,
        confidence: row.suggested?.confidence || row.confidence,
        reason: row.suggested?.reason || 'DPD approved persisted coding suggestion'
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['coding-review'] })
  });

  return (
    <div className="space-y-6">
      <SectionHeader title="Processing and coding" eyebrow="DPD workspace" />

      <Card>
        <SectionHeader
          title="Coding review queue"
          eyebrow="Persisted semantic classification"
          actions={
            <span className="inline-flex items-center gap-2 rounded-full border border-gov-teal bg-green-50 px-3 py-1 text-xs font-semibold text-gov-teal">
              <DatabaseZap className="h-3.5 w-3.5" />
              Local code registry
            </span>
          }
        />
        {approveCodingMutation.error ? (
          <p className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-gov-red">{(approveCodingMutation.error as Error).message}</p>
        ) : null}
        <DataTable
          rows={codingRows}
          rowKey={(row) => row.id}
          empty={codingQuery.isLoading ? 'Loading coding queue...' : 'No coding rows need review.'}
          columns={[
            { key: 'raw', header: 'Raw response', render: (row) => <span className="font-medium text-slate-900">{row.rawText}</span>, sortValue: (row) => row.rawText },
            {
              key: 'suggested',
              header: 'Suggested code',
              render: (row) =>
                row.suggested ? (
                  <span>
                    <strong className="text-gov-primary">
                      {row.suggested.type} {row.suggested.code}
                    </strong>
                    <span className="ml-2 text-slate-500">{row.suggested.label}</span>
                  </span>
                ) : (
                  <span className="text-slate-500">No match</span>
                ),
              sortValue: (row) => row.suggested?.code || ''
            },
            {
              key: 'confidence',
              header: 'Confidence',
              render: (row) => (
                <span className="inline-flex items-center gap-2">
                  {Math.round(row.suggested?.confidence || row.confidence || 0)}%
                  <ReasonPopover reason={row.suggested?.reason || 'No persisted coding reason was returned'} />
                </span>
              ),
              sortValue: (row) => row.suggested?.confidence || row.confidence || 0
            },
            { key: 'source', header: 'Source', render: (row) => row.suggested?.source || row.source },
            {
              key: 'actions',
              header: 'Actions',
              render: (row) => (
                <div className="flex flex-wrap gap-2">
                  <button
                    className="inline-flex items-center gap-1 rounded-lg bg-gov-primary px-2 py-1 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                    type="button"
                    disabled={!row.suggested || approveCodingMutation.isPending}
                    onClick={() => approveCodingMutation.mutate(row)}
                  >
                    <Check className="h-3 w-3" />
                    Approve
                  </button>
                  <button className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700" type="button">
                    <Search className="h-3 w-3" />
                    Review
                  </button>
                </div>
              )
            }
          ]}
        />
      </Card>

      <Card>
        <SectionHeader title="Validation queue" eyebrow="Flag review from persisted verdicts" />
        <div className="space-y-3">
          {validationRows.map((row) => (
            <ValidationQueueItem key={row.id} row={row} expanded={expanded === row.id} onToggle={() => setExpanded(expanded === row.id ? '' : row.id)} />
          ))}
          {!validationRows.length ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">
              {flagQuery.isLoading ? 'Loading validation queue...' : 'No flagged responses need review.'}
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

function ValidationQueueItem({ row, expanded, onToggle }: { row: LiveFlag; expanded: boolean; onToggle: () => void }) {
  const queryClient = useQueryClient();
  const detailQuery = useQuery({ queryKey: ['response-detail', row.id], queryFn: () => getResponseDetail(row.id), enabled: expanded });
  const reviewMutation = useMutation({
    mutationFn: (action: 'approve' | 're_interview') =>
      reviewResponse(row.id, {
        action,
        reason: action === 'approve' ? 'DPD accepted validation evidence' : 'DPD requested re-interview from validation reasons'
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flagged-responses'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
    }
  });
  const detail = detailQuery.data?.data;
  const layers: ValidationLayer[] = detail?.validationFlags?.length ? detail.validationFlags : [{ layer: 'Verdict', status: statusFromTrust(row.trustScore), reason: row.reason }];
  const seconds = detail?.paradata?.totalSeconds;
  const paradata = seconds
    ? `Completed in ${seconds}s, corrections ${detail?.paradata?.correctionCount || 0}, back navigation ${detail?.paradata?.backNavCount || 0}`
    : 'Open details to load persisted paradata.';

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full flex-wrap items-center justify-between gap-3 p-4 text-left focus:outline-none focus:ring-2 focus:ring-gov-teal"
      >
        <div>
          <p className="font-semibold text-slate-900">
            {row.id} - {row.survey}
          </p>
          <p className="text-sm text-slate-500">{row.enumeratorName}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusChip status={statusFromTrust(row.trustScore)} label={`${Math.round(row.trustScore)}% confidence`} reason="Confidence is persisted from validation, fraud, evidence, and behaviour scores." />
          <ShieldAlert className="h-5 w-5 text-gov-primary" />
        </div>
      </button>

      {expanded ? (
        <div className="grid gap-4 border-t border-slate-100 p-4 lg:grid-cols-[16rem_1fr]">
          <div>
            <ConfidenceGauge value={Math.round(detail?.qualityScore || row.trustScore)} reason={detail?.trust?.reasons?.[0] || row.reason} />
            <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{detailQuery.isLoading ? 'Loading response detail...' : paradata}</p>
          </div>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {layers.map((layer) => (
                <StatusChip key={`${layer.layer}-${layer.reason}`} status={layer.status} label={layer.layer} reason={layer.reason} />
              ))}
            </div>
            {reviewMutation.error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-gov-red">{(reviewMutation.error as Error).message}</p> : null}
            <div className="flex flex-wrap gap-2">
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                disabled={reviewMutation.isPending}
                onClick={() => reviewMutation.mutate('approve')}
              >
                <Check className="h-4 w-4" />
                Approve
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-gov-red px-3 py-2 text-sm font-semibold text-gov-red disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                disabled={reviewMutation.isPending}
                onClick={() => reviewMutation.mutate('re_interview')}
              >
                <Undo2 className="h-4 w-4" />
                Send for re-interview
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
