import { useAppStore } from '../store/appStore';
import type {
  AnalyticsSnapshot,
  ApiResponse,
  Assignment,
  CodeRecord,
  CodeSuggestion,
  CodingReviewItem,
  Enumerator,
  Household,
  IntelligenceResult,
  LiveFlag,
  ResponseDetail,
  Survey,
  User
} from '../types';
import { getQueuedCount, queueRequest, syncQueue } from './offlineQueue';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

function authHeaders(): Record<string, string> {
  const token = useAppStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function isOfflineMode() {
  return useAppStore.getState().simulatedOffline || (typeof navigator !== 'undefined' && !navigator.onLine);
}

function unavailableMessage(path: string) {
  return `SATARK API is unavailable for ${path}. Start the local backend stack instead of using bundled fallback data.`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  if (isOfflineMode()) {
    throw new Error(unavailableMessage(path));
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      detail = await response.text().catch(() => '');
    }
    throw new Error(`SATARK API ${response.status}${detail ? `: ${detail}` : ''}`);
  }

  return { data: (await response.json()) as T, source: 'api' };
}

export async function login(username: string, password: string) {
  return request<{ user: Omit<User, 'password'>; token: string; scopes?: string[] }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
}

export async function getSurveys() {
  return request<{ surveys: Survey[] }>('/surveys');
}

export async function generateSurvey(prompt: string) {
  return request<{ survey: Survey; generated?: Record<string, unknown>; note: string }>('/surveys/generate', {
    method: 'POST',
    body: JSON.stringify({ prompt })
  });
}

export async function getQuestionBank() {
  return request<{ questions: Survey['nodes'] }>('/question-bank');
}

export async function getCodes() {
  return request<{ codes: CodeRecord[] }>('/codes');
}

export async function getEnumerators() {
  return request<{ enumerators: Enumerator[] }>('/enumerators');
}

export async function getEnumerator(id: string) {
  return request<{ enumerator: Enumerator }>(`/enumerators/${id}`);
}

export async function getAnalytics() {
  return request<AnalyticsSnapshot>('/dashboard/metrics');
}

export async function getFlaggedResponses() {
  return request<{ responses: LiveFlag[] }>('/dashboard/flags');
}

export async function getResponseDetail(responseId: string) {
  return request<ResponseDetail>(`/responses/${responseId}`);
}

