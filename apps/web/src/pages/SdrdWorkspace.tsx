import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, Eye, FilePlus2, Plus, Send, SlidersHorizontal, Trash2, Upload } from 'lucide-react';
import { Card, DataTable, ReasonPopover, SectionHeader, StatusChip } from '../components/ui';
import {
  createAdaptiveLogic,
  createSurvey,
  createValidationRule,
  deleteAdaptiveLogic,
  deleteValidationRule,
  generateSurvey,
  getAdaptiveLogic,
  getCodes,
  getQuestionBank,
  getSurvey,
  getSurveys,
  getValidationRules,
  patchSurvey,
  publishSurvey,
  ragIngest,
  ragStatus
} from '../lib/apiClient';
import { cn } from '../lib/format';
import { getQuestionText } from '../lib/intelligence';
import { useAppStore } from '../store/appStore';
import type { Assignment, Language, Survey, SurveyQuestion } from '../types';

const languageTabs: Language[] = ['en', 'hi', 'ta'];

export function SdrdWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'surveys';

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Survey design"
        eyebrow="SDRD workspace"
        actions={
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-amber-50 px-2 py-1 font-semibold text-amber-700">All AI outputs marked needs_review · is_verdict:false</span>
          </div>
        }
      />

      {activeTab === 'surveys' || activeTab === 'builder' ? (
        <BuilderTab activeTab={activeTab} setSearchParams={setSearchParams} />
      ) : null}
      {activeTab === 'bank' ? <QuestionBankTab /> : null}
      {activeTab === 'codes' ? <CodeLibraryTab /> : null}
      {activeTab === 'rules' ? <RulesTab /> : null}
      {activeTab === 'kb' ? <KnowledgeBaseTab /> : null}
    </div>
  );
}

// ============================================================================
// BUILDER — My Surveys list + canvas + properties panel
// ============================================================================

function BuilderTab({ activeTab, setSearchParams }: { activeTab: string; setSearchParams: (p: URLSearchParams) => void }) {
  const queryClient = useQueryClient();
  const language = useAppStore((state) => state.language);

  const surveysQuery = useQuery({ queryKey: ['surveys'], queryFn: getSurveys });
  const [selectedSurveyId, setSelectedSurveyId] = useState<string | null>(null);

  // Auto-pick first survey when list loads
  useEffect(() => {
    const surveys = surveysQuery.data?.data.surveys || [];
    if (!selectedSurveyId && surveys.length > 0) {
      setSelectedSurveyId(surveys[0].id);
    }
  }, [surveysQuery.data, selectedSurveyId]);

  const surveyQuery = useQuery({
    queryKey: ['survey', selectedSurveyId],
    queryFn: () => getSurvey(selectedSurveyId!),
    enabled: !!selectedSurveyId
  });

  const surveys = surveysQuery.data?.data.surveys || [];
  const survey = surveyQuery.data?.data.survey as (Survey & { status?: string; version?: number }) | undefined;

  return (
    <div className="space-y-6">
      {activeTab === 'surveys' ? (
        <Card className="space-y-3">
          <SectionHeader title="My surveys" eyebrow={`${surveys.length} survey${surveys.length === 1 ? '' : 's'}`} />
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-600">
              <tr>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Version</th>
                <th className="px-3 py-2">Domain</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {surveys.map((s) => {
                const title = (s.title?.en as string) || s.id;
                const status = (s as { status?: string }).status || 'draft';
                const version = (s as { version?: number }).version || 1;
                const domain = ((s.metadata as { domain?: string })?.domain) || '—';
                return (
                  <tr key={s.id} className={selectedSurveyId === s.id ? 'bg-indigo-50' : 'bg-white'}>
                    <td className="px-3 py-2 font-medium text-gov-primary">{title}</td>
                    <td className="px-3 py-2">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold', status === 'published' ? 'bg-green-100 text-gov-green' : 'bg-amber-100 text-amber-700')}>
                        {status}
                      </span>
                    </td>
                    <td className="px-3 py-2">v{version}</td>
                    <td className="px-3 py-2 text-slate-600">{domain}</td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedSurveyId(s.id);
                          const params = new URLSearchParams(); params.set('tab', 'builder'); setSearchParams(params);
                        }}
                        className="rounded-lg bg-gov-primary px-3 py-1 text-xs font-semibold text-white"
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                );
              })}
              {surveys.length === 0 ? (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-500">No surveys yet — generate one with AI Assist below.</td></tr>
              ) : null}
            </tbody>
          </table>
        </Card>
      ) : null}

      {activeTab === 'builder' && survey ? (
        <BuilderCanvas
          key={survey.id}
          survey={survey}
          language={language}
          onAfterSave={() => queryClient.invalidateQueries({ queryKey: ['surveys'] })}
        />
      ) : null}

      {activeTab === 'surveys' ? (
        <AssistDraftPanel
          selectedSurvey={survey}
          onDraftAccepted={(acceptedSurveyId) => {
            setSelectedSurveyId(acceptedSurveyId);
            queryClient.invalidateQueries({ queryKey: ['surveys'] });
            queryClient.invalidateQueries({ queryKey: ['survey', acceptedSurveyId] });
            const params = new URLSearchParams();
            params.set('tab', 'builder');
            setSearchParams(params);
          }}
        />
      ) : null}
    </div>
  );
}

