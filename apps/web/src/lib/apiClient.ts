import { seedData } from '../data/seed';
import { useAppStore } from '../store/appStore';
import type { AnalyticsSnapshot, ApiResponse, CodeRecord, Enumerator, LiveFlag, Survey, User } from '../types';
import { evaluateIntelligence, findCodeSuggestion } from './intelligence';
import { getQueuedCount, queueRequest, syncQueue } from './offlineQueue';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function request<T>(path: string, options: RequestInit = {}, fallback: () => T | Promise<T>): Promise<ApiResponse<T>> {
  const offline = useAppStore.getState().simulatedOffline || (typeof navigator !== 'undefined' && !navigator.onLine);
  if (offline) {
    return { data: await fallback(), source: 'seed' };
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return { data: (await response.json()) as T, source: 'api' };
  } catch {
    return { data: await fallback(), source: 'seed' };
  }
}

export async function login(username: string, password: string) {
  return request<{ user: Omit<User, 'password'>; token: string }>(
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ username, password })
    },
    () => {
      const user = seedData.users.find((item) => item.username === username && item.password === password);
      if (!user) throw new Error('Invalid credentials');
      return {
        user: { username: user.username, role: user.role, name: user.name },
        token: `seed-${user.username}`
      };
    }
  );
}

export async function getSurveys() {
  return request<{ surveys: Survey[] }>('/surveys', {}, () => ({ surveys: [seedData.survey] }));
}

export async function generateSurvey(prompt: string) {
  return request<{ survey: Survey; generated?: Record<string, unknown>; note: string }>(
    '/surveys/generate',
    {
      method: 'POST',
      body: JSON.stringify({ prompt })
    },
    () => ({
      survey: seedData.survey,
      note: 'Draft generated from seed intelligence - review before publishing'
    })
  );
}

export async function getQuestionBank() {
  return request<{ questions: Survey['nodes'] }>('/question-bank', {}, () => ({
    questions: seedData.survey.nodes.filter((node) => node.type !== 'adaptive')
  }));
}

export async function getCodes() {
  return request<{ codes: CodeRecord[] }>('/codes', {}, () => ({ codes: seedData.codes }));
}

export async function getEnumerators() {
  return request<{ enumerators: Enumerator[] }>('/enumerators', {}, () => ({
    enumerators: useAppStore.getState().enumerators
  }));
}

export async function getEnumerator(id: string) {
  return request<{ enumerator: Enumerator }>(`/enumerators/${id}`, {}, () => {
    const enumerator = useAppStore.getState().enumerators.find((item) => item.id === id) || seedData.enumerators[0];
    return { enumerator };
  });
}

export async function getAnalytics() {
  return request<AnalyticsSnapshot>('/analytics', {}, buildSeedAnalytics);
}

export async function getFlaggedResponses() {
  return request<{ responses: LiveFlag[] }>('/responses?status=flagged', {}, () => ({
    responses: useAppStore.getState().liveFlags
  }));
}

export async function submitConsent(payload: Record<string, unknown>) {
  return request<{ ok: boolean; consentId: string }>(
    '/consent',
    { method: 'POST', body: JSON.stringify(payload) },
    () => ({ ok: true, consentId: `consent-${Date.now()}` })
  );
}

export async function prepopulate(householdId: string) {
  return request<{ household: (typeof seedData.households)[number] | null }>(
    '/prepopulate',
    { method: 'POST', body: JSON.stringify({ householdId }) },
    () => ({ household: seedData.households.find((item) => item.id === householdId) || null })
  );
}

export async function startIntelligenceSession(payload: Record<string, unknown>) {
  return request<{ sessionId: string }>(
    '/intelligence/sessions',
    { method: 'POST', body: JSON.stringify(payload) },
    () => ({ sessionId: `session-${Date.now()}` })
  );
}

export async function submitAnswer(payload: {
  answers: Record<string, string>;
  activeQuestionId?: string;
  persona: 'genuine' | 'suspicious';
  speedMode: 'normal' | 'too-fast';
  elapsedSeconds: number;
}) {
  return request('/intelligence/answer', { method: 'POST', body: JSON.stringify(payload) }, () => evaluateIntelligence(payload));
}

