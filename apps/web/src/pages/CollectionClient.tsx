import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mic, Send, ShieldCheck } from 'lucide-react';
import { Card, IntelligencePanel, ReasonPopover, SectionHeader, StatusChip, TrustBadge } from '../components/ui';
import { seedData } from '../data/seed';
import { getAssignments, getEnumerators, getSurvey, startIntelligenceSession, submitAnswer, submitCollectionResponse, submitConsent } from '../lib/apiClient';
import { cn, trustLevelForScore } from '../lib/format';
import { evaluateIntelligence, getOrderedQuestions, getQuestionText, initialIntelligence } from '../lib/intelligence';
import { useAppStore } from '../store/appStore';
import type { IntelligenceResult, Language, SurveyQuestion } from '../types';

type ClientStep = 'language' | 'consent' | 'survey' | 'done';

export function CollectionClient() {
  const { t } = useTranslation();
  const params = useParams();
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const addLiveFlag = useAppStore((state) => state.addLiveFlag);
  const updateEnumeratorTrust = useAppStore((state) => state.updateEnumeratorTrust);
  const requestedSurveyId = params.surveyId || 'latest';
  const useLatestAssignment = requestedSurveyId === 'latest';
  const enumeratorQuery = useQuery({ queryKey: ['enumerators', 'collection'], queryFn: getEnumerators });
  const enumerators = enumeratorQuery.data?.data.enumerators || [];
  const [step, setStep] = useState<ClientStep>('language');
  const [persona, setPersona] = useState<'genuine' | 'suspicious'>('genuine');
  const [speedMode, setSpeedMode] = useState<'normal' | 'too-fast'>('normal');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [draftValue, setDraftValue] = useState('');
  const [intelligence, setIntelligence] = useState<IntelligenceResult>(initialIntelligence);
  const [submittedMessage, setSubmittedMessage] = useState('');
  const questionStartedAt = useRef(Date.now());
  const flagCreated = useRef(false);

  const personaData = seedData.personas[persona];
  const assignmentQuery = useQuery({
    queryKey: ['collection-assignment', requestedSurveyId],
    queryFn: () => getAssignments({ surveyId: useLatestAssignment ? undefined : requestedSurveyId, status: 'assigned' })
  });
  const assignment = assignmentQuery.data?.data.assignments[0] || null;
  const activeSurveyId = assignment?.surveyId || (useLatestAssignment ? seedData.survey.id : requestedSurveyId);
  const surveyQuery = useQuery({ queryKey: ['survey', activeSurveyId, 'collection'], queryFn: () => getSurvey(activeSurveyId), enabled: Boolean(activeSurveyId) });
  const survey = surveyQuery.data?.data.survey || null;
  const household = assignment?.household && assignment.householdId ? { id: assignment.householdId, prepop: assignment.household } : null;
  const enumerator = enumerators.find((item) => item.id === assignment?.enumeratorId) || enumerators.find((item) => item.id === personaData.enumeratorId) || null;
  const orderedQuestions = useMemo(() => (survey ? getOrderedQuestions(answers.occupation, survey) : []), [answers.occupation, survey]);
  const question = orderedQuestions[currentIndex];
  const progress = orderedQuestions.length ? Math.round(((currentIndex + 1) / orderedQuestions.length) * 100) : 0;

  useEffect(() => {
    if (household?.prepop.name && !answers.name) {
      setAnswers((current) => ({ name: household.prepop.name, ...current }));
    }
  }, [answers.name, household?.prepop.name]);

  useEffect(() => {
    questionStartedAt.current = Date.now();
    setDraftValue(question ? answers[question.id] || personaData.answers[question.id] || (question.prepop ? household?.prepop.name || '' : '') : '');
  }, [answers, currentIndex, household?.prepop.name, personaData.answers, question]);

  useEffect(() => {
    if (persona === 'suspicious') setSpeedMode('too-fast');
  }, [persona]);

  async function chooseLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    setStep('consent');
  }

  async function acceptConsent() {
    await submitConsent({
      surveyId: activeSurveyId,
      householdId: household?.id,
      enumeratorId: enumerator?.id,
      language,
      timestamp: new Date().toISOString()
    });
    await startIntelligenceSession({
      surveyId: activeSurveyId,
      householdId: household?.id,
      enumeratorId: enumerator?.id,
      assignmentId: assignment?.id,
      language
    });
    setStep('survey');
  }

  async function answerCurrent(value: string) {
    if (!question || !enumerator || !survey) return;
    const elapsedSeconds =
      speedMode === 'too-fast'
        ? personaData.speedSeconds[Math.min(currentIndex, personaData.speedSeconds.length - 1)] || 4
        : Math.max(8, Math.round((Date.now() - questionStartedAt.current) / 1000));
    const nextAnswers = { ...answers, [question.id]: value };
    setAnswers(nextAnswers);

    const evaluated = evaluateIntelligence({
      answers: nextAnswers,
      activeQuestionId: question.id,
      persona,
      speedMode,
      elapsedSeconds
    });

    const response = await submitAnswer({
      answers: nextAnswers,
      activeQuestionId: question.id,
      persona,
      speedMode,
      elapsedSeconds
    });
    setIntelligence((response.data as IntelligenceResult) || evaluated);

    if (!flagCreated.current && evaluated.confidence <= 55) {
      flagCreated.current = true;
      const nextTrust = 36;
      const trustLevel = trustLevelForScore(nextTrust);
      updateEnumeratorTrust(enumerator.id, nextTrust, trustLevel);
      addLiveFlag({
        id: `flag-${Date.now()}`,
        enumeratorId: enumerator.id,
        enumeratorName: enumerator.name,
        survey: survey.title.en,
        reason: evaluated.layers.find((layer) => layer.status === 'fail')?.reason || evaluated.reason,
        trustScore: nextTrust,
        trustLevel,
        timestamp: new Date().toISOString()
      });
    }

    if (currentIndex < orderedQuestions.length - 1) {
      setCurrentIndex((index) => index + 1);
    } else {
      const storedResult = { ...evaluated, stored: true };
      setIntelligence(storedResult);
      const submitResult = await submitCollectionResponse({
        surveyId: activeSurveyId,
        householdId: household?.id,
        enumeratorId: enumerator.id,
        assignmentId: assignment?.id,
        answers: nextAnswers,
        prepopulated: household?.prepop || {},
        intelligence: storedResult,
        speedMode,
        elapsedSeconds,
        durationSeconds: personaData.speedSeconds.reduce((sum, item) => sum + item, 0),
        channel: 'collection-client',
        submittedAt: new Date().toISOString()
      });
      setSubmittedMessage(submitResult.data.queued ? 'Response queued for sync.' : 'Response stored successfully.');
      setStep('done');
    }
  }

  function currentDefault(questionItem: SurveyQuestion) {
    return answers[questionItem.id] || personaData.answers[questionItem.id] || (questionItem.prepop ? household?.prepop.name || '' : '');
  }

  if (!enumerator || !survey || assignmentQuery.isLoading || surveyQuery.isLoading) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading assigned collection context...</div>;
  }

  if (assignmentQuery.error || surveyQuery.error || !household) {
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
            <Segmented
              label="Persona"
              value={persona}
              options={[
                { label: 'Genuine', value: 'genuine' },
                { label: 'Suspicious', value: 'suspicious' }
              ]}
              onChange={(value) => {
                flagCreated.current = false;
                setPersona(value);
                setCurrentIndex(0);
                setAnswers({ name: household.prepop.name });
                setIntelligence(initialIntelligence);
              }}
            />
            <Segmented
              label="Speed"
              value={speedMode}
              options={[
                { label: 'Normal', value: 'normal' },
                { label: 'Too-fast', value: 'too-fast' }
              ]}
              onChange={setSpeedMode}
            />
            <TrustBadge score={enumerator.trustScore} level={enumerator.trustLevel} reason="Enumerator trust ticks down when a live quality flag is created." />
          </div>
        }
      />

      {step === 'language' ? (
        <Card className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold text-gov-primary">Choose language</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              { label: 'English', value: 'en' as Language },
              { label: 'हिन्दी', value: 'hi' as Language },
              { label: 'தமிழ்', value: 'ta' as Language }
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
                This survey collects household employment data for official statistics. Your data is used only for this purpose and stored securely.
              </p>
            </div>
          </div>
          <ul className="grid gap-2 text-sm text-slate-700">
            <li className="rounded-lg bg-slate-50 p-3">What is collected: consent, household profile, employment, income, and survey paradata.</li>
            <li className="rounded-lg bg-slate-50 p-3">How it is used: validation, official statistics production, and quality monitoring.</li>
            <li className="rounded-lg bg-slate-50 p-3">Your rights: decline, pause, correct pre-filled data, and ask for purpose clarification.</li>
          </ul>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={acceptConsent} className="rounded-lg bg-gov-primary px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-gov-teal">
              {t('consentAccept')}
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

              {question.prepop ? <StatusChip status="pass" label="From household record" reason="This value is pre-filled from household HH-TN-0042 and can be corrected." /> : null}
            </div>

            <AnswerInput question={question} value={draftValue || currentDefault(question)} onChange={setDraftValue} onSubmit={answerCurrent} />

            {intelligence.suggestion ? (
              <div className="rounded-lg border border-gov-teal bg-green-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gov-teal">
                      {intelligence.suggestion.type} {intelligence.suggestion.code} · {intelligence.suggestion.confidence}% · {intelligence.suggestion.source}
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
            <p className="text-sm text-slate-600">Response confidence settled at {intelligence.confidence}. Validation status is ready for supervisor review.</p>
            <div className="flex flex-wrap gap-2">
              {intelligence.layers.map((layer) => (
                <StatusChip key={layer.layer} status={layer.status} label={layer.layer} reason={layer.reason} />
              ))}
            </div>
            <button
              type="button"
              onClick={() => {
                setStep('language');
                setCurrentIndex(0);
                setAnswers({ name: household.prepop.name });
                setIntelligence(initialIntelligence);
                setSubmittedMessage('');
                flagCreated.current = false;
              }}
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

function Segmented<T extends string>({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: T;
  options: Array<{ label: string; value: T }>;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <span className="sr-only">{label}</span>
      <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            onClick={() => onChange(option.value)}
            className={cn(
              'rounded-md px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-gov-teal',
              value === option.value ? 'bg-gov-primary text-white' : 'text-slate-700 hover:bg-slate-50'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function AnswerInput({
  question,
  value,
  onChange,
  onSubmit
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
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
              onClick={() => onChange(option)}
              className={cn(
                'rounded-full border px-4 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-gov-teal',
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
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-4 py-3 text-base focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
        />
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onSubmit(value)}
          className="inline-flex items-center gap-2 rounded-lg bg-gov-primary px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-gov-teal"
        >
          <Send className="h-4 w-4" />
          Next
        </button>
        <button
          type="button"
          onClick={() => onChange(value || 'voice input simulated')}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-gov-teal"
        >
          <Mic className="h-4 w-4" />
          Voice
        </button>
      </div>
    </div>
  );
}