// ============================================================================
// BUILDER CANVAS — debounced PATCH on edits + Publish button
// ============================================================================

interface CanvasState {
  title: Record<string, string>;
  nodes: SurveyQuestion[];
  branches: Record<string, unknown>;
  dirty: boolean;
  saving: boolean;
  lastSavedAt?: number;
  publishedAt?: string;
  assignment?: Assignment;
}

function BuilderCanvas({ survey, language, onAfterSave }: { survey: Survey & { status?: string; version?: number }; language: Language; onAfterSave: () => void }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<CanvasState>({
    title: survey.title || { en: survey.id },
    nodes: (survey.nodes || []).filter((n) => n.type !== 'adaptive'),
    branches: survey.branches || {},
    dirty: false,
    saving: false
  });
  const [selectedId, setSelectedId] = useState<string | null>(state.nodes[0]?.id || null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isPublished = (survey.status === 'published');

  // Debounced PATCH on every edit
  useEffect(() => {
    if (!state.dirty || isPublished) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      setState((s) => ({ ...s, saving: true }));
      const payload = {
        title: state.title,
        question_graph: { id: survey.id, title: state.title, nodes: state.nodes, branches: state.branches }
      };
      await patchSurvey(survey.id, payload);
      setState((s) => ({ ...s, saving: false, dirty: false, lastSavedAt: Date.now() }));
      queryClient.invalidateQueries({ queryKey: ['survey', survey.id] });
      onAfterSave();
    }, 800);
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current); };
  }, [state.dirty, state.title, state.nodes, state.branches, survey.id, isPublished, onAfterSave, queryClient]);

  const publishMutation = useMutation({
    mutationFn: () => publishSurvey(survey.id),
    onSuccess: ({ data }) => {
      setState((s) => ({ ...s, publishedAt: data.published_at || new Date().toISOString(), assignment: data.assignment }));
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['survey', survey.id] });
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      onAfterSave();
    }
  });

  function updateNode(id: string, updater: (n: SurveyQuestion) => SurveyQuestion) {
    setState((s) => ({ ...s, dirty: true, nodes: s.nodes.map((n) => (n.id === id ? updater(n) : n)) }));
  }

  function addNode(type: SurveyQuestion['type']) {
    const id = `q-${Date.now().toString(36)}`;
    const next: SurveyQuestion = {
      id,
      type,
      q: { en: 'New question', hi: 'नया प्रश्न', ta: 'புதிய கேள்வி' },
      rules: type === 'number' ? { range: [0, 100] } : undefined,
      options: type === 'choice' || type === 'multi' ? ['Option 1', 'Option 2'] : undefined
    };
    setState((s) => ({ ...s, dirty: true, nodes: [...s.nodes, next] }));
    setSelectedId(id);
  }

  function deleteNode(id: string) {
    setState((s) => ({ ...s, dirty: true, nodes: s.nodes.filter((n) => n.id !== id) }));
    if (selectedId === id) setSelectedId(null);
  }

  const selectedNode = state.nodes.find((n) => n.id === selectedId);
  const status = state.saving ? 'Saving…' : state.dirty ? 'Pending…' : state.lastSavedAt ? `Saved · ${new Date(state.lastSavedAt).toLocaleTimeString()}` : 'Synced';

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <input
            value={state.title.en || ''}
            onChange={(e) => setState((s) => ({ ...s, dirty: true, title: { ...s.title, en: e.target.value } }))}
            disabled={isPublished}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-lg font-semibold text-gov-primary disabled:bg-slate-50"
          />
          <div className="mt-1 flex items-center gap-2 text-xs">
            <span className={cn('rounded-full px-2 py-0.5 font-semibold', isPublished ? 'bg-green-100 text-gov-green' : 'bg-amber-100 text-amber-700')}>
              {survey.status || 'draft'} · v{survey.version || 1}
            </span>
            <span className="text-slate-500">{status}</span>
            <span className="text-slate-400">·</span>
            <span className="text-slate-500">{state.nodes.length} questions</span>
            {state.assignment ? (
              <>
                <span className="text-slate-400">·</span>
                <span className="text-gov-teal">Assigned to {state.assignment.enumeratorName}</span>
              </>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {state.assignment ? (
            <Link
              to={`/collect/${survey.id}`}
              className="inline-flex items-center gap-2 rounded-lg border border-gov-teal px-3 py-2 text-sm font-semibold text-gov-teal hover:bg-green-50"
            >
              <Send className="h-4 w-4" />
              Collect
            </Link>
          ) : null}
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
            disabled
          >
            <Eye className="h-4 w-4" />
            Preview
          </button>
          <button
            type="button"
            onClick={() => publishMutation.mutate()}
            disabled={isPublished || publishMutation.isPending || state.saving}
            className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white hover:bg-gov-primaryDark disabled:bg-slate-300"
          >
            <Check className="h-4 w-4" />
            {publishMutation.isPending ? 'Publishing…' : isPublished ? 'Published' : 'Publish'}
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[16rem_1fr_22rem]">
        {/* Palette */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Add question</h3>
          {(['choice', 'multi', 'number', 'text', 'date'] as SurveyQuestion['type'][]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => addNode(type)}
              disabled={isPublished}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <span className="capitalize">{type === 'multi' ? 'Multi select' : type}</span>
              <Plus className="h-4 w-4" />
            </button>
          ))}
        </div>

        {/* Canvas — question cards */}
        <div className="space-y-2">
          {state.nodes.map((node, index) => (
            <button
              key={node.id}
              type="button"
              onClick={() => setSelectedId(node.id)}
              className={cn('flex w-full items-start gap-3 rounded-lg border p-3 text-left', selectedId === node.id ? 'border-gov-primary bg-indigo-50' : 'border-slate-200 bg-white hover:bg-slate-50')}
            >
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">Q{index + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase text-gov-teal">{node.type}{node.codeType ? ` · auto-code ${node.codeType}` : ''}</p>
                <p className="mt-1 font-medium text-slate-900">{getQuestionText(node, language) || '(untitled)'}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                  {node.rules?.range ? <StatusChip status="pass" label={`Range ${node.rules.range[0]}-${node.rules.range[1]}`} reason="Numeric range" /> : null}
                  {node.rules?.crossField ? <StatusChip status="warn" label="Cross-field" reason="Cross-field rule" /> : null}
                </div>
              </div>
              {!isPublished ? (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); deleteNode(node.id); }}
                  className="rounded p-1 text-slate-400 hover:text-gov-red"
                  aria-label="Delete question"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              ) : null}
            </button>
          ))}
          {state.nodes.length === 0 ? <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">No questions yet. Add one from the palette.</p> : null}
        </div>

        {/* Properties panel */}
        <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-gov-primary" />
            <h2 className="text-sm font-semibold text-gov-primary">Properties</h2>
          </div>
          {selectedNode ? (
            <NodeProperties
              node={selectedNode}
              onChange={(updater) => updateNode(selectedNode.id, updater)}
              disabled={isPublished}
            />
          ) : (
            <p className="text-sm text-slate-500">Select a question card to edit.</p>
          )}
        </div>
      </div>
    </Card>
  );
}