export async function submitCollectionResponse(payload: Record<string, unknown>) {
  const offline = useAppStore.getState().simulatedOffline || (typeof navigator !== 'undefined' && !navigator.onLine);
  if (offline) {
    const count = await queueRequest('/responses', 'POST', payload);
    useAppStore.getState().setQueuedCount(count);
    return { data: { queued: true, responseId: `queued-${Date.now()}` }, source: 'seed' as const };
  }

  try {
    const response = await fetch(`${API_BASE}/responses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Response submit failed');
    return { data: await response.json(), source: 'api' as const };
  } catch {
    const count = await queueRequest('/responses', 'POST', payload);
    useAppStore.getState().setQueuedCount(count);
    return { data: { queued: true, responseId: `queued-${Date.now()}` }, source: 'seed' as const };
  }
}

export async function submitCoding(rawResponse: string) {
  return request<{ suggestion: ReturnType<typeof findCodeSuggestion> }>(
    '/coding',
    { method: 'POST', body: JSON.stringify({ rawResponse }) },
    () => ({ suggestion: findCodeSuggestion(rawResponse) })
  );
}

export async function reviewCoding(payload: Record<string, unknown>) {
  return request<{ ok: boolean }>('/coding/review', { method: 'POST', body: JSON.stringify(payload) }, () => ({ ok: true }));
}

export async function postAction(payload: Record<string, unknown>) {
  return request<{ ok: boolean }>('/actions', { method: 'POST', body: JSON.stringify(payload) }, () => ({ ok: true }));
}

export async function exportData(format: 'csv' | 'pdf') {
  return request<{ fileName: string; content: string }>(
    '/export',
    { method: 'POST', body: JSON.stringify({ format }) },
    () => ({
      fileName: `satark-export.${format}`,
      content: 'survey,responses,validated,error_rate\nPLFS 2025-26,1000,90,10'
    })
  );
}

export async function refreshQueueCount() {
  const count = await getQueuedCount();
  useAppStore.getState().setQueuedCount(count);
  return count;
}

export async function syncOfflineQueue() {
  if (useAppStore.getState().simulatedOffline || !navigator.onLine) return refreshQueueCount();
  const count = await syncQueue(API_BASE);
  useAppStore.getState().setQueuedCount(count);
  return count;
}

function buildSeedAnalytics(): AnalyticsSnapshot {
  const enumerators = useAppStore.getState().enumerators;
  return {
    responsesToday: 186,
    flagged: useAppStore.getState().liveFlags.length + 13,
    averageConfidence: 86.4,
    activeEnumerators: enumerators.length,
    totalResponses: 1000,
    validatedRate: 90,
    errorRate: 10,
    ruralUrban: [33.4, 66.6],
    genderRatio: { male: 334, female: 333 },
    confidenceScore: 86.4,
    stateValidation: [
      { state: 'Uttar Pradesh', rate: 89.5 },
      { state: 'Maharashtra', rate: 88.8 },
      { state: 'Bihar', rate: 75.8 },
      { state: 'West Bengal', rate: 79.2 },
      { state: 'Madhya Pradesh', rate: 76.9 },
      { state: 'Tamil Nadu', rate: 91.4 }
    ],
    enumeratorRanking: [
      ...enumerators.map((enumerator, index) => ({
        ...enumerator,
        responses: enumerator.completed * 9 + index * 11,
        errorRate: enumerator.trustLevel === 'Red' ? 14.1 : 3.3 + index * 2.5,
        flaggedRate: enumerator.trustLevel === 'Red' ? 18.4 : 4.1 + index
      })),
      { ...seedData.enumerators[0], id: 'ENUM004', responses: 81, errorRate: 3.3, flaggedRate: 7 },
      { ...seedData.enumerators[0], id: 'ENUM008', responses: 116, errorRate: 3.3, flaggedRate: 4.1 },
      { ...seedData.enumerators[0], id: 'ENUM006', responses: 181, errorRate: 5.8, flaggedRate: 7 },
      { ...seedData.enumerators[0], id: 'ENUM001', responses: 173, errorRate: 5.9, flaggedRate: 0.8 }
    ],
    responseTrend: [
      { label: 'Mon', responses: 120, flagged: 8 },
      { label: 'Tue', responses: 148, flagged: 11 },
      { label: 'Wed', responses: 171, flagged: 16 },
      { label: 'Thu', responses: 154, flagged: 13 },
      { label: 'Fri', responses: 186, flagged: 15 },
      { label: 'Sat', responses: 132, flagged: 9 }
    ],
    sectorDistribution: [
      { sector: 'Labour', value: 38 },
      { sector: 'Health', value: 22 },
      { sector: 'Agriculture', value: 18 },
      { sector: 'Education', value: 12 },
      { sector: 'Enterprise', value: 10 }
    ],
    confidenceDistribution: [
      { bucket: '0-50', count: 32 },
      { bucket: '51-70', count: 91 },
      { bucket: '71-85', count: 240 },
      { bucket: '86-95', count: 421 },
      { bucket: '96-100', count: 216 }
    ]
  };
}