export async function reviewResponse(responseId: string, payload: { action: 'approve' | 're_interview' | 'escalate'; reason?: string }) {
  return request<{ ok: boolean; responseId: string; status: string; assignmentId?: string | null }>(`/responses/${responseId}/review`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function getHouseholds(region?: string) {
  const qs = region ? `?region=${encodeURIComponent(region)}` : '';
  return request<{ households: Household[] }>(`/households${qs}`);
}

export async function getAssignments(params: { surveyId?: string; enumeratorId?: string; status?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.surveyId) qs.set('survey_id', params.surveyId);
  if (params.enumeratorId) qs.set('enumerator_id', params.enumeratorId);
  if (params.status) qs.set('status', params.status);
  const suffix = qs.toString() ? `?${qs}` : '';
  return request<{ assignments: Assignment[] }>(`/assignments${suffix}`);
}

export async function createAssignment(payload: { surveyId: string; enumeratorId?: string; enumeratorIds?: string[]; householdId?: string; householdIds?: string[] }) {
  return request<{ assignments: Assignment[] }>('/assignments', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateAssignment(assignmentId: string, payload: { status: string; reason?: string }) {
  return request<{ assignment: Assignment }>(`/assignments/${assignmentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function submitConsent(payload: Record<string, unknown>) {
  return request<{ ok: boolean; consentId: string }>('/consent', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function prepopulate(householdId: string) {
  return request<{ household: Household | null }>('/prepopulate', {
    method: 'POST',
    body: JSON.stringify({ householdId })
  });
}

export async function startIntelligenceSession(payload: Record<string, unknown>) {
  return request<{ sessionId: string }>('/intelligence/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function submitAnswer(payload: {
  answers: Record<string, string>;
  activeQuestionId?: string;
  persona: 'genuine' | 'suspicious';
  speedMode: 'normal' | 'too-fast';
  elapsedSeconds: number;
}) {
  return request<IntelligenceResult>('/intelligence/answer', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function submitCollectionResponse(payload: Record<string, unknown>) {
  if (isOfflineMode()) {
    const count = await queueRequest('/responses', 'POST', payload);
    useAppStore.getState().setQueuedCount(count);
    return { data: { queued: true, responseId: `queued-${Date.now()}` }, source: 'queued' as const };
  }

  const response = await fetch(`${API_BASE}/responses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`SATARK API ${response.status}: response submit failed`);
  }

  return { data: await response.json(), source: 'api' as const };
}

export async function submitCoding(rawResponse: string) {
  return request<{ suggestion: CodeSuggestion | null; is_verdict: false; needs_review: true }>('/coding', {
    method: 'POST',
    body: JSON.stringify({ rawResponse })
  });
}

export async function reviewCoding(payload: Record<string, unknown>) {
  return request<{ ok: boolean }>('/coding/review', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function getCodingReviewQueue(needsReview = true) {
  return request<{ items: CodingReviewItem[] }>(`/coding-review?needs_review=${needsReview ? 'true' : 'false'}`);
}

export async function postAction(payload: Record<string, unknown>) {
  return request<{ ok: boolean }>('/actions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function getSurvey(surveyId: string) {
  return request<{ survey: Survey & { status?: string; version?: number } }>(`/surveys/${surveyId}`);
}

export async function createSurvey(
  payload: Partial<Survey> & {
    id?: string;
    title?: Record<string, string>;
    domain?: string;
    question_graph?: Record<string, unknown>;
  }
) {
  return request<{ survey: Survey & { status?: string; version?: number } }>('/surveys', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function patchSurvey(surveyId: string, payload: Record<string, unknown>) {
  return request<{ survey: Survey & { status?: string; version?: number } }>(`/surveys/${surveyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function publishSurvey(surveyId: string) {
  return request<{ survey_id: string; status: string; version: number; published_at?: string; assignment?: Assignment; validationRulesCreated?: number }>(`/surveys/${surveyId}/publish`, {
    method: 'POST'
  });
}

export async function ragStatus() {
  return request<{ enabled: boolean; buckets: Record<string, { chroma_count?: number; memory_count?: number }> }>('/rag/status');
}

export async function ragQuery(payload: { bucket: string; question: string; k?: number }) {
  return request<{
    answer: string;
    sources: Array<{ id: string; text: string; score: number }>;
    confidence: number;
    is_verdict: false;
    needs_review: true;
  }>('/rag/query', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function ragIngest(
  file: File,
  bucket: string
): Promise<ApiResponse<{ source_id: string; bucket: string; chunk_count: number; sha256: string; byte_size: number; is_verdict: false }>> {
  if (isOfflineMode()) {
    throw new Error(unavailableMessage('/rag/ingest'));
  }

  const form = new FormData();
  form.append('file', file);
  form.append('bucket', bucket);
  const response = await fetch(`${API_BASE}/rag/ingest`, {
    method: 'POST',
    headers: { ...authHeaders() },
    body: form
  });
  if (!response.ok) {
    throw new Error(`SATARK API ${response.status}: RAG ingest failed`);
  }
  return { data: await response.json(), source: 'api' };
}

export async function getValidationRules(surveyId?: string) {
  const qs = surveyId ? `?survey_id=${encodeURIComponent(surveyId)}` : '';
  return request<{ rules: Array<{ id: string; survey_id: string; field: string; rule_type: string; params: Record<string, unknown>; severity: string; reason_template: string }> }>(
    `/validation-rules${qs}`
  );
}

export async function createValidationRule(payload: Record<string, unknown>) {
  return request<{ id: string }>('/validation-rules', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function deleteValidationRule(ruleId: string) {
  return request<{ ok: boolean }>(`/validation-rules/${ruleId}`, { method: 'DELETE' });
}

export async function getAdaptiveLogic(surveyId?: string) {
  const qs = surveyId ? `?survey_id=${encodeURIComponent(surveyId)}` : '';
  return request<{ rules: Array<{ id: string; survey_id: string; trigger: Record<string, unknown>; action: string; target: Record<string, unknown> }> }>(`/adaptive-logic${qs}`);
}

export async function createAdaptiveLogic(payload: Record<string, unknown>) {
  return request<{ id: string }>('/adaptive-logic', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function deleteAdaptiveLogic(ruleId: string) {
  return request<{ ok: boolean }>(`/adaptive-logic/${ruleId}`, { method: 'DELETE' });
}

export async function exportData(format: 'csv' | 'pdf') {
  return request<{ fileName: string; content: string }>('/export', {
    method: 'POST',
    body: JSON.stringify({ format })
  });
}

export async function refreshQueueCount() {
  const count = await getQueuedCount();
  useAppStore.getState().setQueuedCount(count);
  return count;
}

export async function syncOfflineQueue() {
  if (isOfflineMode()) return refreshQueueCount();
  const count = await syncQueue(API_BASE, authHeaders());
  useAppStore.getState().setQueuedCount(count);
  return count;
}
