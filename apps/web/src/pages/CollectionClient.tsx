import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mic, Send, ShieldCheck } from 'lucide-react';
import { Card, IntelligencePanel, ReasonPopover, SectionHeader, StatusChip, TrustBadge } from '../components/ui';
import { answerCollectionSession, completeCollectionSession, getAssignments, getSurvey, startCollectionSession, submitConsent } from '../lib/apiClient';
import { cn } from '../lib/format';
import { getQuestionText, initialIntelligence } from '../lib/intelligence';
import { useAppStore } from '../store/appStore';
import type { Assignment, CollectionSessionState, IntelligenceResult, Language, SurveyQuestion } from '../types';

type ClientStep = 'language' | 'consent' | 'survey' | 'done';

export function CollectionClient() {
  const { t } = useTranslation();
  const params = useParams();
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const requestedSurveyId = params.surveyId || 'latest';
  const useLatestAssignment = requestedSurveyId === 'latest';
  const [step, setStep] = useState<ClientStep>('language');
  const [session, setSession] = useState<CollectionSessionState | null>(null);
  const [draftValue, setDraftValue] = useState('');
  const [intelligence, setIntelligence] = useState<IntelligenceResult>(initialIntelligence);
  const [submittedMessage, setSubmittedMessage] = useState('');
  const questionStartedAt = useRef(Date.now());

  const assignmentQuery = useQuery({
    queryKey: ['collection-assignment', requestedSurveyId],
    queryFn: () => getAssignments({ surveyId: useLatestAssignment ? undefined : requestedSurveyId, status: 'assigned' })
  });
  const assignment = assignmentQuery.data?.data.assignments[0] || null;
  const activeSurveyId = assignment?.surveyId || (useLatestAssignment ? undefined : requestedSurveyId);
  const surveyQuery = useQuery({
    queryKey: ['survey', activeSurveyId, 'collection'],
    queryFn: () => getSurvey(activeSurveyId as string),
    enabled: Boolean(activeSurveyId)
  });
  const survey = session?.survey || surveyQuery.data?.data.survey || null;
  const household = session?.household || (assignment?.household && assignment.householdId ? { id: assignment.householdId, prepop: assignment.household } : null);
  const enumerator = session?.enumerator || null;
  const question = session?.currentQuestion || null;
  const answeredCount = Object.keys(session?.answers || {}).length;
  const progress = session?.visibleQueue?.length ? Math.min(100, Math.round((answeredCount / session.visibleQueue.length) * 100)) : 0;

  const startMutation = useMutation({
    mutationFn: (payload: { assignment: Assignment; language: Language }) =>
      startCollectionSession({ assignmentId: payload.assignment.id, surveyId: payload.assignment.surveyId, language: payload.language }),
    onSuccess: ({ data }) => {
      setSession(data);
      setIntelligence(data.intelligence || initialIntelligence);
      setStep('survey');
    }
  });

  const answerMutation = useMutation({
    mutationFn: (payload: { questionId: string; value: string; elapsedSeconds: number }) => {
      if (!session?.sessionId) throw new Error('Collection session has not started');
      return answerCollectionSession(session.sessionId, payload);
    },
    onSuccess: async ({ data }) => {
      setSession(data);
      setIntelligence(data.intelligence || initialIntelligence);
      if (data.complete) {
        const completed = await completeCollectionSession(data.sessionId);
        setIntelligence({ ...completed.data.intelligence, stored: true });
        setSubmittedMessage(`Response stored successfully. Trust ${completed.data.trustLevel}, confidence ${completed.data.qualityScore}.`);
        setStep('done');
      }
    }
  });

  useEffect(() => {
    questionStartedAt.current = Date.now();
    setDraftValue(question ? currentDefault(question, session, household) : '');
  }, [question?.id, session?.sessionId]);

  async function chooseLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    setStep('consent');
  }

  async function acceptConsent() {
    if (!assignment) return;
    await submitConsent({
      surveyId: assignment.surveyId,
      householdId: assignment.householdId,
      enumeratorId: assignment.enumeratorId,
      language,
      timestamp: new Date().toISOString()
    });
    startMutation.mutate({ assignment, language });
  }

  async function answerCurrent(value: string) {
    if (!question || !session) return;
    const elapsedSeconds = Math.max(1, Math.round((Date.now() - questionStartedAt.current) / 1000));
    answerMutation.mutate({ questionId: question.id, value, elapsedSeconds });
  }

  function resetFlow() {
    setStep('language');
    setSession(null);
    setDraftValue('');
    setIntelligence(initialIntelligence);
    setSubmittedMessage('');
  }

  if (assignmentQuery.isLoading || surveyQuery.isLoading) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading assigned collection context...</div>;
  }

  if (assignmentQuery.error || surveyQuery.error || !assignment || !survey || !household) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-gov-red">
        Could not load a persisted assignment, household, and survey for this collection flow. Publish a survey or create an assignment in FOD first.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title={survey.title[language] || survey.title.en}
        eyebrow="Collection client"
        actions={
          <div className="flex flex-wrap gap-2">
            {enumerator ? <TrustBadge score={enumerator.trustScore} level={enumerator.trustLevel} reason="Enumerator trust is updated only after persisted backend verdicts." /> : null}
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
              {assignment.enumeratorName} - {assignment.householdId}
            </span>
          </div>
        }
      />

      {step === 'language' ? (
        <Card className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold text-gov-primary">Choose language</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              { label: 'English', value: 'en' as Language },
              { label: 'Hindi', value: 'hi' as Language },
              { label: 'Tamil', value: 'ta' as Language }
            ].map((item) => (
              <button
                type="button"
                key={item.value}
                onClick={() => chooseLanguage(item.value)}
                className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-lg font-semibold text-gov-primary hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-gov-teal"
              >
                {item.label}
              </button>
            ))}
          </div>
        </Card>
      ) : null}

      {step === 'consent' ? (
        <Card className="mx-auto max-w-3xl space-y-4">
          <div className="flex items-start gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-gov-primary text-white">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gov-primary">{t('consentTitle')}</h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                This survey collects household data for official statistics. Your data is used only for this purpose and stored securely.
              </p>
            </div>
          </div>
          <ul className="grid gap-2 text-sm text-slate-700">
            <li className="rounded-lg bg-slate-50 p-3">What is collected: consent, household profile, answers, and survey paradata.</li>
            <li className="rounded-lg bg-slate-50 p-3">How it is used: validation, official statistics production, and quality monitoring.</li>
            <li className="rounded-lg bg-slate-50 p-3">Your rights: decline, pause, correct pre-filled data, and ask for purpose clarification.</li>
          </ul>
          {startMutation.error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-gov-red">{(startMutation.error as Error).message}</p> : null}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={acceptConsent}
              disabled={startMutation.isPending}
              className="rounded-lg bg-gov-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              {startMutation.isPending ? 'Starting...' : t('consentAccept')}
            </button>
            <button type="button" onClick={() => setStep('language')} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-gov-teal">
              {t('consentDecline')}
            </button>
          </div>
        </Card>
      ) : null}

      {step === 'survey' && question ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_28rem]">
          <Card className="space-y-5">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-gov-teal transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-gov-primary text-xs font-semibold text-white">S</span>
                <p className="rounded-lg bg-white px-4 py-3 text-sm font-medium text-slate-900 shadow-card">
                  {getQuestionText(question, language)}
                </p>
              </div>
              {question.prepop ? <StatusChip status="pass" label="From household record" reason={`This value is pre-filled from household ${household.id} and can be corrected.`} /> : null}
            </div>

            <AnswerInput question={question} value={draftValue} onChange={setDraftValue} onSubmit={answerCurrent} disabled={answerMutation.isPending} />
            {answerMutation.error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-gov-red">{(answerMutation.error as Error).message}</p> : null}

            {intelligence.suggestion ? (
              <div className="rounded-lg border border-gov-teal bg-green-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gov-teal">
                      {intelligence.suggestion.type} {intelligence.suggestion.code} - {intelligence.suggestion.confidence}% - {intelligence.suggestion.source}
                    </p>
                    <p className="mt-1 text-sm text-slate-700">{intelligence.suggestion.label}</p>
                  </div>
                  <ReasonPopover reason={intelligence.suggestion.reason}>reason</ReasonPopover>
                </div>
              </div>
            ) : null}
          </Card>

          <IntelligencePanel result={intelligence} />
        </div>
      ) : null}

      {step === 'done' ? (
        <div className="grid gap-4 xl:grid-cols-[1fr_28rem]">
          <Card className="space-y-4">
            <h2 className="text-xl font-semibold text-gov-primary">{submittedMessage}</h2>
            <p className="text-sm text-slate-600">The final stored verdict is the same backend verdict returned during collection.</p>
            <div className="flex flex-wrap gap-2">
              {intelligence.layers.map((layer) => (
                <StatusChip key={layer.layer} status={layer.status} label={layer.layer} reason={layer.reason} />
              ))}
            </div>
            <button
              type="button"
              onClick={resetFlow}
              className="rounded-lg bg-gov-primary px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-gov-teal"
            >
              Start another response
            </button>
          </Card>
          <IntelligencePanel result={intelligence} />
        </div>
      ) : null}
    </div>
  );
}