function NodeProperties({ node, onChange, disabled }: { node: SurveyQuestion; onChange: (u: (n: SurveyQuestion) => SurveyQuestion) => void; disabled: boolean }) {
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  return (
    <>
      <div className="flex gap-1.5">
        {languageTabs.map((lang) => (
          <button
            key={lang}
            type="button"
            onClick={() => setLanguage(lang)}
            className={cn('rounded-full border px-2 py-0.5 text-xs font-semibold', language === lang ? 'border-gov-primary bg-gov-primary text-white' : 'border-slate-200 text-slate-600')}
          >
            {lang.toUpperCase()}
          </button>
        ))}
      </div>
      <label className="block">
        <span className="text-xs font-medium text-slate-700">Question label ({language.toUpperCase()})</span>
        <textarea
          value={node.q?.[language] || ''}
          onChange={(e) => onChange((n) => ({ ...n, q: { ...(n.q || {}), [language]: e.target.value } }))}
          disabled={disabled}
          rows={2}
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-700">Auto-code as</span>
        <select
          value={node.codeType || ''}
          onChange={(e) => onChange((n) => ({ ...n, codeType: e.target.value || null }))}
          disabled={disabled}
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100"
        >
          <option value="">None</option>
          <option value="NCO">NCO</option>
          <option value="NIC">NIC</option>
          <option value="ISIC">ISIC</option>
        </select>
      </label>
      {node.type === 'number' ? (
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="text-xs font-medium text-slate-700">Min</span>
            <input
              type="number"
              value={node.rules?.range?.[0] ?? 0}
              onChange={(e) => onChange((n) => ({ ...n, rules: { ...(n.rules || {}), range: [Number(e.target.value), n.rules?.range?.[1] ?? 100] } }))}
              disabled={disabled}
              className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-700">Max</span>
            <input
              type="number"
              value={node.rules?.range?.[1] ?? 100}
              onChange={(e) => onChange((n) => ({ ...n, rules: { ...(n.rules || {}), range: [n.rules?.range?.[0] ?? 0, Number(e.target.value)] } }))}
              disabled={disabled}
              className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100"
            />
          </label>
        </div>
      ) : null}
      <div className="rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-600">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-800">Reason text</span>
          <ReasonPopover reason="Every rule emits a plain-language reason for the validation queue and the collection Intelligence Panel." />
        </div>
      </div>
    </>
  );
}

