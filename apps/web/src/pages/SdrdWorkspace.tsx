import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Check, Eye, FilePlus2, Plus, Send, SlidersHorizontal } from 'lucide-react';
import { Card, DataTable, ReasonPopover, SectionHeader, StatusChip } from '../components/ui';
import { seedData } from '../data/seed';
import { generateSurvey, getCodes, getQuestionBank } from '../lib/apiClient';
import { cn } from '../lib/format';
import { getQuestionText } from '../lib/intelligence';
import { useAppStore } from '../store/appStore';
import type { Language, SurveyQuestion } from '../types';

const languageTabs: Language[] = ['en', 'hi', 'ta'];

export function SdrdWorkspace() {
  const [searchParams] = useSearchParams();
  const language = useAppStore((state) => state.language);
  const [surveyTitle, setSurveyTitle] = useState(seedData.survey.title.en);
  const [questions, setQuestions] = useState<SurveyQuestion[]>(seedData.survey.nodes.filter((node) => node.type !== 'adaptive'));
  const [selectedId, setSelectedId] = useState(questions[0]?.id);
  const [promptOpen, setPromptOpen] = useState(true);
  const [prompt, setPrompt] = useState('Design a household employment survey for Tamil Nadu with demographic, occupation, income, and household validation.');
  const [published, setPublished] = useState(false);
  const [draftNote, setDraftNote] = useState('');

  const activeTab = searchParams.get('tab') || 'builder';
  const selectedQuestion = questions.find((question) => question.id === selectedId) || questions[0];
  const questionBank = useQuery({ queryKey: ['question-bank'], queryFn: getQuestionBank });
  const codes = useQuery({ queryKey: ['codes'], queryFn: getCodes });
  const draftMutation = useMutation({
    mutationFn: () => generateSurvey(prompt),
    onSuccess: ({ data }) => {
      setSurveyTitle(data.survey.title.en);
      setQuestions(data.survey.nodes.filter((node) => node.type !== 'adaptive'));
      setSelectedId(data.survey.nodes.find((node) => node.type !== 'adaptive')?.id || '');
      const llm = data.survey.metadata?.llm as { model?: string; privacy?: string; role?: string } | undefined;
      setDraftNote(
        llm?.model
          ? `Local LLM planner: ${llm.model} · ${llm.privacy || 'local inference'} · ${llm.role || 'intent planning'}`
          : data.note
      );
      setPublished(false);
    }
  });

  const questionBankRows = questionBank.data?.data.questions || seedData.survey.nodes.filter((node) => node.type !== 'adaptive');
  const codeRows = codes.data?.data.codes || seedData.codes;

  function addQuestion(type: SurveyQuestion['type']) {
    const nextQuestion: SurveyQuestion = {
      id: `q-${questions.length + 1}`,
      type,
      q: { en: 'New question', hi: 'नया प्रश्न', ta: 'புதிய கேள்வி' },
      rules: type === 'number' ? { range: [0, 100] } : undefined,
      options: type === 'choice' || type === 'multi' ? ['Option 1', 'Option 2'] : undefined
    };
    setQuestions((items) => [...items, nextQuestion]);
    setSelectedId(nextQuestion.id);
    setPublished(false);
  }

  function addFromBank(question: SurveyQuestion) {
    const copy = { ...question, id: `${question.id}-${questions.length + 1}` };
    setQuestions((items) => [...items, copy]);
    setSelectedId(copy.id);
    setPublished(false);
  }

  function updateSelected(updater: (question: SurveyQuestion) => SurveyQuestion) {
    if (!selectedQuestion) return;
    setQuestions((items) => items.map((question) => (question.id === selectedQuestion.id ? updater(question) : question)));
    setPublished(false);
  }

  function updateLabel(nextLanguage: Language, value: string) {
    updateSelected((question) => ({
      ...question,
      q: {
        ...(question.q || {}),
        [nextLanguage]: value
      }
    }));
  }

  const previewQuestions = useMemo(
    () =>
      questions.map((question, index) => ({
        ...question,
        display: `Q${index + 1}`,
        text: getQuestionText(question, language)
      })),
    [language, questions]
  );

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Survey design"
        eyebrow="SDRD workspace"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setPromptOpen((value) => !value)}
              className="inline-flex items-center gap-2 rounded-lg border border-gov-primary px-3 py-2 text-sm font-semibold text-gov-primary focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              <Send className="h-4 w-4" />
              Generate from prompt
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              <Eye className="h-4 w-4" />
              Preview
            </button>
            <button
              type="button"
              onClick={() => setPublished(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-3 py-2 text-sm font-semibold text-white hover:bg-gov-primaryDark focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              <Check className="h-4 w-4" />
              Publish survey
            </button>
          </div>
        }
      />

      {published ? (
        <div className="rounded-lg border border-gov-green bg-green-50 px-4 py-3 text-sm font-medium text-gov-green">
          Survey published. Collection link: /collect/{seedData.survey.id}
        </div>
      ) : null}

      {draftNote ? (
        <div className="rounded-lg border border-gov-teal bg-green-50 px-4 py-3 text-sm font-medium text-gov-teal">
          {draftNote}
        </div>
      ) : null}

      {promptOpen ? (
        <Card>
          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Describe the survey you need</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={3}
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
            />
          </label>
          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500">Draft generated - review before publishing.</p>
            <button
              type="button"
              onClick={() => draftMutation.mutate()}
              className="inline-flex items-center gap-2 rounded-lg bg-gov-teal px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-gov-primary"
            >
              <FilePlus2 className="h-4 w-4" />
              {draftMutation.isPending ? 'Generating...' : 'Generate draft'}
            </button>
          </div>
        </Card>
      ) : null}

      {activeTab === 'bank' ? <QuestionBank rows={questionBankRows} onAdd={addFromBank} /> : null}
      {activeTab === 'codes' ? <CodeLibrary rows={codeRows} /> : null}

      <div className={cn('grid gap-4 xl:grid-cols-[18rem_1fr_22rem]', activeTab !== 'builder' && 'xl:grid-cols-[1fr]')}>
        {activeTab === 'builder' ? (
          <>
            <Card className="space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-gov-primary">Palette</h2>
                <p className="text-xs text-slate-500">Add questions or reuse official bank items.</p>
              </div>
              <div className="grid gap-2">
                {(['choice', 'multi', 'number', 'text', 'date'] as SurveyQuestion['type'][]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => addQuestion(type)}
                    className="inline-flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-gov-teal"
                  >
                    <span className="capitalize">{type === 'multi' ? 'Multi select' : type}</span>
                    <Plus className="h-4 w-4" />
                  </button>
                ))}
              </div>
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase text-slate-500">From question bank</h3>
                {questionBankRows.slice(0, 4).map((question) => (
                  <button
                    key={question.id}
                    type="button"
                    onClick={() => addFromBank(question)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-gov-teal"
                  >
                    {getQuestionText(question, language)}
                  </button>
                ))}
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="min-w-0 flex-1">
                  <span className="text-xs font-semibold uppercase text-slate-500">Survey title</span>
                  <input
                    value={surveyTitle}
                    onChange={(event) => setSurveyTitle(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-lg font-semibold text-gov-primary focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
                  />
                </label>
                <StatusChip status="pass" label={`${questions.length} questions`} reason="The draft includes all ordered visible questions plus adaptive branches." />
              </div>

              <div className="space-y-3">
                {previewQuestions.map((question) => (
                  <button
                    key={question.id}
                    type="button"
                    onClick={() => setSelectedId(question.id)}
                    className={cn(
                      'w-full rounded-lg border p-4 text-left focus:outline-none focus:ring-2 focus:ring-gov-teal',
                      selectedId === question.id ? 'border-gov-primary bg-indigo-50' : 'border-slate-200 bg-white hover:bg-slate-50'
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold text-gov-teal">{question.display} · {question.type}</p>
                        <h3 className="mt-1 font-semibold text-slate-900">{question.text}</h3>
                      </div>
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                        Show if logic ready
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {question.rules?.range ? <StatusChip status="pass" label={`Range ${question.rules.range[0]}-${question.rules.range[1]}`} reason="Range validation prevents invalid numeric responses." /> : null}
                      {question.rules?.crossField ? <StatusChip status="warn" label="Cross-field rule" reason="If occupation is Unemployed, income above the configured max raises a reasoned flag." /> : null}
                      {question.codeType ? <StatusChip status="pass" label={`Auto-code ${question.codeType}`} reason={`Responses are mapped to ${question.codeType} when synonyms match the code library.`} /> : null}
                    </div>
                  </button>
                ))}
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-gov-primary" />
                <h2 className="text-sm font-semibold text-gov-primary">Properties</h2>
              </div>
              {selectedQuestion ? (
                <>
                  <div className="flex gap-2">
                    {languageTabs.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => useAppStore.getState().setLanguage(item)}
                        className={cn(
                          'rounded-full border px-3 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-gov-teal',
                          language === item ? 'border-gov-primary bg-gov-primary text-white' : 'border-slate-200 text-slate-600'
                        )}
                      >
                        {item.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Question label</span>
                    <textarea
                      value={getQuestionText(selectedQuestion, language)}
                      onChange={(event) => updateLabel(language, event.target.value)}
                      rows={3}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Auto-code as</span>
                    <select
                      value={selectedQuestion.codeType || ''}
                      onChange={(event) => updateSelected((question) => ({ ...question, codeType: event.target.value || null }))}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
                    >
                      <option value="">None</option>
                      <option value="NCO">NCO</option>
                      <option value="NIC">NIC</option>
                      <option value="ISIC">ISIC</option>
                    </select>
                  </label>
                  {selectedQuestion.type === 'number' ? (
                    <div className="grid grid-cols-2 gap-2">
                      <label className="block">
                        <span className="text-sm font-medium text-slate-700">Min</span>
                        <input
                          type="number"
                          value={selectedQuestion.rules?.range?.[0] ?? 0}
                          onChange={(event) =>
                            updateSelected((question) => ({
                              ...question,
                              rules: { ...(question.rules || {}), range: [Number(event.target.value), question.rules?.range?.[1] ?? 100] }
                            }))
                          }
                          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                      </label>
                      <label className="block">
                        <span className="text-sm font-medium text-slate-700">Max</span>
                        <input
                          type="number"
                          value={selectedQuestion.rules?.range?.[1] ?? 100}
                          onChange={(event) =>
                            updateSelected((question) => ({
                              ...question,
                              rules: { ...(question.rules || {}), range: [question.rules?.range?.[0] ?? 0, Number(event.target.value)] }
                            }))
                          }
                          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                      </label>
                    </div>
                  ) : null}
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-800">Rule reason text</span>
                      <ReasonPopover reason="Every rule emits a plain-language reason into the validation queue and collection Intelligence Panel." />
                    </div>
                    <p className="mt-2">If validation fails, SATARK shows the exact rule and reason to supervisors.</p>
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-500">Select a question to edit.</p>
              )}
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}

function QuestionBank({ rows, onAdd }: { rows: SurveyQuestion[]; onAdd: (question: SurveyQuestion) => void }) {
  const language = useAppStore((state) => state.language);
  return (
    <Card>
      <SectionHeader title="Question bank" eyebrow="Reusable official questions" />
      <DataTable
        rows={rows}
        rowKey={(row) => row.id}
        columns={[
          { key: 'question', header: 'Question', render: (row) => getQuestionText(row, language), sortValue: (row) => getQuestionText(row, language) },
          { key: 'type', header: 'Type', render: (row) => row.type, sortValue: (row) => row.type },
          { key: 'code', header: 'Code', render: (row) => row.codeType || 'None' },
          {
            key: 'languages',
            header: 'Languages',
            render: (row) => Object.keys(row.q || {}).join(', ').toUpperCase()
          },
          {
            key: 'add',
            header: 'Action',
            render: (row) => (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onAdd(row);
                }}
                className="rounded-lg bg-gov-primary px-3 py-1 text-xs font-semibold text-white"
              >
                Add to survey
              </button>
            )
          }
        ]}
      />
    </Card>
  );
}

function CodeLibrary({ rows }: { rows: typeof seedData.codes }) {
  return (
    <Card>
      <SectionHeader title="Code library" eyebrow="NCO / NIC semantic coding" />
      <DataTable
        rows={rows}
        rowKey={(row) => `${row.type}-${row.code}`}
        columns={[
          { key: 'code', header: 'Code', render: (row) => <span className="font-semibold text-gov-primary">{row.code}</span>, sortValue: (row) => row.code },
          { key: 'type', header: 'Type', render: (row) => row.type, sortValue: (row) => row.type },
          { key: 'label', header: 'Label', render: (row) => row.label, sortValue: (row) => row.label },
          { key: 'source', header: 'Source', render: (row) => row.externalSource || 'Local' },
          {
            key: 'reason',
            header: 'Reason',
            render: (row) => <ReasonPopover reason={`Synonyms such as ${row.synonyms.slice(0, 2).join(', ')} map raw text to ${row.type} ${row.code}.`}>why</ReasonPopover>
          }
        ]}
      />
    </Card>
  );
}
