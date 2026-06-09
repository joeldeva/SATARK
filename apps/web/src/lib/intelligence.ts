import { seedData } from '../data/seed';
import type { CodeSuggestion, IntelligenceResult, Language, SurveyQuestion, ValidationLayer } from '../types';
import { formatCurrency, trustLevelForScore } from './format';

interface EvaluateInput {
  answers: Record<string, string>;
  activeQuestionId?: string;
  persona: 'genuine' | 'suspicious';
  speedMode: 'normal' | 'too-fast';
  elapsedSeconds: number;
}

const passLayers: ValidationLayer[] = [
  { layer: 'Completeness', status: 'pass', reason: 'Required responses are present' },
  { layer: 'Range', status: 'pass', reason: 'Numeric answers are inside permitted ranges' },
  { layer: 'Cross-field', status: 'pass', reason: 'Occupation and income do not conflict' },
  { layer: 'Context', status: 'pass', reason: 'Values are within regional reference distribution' },
  { layer: 'Behaviour', status: 'pass', reason: 'Response speed is consistent with expected survey pace' }
];

export function getQuestionText(question: SurveyQuestion | { q?: Partial<Record<Language, string>> }, language: Language) {
  return question.q?.[language] || question.q?.en || 'Question';
}

export function getOrderedQuestions(occupation?: string, survey = seedData.survey) {
  const questions = survey.nodes.filter((node) => node.type !== 'adaptive');
  const branch = occupation ? survey.branches[occupation] : undefined;
  if (!branch) return questions;
  const branchQuestion: SurveyQuestion = {
    id: branch.id,
    type: branch.options ? 'choice' : 'text',
    options: branch.options,
    q: branch.q
  };
  const branchIndex = questions.findIndex((question) => question.id === 'income');
  return [...questions.slice(0, branchIndex), branchQuestion, ...questions.slice(branchIndex)];
}

export function findCodeSuggestion(rawValue: string): CodeSuggestion | undefined {
  const value = rawValue.trim().toLowerCase();
  if (!value) return undefined;

  for (const record of seedData.codes) {
    const matched = record.synonyms.find((synonym) => value.includes(synonym.toLowerCase()));
    if (matched || value.includes(record.label.toLowerCase())) {
      return {
        code: record.code,
        type: record.type,
        label: record.label,
        confidence: record.externalSource ? 93 : 96,
        source: record.externalSource ? 'MoSPI NIC' : 'Local',
        reason: `Matched synonym '${matched || record.label}' to ${record.type} ${record.code}`
      };
    }
  }

  return undefined;
}

export function evaluateIntelligence(input: EvaluateInput): IntelligenceResult {
  const income = Number(input.answers.income || 0);
  const occupation = input.answers.occupation;
  const tooFast = input.speedMode === 'too-fast' || input.elapsedSeconds <= 5;
  const unemployedHighIncome = occupation === 'Unemployed' && income > 50000;
  const outsideIncome = income > seedData.referenceDistributions.income.p95 || (income > 0 && income < seedData.referenceDistributions.income.p05);
  const suggestion = input.activeQuestionId === 'occupation' ? findCodeSuggestion(input.answers.occupation || '') : undefined;

  let layers = passLayers;
  let confidence = input.persona === 'genuine' ? 96 : 84;
  let reason = 'All validation layers are currently passing';

  if (unemployedHighIncome || tooFast || outsideIncome) {
    layers = [
      { layer: 'Completeness', status: 'pass', reason: 'Required responses are present' },
      { layer: 'Range', status: 'pass', reason: 'Numeric answers are inside field-level ranges' },
      unemployedHighIncome
        ? { layer: 'Cross-field', status: 'fail', reason: `Income ${formatCurrency(income)} contradicts status 'Unemployed'` }
        : { layer: 'Cross-field', status: 'pass', reason: 'Occupation and income do not conflict' },
      outsideIncome
        ? {
            layer: 'Context',
            status: 'warn',
            reason: `${formatCurrency(income)} outside regional range ${formatCurrency(seedData.referenceDistributions.income.p05)}-${formatCurrency(seedData.referenceDistributions.income.p95)}`
          }
        : { layer: 'Context', status: 'pass', reason: 'Income is inside regional reference range' },
      tooFast
        ? {
            layer: 'Behaviour',
            status: 'fail',
            reason: `Answered in ${Math.max(3, Math.round(input.elapsedSeconds))}s vs ~${seedData.referenceDistributions.responseTimeSeconds.median}s median`
          }
        : { layer: 'Behaviour', status: 'pass', reason: 'Response speed is consistent with expected survey pace' }
    ];
    confidence = unemployedHighIncome && tooFast ? 46 : outsideIncome ? 68 : 72;
    reason = unemployedHighIncome
      ? "Cross-field validation found income inconsistent with 'Unemployed'"
      : 'Context validation found an outlier that needs review';
  }

  const failed = layers.filter((layer) => layer.status === 'fail').length;
  const warned = layers.filter((layer) => layer.status === 'warn').length;
  const trustLevel = trustLevelForScore(confidence);

  return {
    confidence,
    trustLevel,
    decision: failed ? 'SIMPLIFY' : warned ? 'ASK' : 'ASK',
    nextQuestionId: undefined,
    reason,
    layers,
    scores: {
      engagement: tooFast ? 45 : 92,
      fatigue: tooFast ? 38 : 84,
      dropout: failed ? 44 : 90,
      quality: confidence
    },
    breakdown: {
      validation: Math.max(0, 100 - failed * 35 - warned * 12),
      fraud: tooFast ? 42 : 94,
      evidence: failed ? 58 : 90,
      behaviour: tooFast ? 34 : 91
    },
    suggestion,
    stored: false
  };
}

export const initialIntelligence: IntelligenceResult = {
  confidence: 90,
  trustLevel: 'Green',
  decision: 'ASK',
  reason: 'Waiting for the next response',
  layers: passLayers,
  scores: { engagement: 90, fatigue: 88, dropout: 91, quality: 90 },
  breakdown: { validation: 90, fraud: 90, evidence: 88, behaviour: 90 },
  stored: false
};