function currentDefault(question: SurveyQuestion, session: CollectionSessionState | null, household: { prepop: { name?: string } } | null) {
  const existing = session?.answers?.[question.id];
  if (existing !== undefined) return existing;
  return question.prepop ? household?.prepop.name || '' : '';
}

function AnswerInput({
  question,
  value,
  onChange,
  onSubmit,
  disabled = false
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}) {
  const isChoice = question.type === 'choice' && question.options?.length;
  return (
    <div className="space-y-3">
      {isChoice ? (
        <div className="flex flex-wrap gap-2">
          {question.options?.map((option) => (
            <button
              type="button"
              key={option}
              disabled={disabled}
              onClick={() => onChange(option)}
              className={cn(
                'rounded-full border px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gov-teal',
                value === option ? 'border-gov-primary bg-gov-primary text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              )}
            >
              {option}
            </button>
          ))}
        </div>
      ) : (
        <input
          type={question.type === 'number' ? 'number' : 'text'}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-4 py-3 text-base disabled:bg-slate-100 focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
        />
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSubmit(value)}
          className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gov-teal"
        >
          <Send className="h-4 w-4" />
          {disabled ? 'Saving' : 'Next'}
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(value || 'voice input simulated')}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gov-teal"
        >
          <Mic className="h-4 w-4" />
          Voice
        </button>
      </div>
    </div>
  );
}