// ============================================================================
// ASSIST DRAFT — POST /api/surveys/generate (no DB write) + accept into canvas
// ============================================================================

function AssistDraftPanel({
  onDraftAccepted,
  selectedSurvey
}: {
  onDraftAccepted: (surveyId: string) => void;
  selectedSurvey?: (Survey & { status?: string; version?: number }) | null;
}) {
  const [prompt, setPrompt] = useState('Design a household employment survey for Tamil Nadu with demographic, occupation, income, and household validation.');
  const [draft, setDraft] = useState<{ survey: Survey; note: string; assist?: { model?: string; needs_review?: boolean; is_verdict?: boolean }; sources?: unknown[] } | null>(null);
  const [acceptMessage, setAcceptMessage] = useState('');
  const [accepting, setAccepting] = useState(false);

  const mutation = useMutation({
    mutationFn: () => generateSurvey(prompt),
    onSuccess: ({ data }) => {
      const meta = (data.survey.metadata || {}) as { assist?: { model?: string; needs_review?: boolean; is_verdict?: boolean } };
      setAcceptMessage('');
      setDraft({
        survey: data.survey,
        note: data.note,
        assist: meta.assist,
        sources: (data as { sources?: unknown[] }).sources
      });
    }
  });

  async function acceptIntoSurvey() {
    if (!draft) return;
    setAccepting(true);
    setAcceptMessage('');
    const nodes = (draft.survey.nodes || []).filter((n) => n.type !== 'adaptive');
    const targetSurveyId = selectedSurvey?.id || draft.survey.id;
    const graph = {
      id: targetSurveyId,
      title: draft.survey.title,
      nodes,
      branches: draft.survey.branches || {},
      metadata: draft.survey.metadata || {}
    };

    try {
      if (selectedSurvey && selectedSurvey.status !== 'published') {
        await patchSurvey(selectedSurvey.id, {
          title: draft.survey.title,
          question_graph: graph
        });
        setDraft(null);
        onDraftAccepted(selectedSurvey.id);
        return;
      }

      const newSurveyId = `draft-${Date.now().toString(36)}`;
      const createResult = await createSurvey({
        id: newSurveyId,
        title: draft.survey.title,
        metadata: draft.survey.metadata,
        question_graph: { ...graph, id: newSurveyId },
        nodes,
        branches: draft.survey.branches || {}
      });
      setDraft(null);
      onDraftAccepted(createResult.data.survey.id);
    } catch (error) {
      setAcceptMessage(error instanceof Error ? error.message : 'Could not store generated survey draft');
    } finally {
      setAccepting(false);
    }
  }

  const canPatchSelected = selectedSurvey && selectedSurvey.status !== 'published';
  const acceptLabel = canPatchSelected
    ? `Accept into ${selectedSurvey.id}`
    : selectedSurvey
      ? 'Create editable draft'
      : 'Create survey draft';

  return (
    <Card className="space-y-3">
      <SectionHeader title="AI Assist" eyebrow="Local Gemma · is_verdict:false · needs_review:true" />
      <label className="block">
        <span className="text-sm font-semibold text-slate-700">Describe the survey you need</span>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">Draft is held in memory until you accept it into a survey — nothing is written to the DB at generate time.</p>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-gov-teal px-3 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
        >
          <FilePlus2 className="h-4 w-4" />
          {mutation.isPending ? 'Generating…' : 'Generate draft'}
        </button>
      </div>

      {draft ? (
        <div className="space-y-3 rounded-lg border border-gov-teal bg-amber-50 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-white px-2 py-0.5 font-semibold text-gov-teal">Draft</span>
              {draft.assist?.model ? <span className="text-slate-600">Model: <strong>{draft.assist.model}</strong></span> : null}
              <span className="rounded-full bg-amber-200 px-2 py-0.5 font-semibold text-amber-900">needs_review</span>
              <span className="rounded-full bg-amber-200 px-2 py-0.5 font-semibold text-amber-900">is_verdict:false</span>
            </div>
            <button
              type="button"
              onClick={acceptIntoSurvey}
              disabled={accepting}
              className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-1 text-xs font-semibold text-white disabled:bg-slate-300"
            >
              <Send className="h-3 w-3" />
              {accepting ? 'Storing...' : acceptLabel}
            </button>
          </div>
          {selectedSurvey?.status === 'published' ? (
            <p className="rounded-md border border-amber-200 bg-white px-2 py-1 text-xs text-amber-800">
              {selectedSurvey.id} is published, so SATARK will store this output as a new editable draft instead of modifying the published survey.
            </p>
          ) : null}
          {acceptMessage ? (
            <p className="rounded-md border border-gov-red bg-red-50 px-2 py-1 text-xs text-gov-red">{acceptMessage}</p>
          ) : null}
          <p className="text-xs text-slate-600">{draft.note}</p>
          <div className="rounded border border-slate-200 bg-white p-2 text-xs">
            <p className="font-semibold text-slate-700">{draft.survey.title.en}</p>
            <p className="mt-1 text-slate-500">{(draft.survey.nodes || []).filter((n) => n.type !== 'adaptive').length} draft questions</p>
          </div>
          <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-white">
            {(draft.survey.nodes || []).filter((n) => n.type !== 'adaptive').map((node, index) => (
              <div key={node.id} className="border-b border-slate-100 p-3 last:border-b-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">Q{index + 1}</span>
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold uppercase text-gov-primary">{node.type}</span>
                  {node.codeType ? <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-gov-teal">{node.codeType}</span> : null}
                  {node.rules?.range ? (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                      Range {node.rules.range[0]}-{node.rules.range[1]}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-sm font-medium text-slate-900">{getQuestionText(node, 'en')}</p>
                {node.options?.length ? (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {node.options.map((option) => (
                      <span key={option} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
                        {option}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}

// ============================================================================
// QUESTION BANK
// ============================================================================

function QuestionBankTab() {
  const language = useAppStore((state) => state.language);
  const bank = useQuery({ queryKey: ['question-bank'], queryFn: getQuestionBank });
  const rows = bank.data?.data.questions || [];
  return (
    <Card>
      <SectionHeader title="Question bank" eyebrow={`${rows.length} reusable items`} />
      <DataTable
        rows={rows}
        rowKey={(row) => row.id}
        columns={[
          { key: 'question', header: 'Question', render: (row) => getQuestionText(row, language) || row.id, sortValue: (row) => getQuestionText(row, language) || row.id },
          { key: 'type', header: 'Type', render: (row) => row.type, sortValue: (row) => row.type },
          { key: 'code', header: 'Code', render: (row) => row.codeType || 'None' },
          { key: 'languages', header: 'Languages', render: (row) => Object.keys(row.q || {}).join(', ').toUpperCase() }
        ]}
      />
    </Card>
  );
}

// ============================================================================
// CODE LIBRARY
// ============================================================================

function CodeLibraryTab() {
  const codes = useQuery({ queryKey: ['codes'], queryFn: getCodes });
  const rows = codes.data?.data.codes || [];
  return (
    <Card>
      <SectionHeader title="Code library" eyebrow={`${rows.length} NCO / NIC / ISIC codes`} />
      <DataTable
        rows={rows}
        rowKey={(row) => `${row.type}-${row.code}`}
        columns={[
          { key: 'code', header: 'Code', render: (row) => <span className="font-semibold text-gov-primary">{row.code}</span>, sortValue: (row) => row.code },
          { key: 'type', header: 'Type', render: (row) => row.type, sortValue: (row) => row.type },
          { key: 'label', header: 'Label', render: (row) => row.label, sortValue: (row) => row.label },
          { key: 'source', header: 'Source', render: (row) => row.externalSource || 'Local' }
        ]}
      />
    </Card>
  );
}

// ============================================================================
// RULES — validation rules + adaptive logic CRUD
// ============================================================================

function RulesTab() {
  const surveysQuery = useQuery({ queryKey: ['surveys'], queryFn: getSurveys });
  const surveys = surveysQuery.data?.data.surveys || [];
  const [surveyId, setSurveyId] = useState<string>('');
  useEffect(() => { if (!surveyId && surveys.length > 0) setSurveyId(surveys[0].id); }, [surveys, surveyId]);

  return (
    <div className="space-y-4">
      <Card>
        <label className="block">
          <span className="text-sm font-semibold text-slate-700">Survey</span>
          <select
            value={surveyId}
            onChange={(e) => setSurveyId(e.target.value)}
            className="mt-1 w-full max-w-md rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">(select)</option>
            {surveys.map((s) => <option key={s.id} value={s.id}>{(s.title?.en as string) || s.id}</option>)}
          </select>
        </label>
      </Card>
      {surveyId ? <ValidationRulesPanel surveyId={surveyId} /> : null}
      {surveyId ? <AdaptiveLogicPanel surveyId={surveyId} /> : null}
    </div>
  );
}

function ValidationRulesPanel({ surveyId }: { surveyId: string }) {
  const queryClient = useQueryClient();
  const rulesQuery = useQuery({ queryKey: ['validation-rules', surveyId], queryFn: () => getValidationRules(surveyId) });
  const rules = rulesQuery.data?.data.rules || [];
  const [field, setField] = useState('income');
  const [ruleType, setRuleType] = useState('range');
  const [params, setParams] = useState('{"min":0,"max":1000000}');
  const [severity, setSeverity] = useState('warn');
  const [reasonTemplate, setReasonTemplate] = useState('Income {value} outside expected band');

  const createMut = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown> = {};
      try { parsed = JSON.parse(params); } catch { /* ignore */ }
      return createValidationRule({ survey_id: surveyId, field, rule_type: ruleType, params: parsed, severity, reason_template: reasonTemplate });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['validation-rules', surveyId] })
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteValidationRule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['validation-rules', surveyId] })
  });

  return (
    <Card className="space-y-3">
      <SectionHeader title="Validation rules" eyebrow={`${rules.length} rules · consumed by verdict lane at collection time`} />
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-600">
          <tr>
            <th className="px-3 py-2">Field</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Params</th>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Reason</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rules.map((r) => (
            <tr key={r.id}>
              <td className="px-3 py-2 font-medium">{r.field}</td>
              <td className="px-3 py-2">{r.rule_type}</td>
              <td className="px-3 py-2 text-xs text-slate-600">{JSON.stringify(r.params)}</td>
              <td className="px-3 py-2"><StatusChip status={r.severity === 'fail' ? 'fail' : r.severity === 'warn' ? 'warn' : 'pass'} label={r.severity} reason={r.reason_template} /></td>
              <td className="px-3 py-2 text-xs">{r.reason_template}</td>
              <td className="px-3 py-2">
                <button onClick={() => deleteMut.mutate(r.id)} className="rounded p-1 text-slate-400 hover:text-gov-red"><Trash2 className="h-4 w-4" /></button>
              </td>
            </tr>
          ))}
          {rules.length === 0 ? <tr><td colSpan={6} className="px-3 py-3 text-center text-slate-500">No rules yet.</td></tr> : null}
        </tbody>
      </table>
      <div className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-6">
        <input value={field} onChange={(e) => setField(e.target.value)} placeholder="field" className="rounded-lg border border-slate-300 px-2 py-1 text-sm" />
        <input value={ruleType} onChange={(e) => setRuleType(e.target.value)} placeholder="rule type" className="rounded-lg border border-slate-300 px-2 py-1 text-sm" />
        <input value={params} onChange={(e) => setParams(e.target.value)} placeholder='{"min":0,"max":100}' className="rounded-lg border border-slate-300 px-2 py-1 text-sm md:col-span-2" />
        <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="rounded-lg border border-slate-300 px-2 py-1 text-sm">
          <option value="info">info</option>
          <option value="warn">warn</option>
          <option value="fail">fail</option>
        </select>
        <button type="button" onClick={() => createMut.mutate()} disabled={createMut.isPending} className="rounded-lg bg-gov-primary px-3 py-1 text-sm font-semibold text-white">Add rule</button>
        <input value={reasonTemplate} onChange={(e) => setReasonTemplate(e.target.value)} placeholder="reason template" className="rounded-lg border border-slate-300 px-2 py-1 text-sm md:col-span-6" />
      </div>
    </Card>
  );
}

function AdaptiveLogicPanel({ surveyId }: { surveyId: string }) {
  const queryClient = useQueryClient();
  const rulesQuery = useQuery({ queryKey: ['adaptive-logic', surveyId], queryFn: () => getAdaptiveLogic(surveyId) });
  const rules = rulesQuery.data?.data.rules || [];
  const [trigger, setTrigger] = useState('{"if":"occupation","equals":"Student"}');
  const [action, setAction] = useState('branch');
  const [target, setTarget] = useState('{"node":"institution"}');

  const createMut = useMutation({
    mutationFn: () => {
      let parsedTrigger: Record<string, unknown> = {};
      let parsedTarget: Record<string, unknown> = {};
      try { parsedTrigger = JSON.parse(trigger); } catch { /* ignore */ }
      try { parsedTarget = JSON.parse(target); } catch { /* ignore */ }
      return createAdaptiveLogic({ survey_id: surveyId, trigger: parsedTrigger, action, target: parsedTarget });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adaptive-logic', surveyId] })
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteAdaptiveLogic(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adaptive-logic', surveyId] })
  });

  return (
    <Card className="space-y-3">
      <SectionHeader title="Adaptive logic" eyebrow={`${rules.length} branches/skips/simplifications`} />
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-600">
          <tr><th className="px-3 py-2">Trigger</th><th className="px-3 py-2">Action</th><th className="px-3 py-2">Target</th><th></th></tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rules.map((r) => (
            <tr key={r.id}>
              <td className="px-3 py-2 text-xs">{JSON.stringify(r.trigger)}</td>
              <td className="px-3 py-2">{r.action}</td>
              <td className="px-3 py-2 text-xs">{JSON.stringify(r.target)}</td>
              <td className="px-3 py-2"><button onClick={() => deleteMut.mutate(r.id)} className="rounded p-1 text-slate-400 hover:text-gov-red"><Trash2 className="h-4 w-4" /></button></td>
            </tr>
          ))}
          {rules.length === 0 ? <tr><td colSpan={4} className="px-3 py-3 text-center text-slate-500">No adaptive rules yet.</td></tr> : null}
        </tbody>
      </table>
      <div className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-7">
        <input value={trigger} onChange={(e) => setTrigger(e.target.value)} placeholder='{"if":"occupation","equals":"Student"}' className="rounded-lg border border-slate-300 px-2 py-1 text-sm md:col-span-3" />
        <select value={action} onChange={(e) => setAction(e.target.value)} className="rounded-lg border border-slate-300 px-2 py-1 text-sm">
          <option value="branch">branch</option>
          <option value="skip">skip</option>
          <option value="simplify">simplify</option>
        </select>
        <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder='{"node":"institution"}' className="rounded-lg border border-slate-300 px-2 py-1 text-sm md:col-span-2" />
        <button type="button" onClick={() => createMut.mutate()} disabled={createMut.isPending} className="rounded-lg bg-gov-primary px-3 py-1 text-sm font-semibold text-white">Add</button>
      </div>
    </Card>
  );
}

// ============================================================================
// KNOWLEDGE BASE — PDF/MD ingest into Chroma buckets (admin scope)
// ============================================================================

function KnowledgeBaseTab() {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ['rag-status'], queryFn: ragStatus });
  const [bucket, setBucket] = useState('survey_generation');
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string>('');

  const ingestMut = useMutation({
    mutationFn: () => file ? ragIngest(file, bucket) : Promise.reject(new Error('no file')),
    onSuccess: ({ data }) => {
      setMessage(`Ingested ${data.chunk_count} chunks into ${data.bucket} (sha256 ${data.sha256.slice(0, 8)})`);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ['rag-status'] });
    },
    onError: (err) => setMessage(`Failed: ${err instanceof Error ? err.message : 'unknown'} (admin scope required)`)
  });

  const status = statusQuery.data?.data;

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <SectionHeader title="Knowledge base" eyebrow="Admin scope · Chroma vector store · keyword fallback" />
        <div className="grid gap-4 md:grid-cols-3">
          {(['survey_generation', 'validation', 'general'] as const).map((b) => (
            <div key={b} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">{b.replace('_', ' ')}</p>
              <p className="mt-2 text-2xl font-semibold text-gov-primary">{status?.buckets?.[b]?.chroma_count ?? 0}</p>
              <p className="text-xs text-slate-500">chunks in Chroma</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Chroma: <strong className={status?.enabled ? 'text-gov-green' : 'text-gov-red'}>{status?.enabled ? 'connected' : 'keyword-fallback only'}</strong>
        </p>
      </Card>

      <Card className="space-y-3">
        <SectionHeader title="Upload document" eyebrow="PDF · TXT · MD · JSON — chunked + embedded into bucket" />
        <div className="grid gap-3 md:grid-cols-3">
          <label className="block">
            <span className="text-xs font-semibold text-slate-700">Bucket</span>
            <select value={bucket} onChange={(e) => setBucket(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm">
              <option value="survey_generation">survey_generation (drives AI Assist)</option>
              <option value="validation">validation (drives verdict-lane rules)</option>
              <option value="general">general</option>
            </select>
          </label>
          <label className="block md:col-span-2">
            <span className="text-xs font-semibold text-slate-700">File</span>
            <input type="file" accept=".pdf,.txt,.md,.json" onChange={(e) => setFile(e.target.files?.[0] || null)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1 text-sm" />
          </label>
        </div>
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">{file ? `Ready: ${file.name} · ${Math.round(file.size / 1024)} KB` : 'No file selected'}</p>
          <button
            type="button"
            onClick={() => ingestMut.mutate()}
            disabled={!file || ingestMut.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
          >
            <Upload className="h-4 w-4" />
            {ingestMut.isPending ? 'Uploading…' : 'Upload + index'}
          </button>
        </div>
        {message ? <p className="rounded-lg border border-slate-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{message}</p> : null}
      </Card>
    </div>
  );
}
