// Thin client for the channel-agnostic collection loop + Enumerator Sandbox feed.
// Every channel posts answers to the SAME backend orchestrator; this client only
// serialises requests — it never scores.
import { apiWsUrl } from '../api';

const API_ORIGIN = ((import.meta as any).env?.VITE_API_URL || '').replace(/\/$/, '');
const V1 = `${API_ORIGIN}/api/v1`;

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('satark_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${V1}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`channels ${path} -> ${res.status}: ${await res.text().catch(() => '')}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${V1}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`channels ${path} -> ${res.status}`);
  return res.json();
}

export type Channel = 'whatsapp' | 'ivr' | 'avatar' | 'web';

export interface MethodResult {
  name: string;
  method?: string;
  status: string;
  reason: string;
  confidence?: number;
  flagged?: boolean;
}

export interface LastResult {
  confidence: number;
  risk_level: 'Green' | 'Amber' | 'Red';
  layers: MethodResult[];
  methods?: MethodResult[];
  flaggedBy?: string[];
}

export interface OutboundPayload {
  type: 'consent' | 'question' | 'clarification' | 'complete';
  channel: Channel;
  session_id: string;
  node_id: string | null;
  prompt_text: { en: string; hi?: string; ta?: string };
  input_kind: 'choice' | 'number' | 'text' | 'voice';
  options?: { value: string; label_i18n: Record<string, string> }[];
  adaptive?: { action: string; reason: string };
  last_result?: LastResult;
  events?: string[];
  speak_text?: string;
  tts_text?: string;
  expect?: string;
  result?: any;
}

export interface SandboxTurn {
  seq: number;
  session_id: string;
  channel: Channel;
  node_id: string;
  question: string;
  answer: unknown;
  result: {
    confidence: number;
    risk_level: string;
    layers: MethodResult[];
    methods?: MethodResult[];
    flaggedBy?: string[];
    reasons: string[];
    scores: Record<string, number>;
  };
  adaptive: { action?: string; reason?: string };
}

export const channels = {
  start: (survey_id: string, channel: Channel, respondent_ref: string, extra: Record<string, unknown> = {}) =>
    post<OutboundPayload>('/channels/session/start', { survey_id, channel, respondent_ref, ...extra }),

  answer: (channel: Channel, respondent_ref: string, raw_answer: string, meta: Record<string, unknown> = {}) =>
    post<OutboundPayload>('/channels/answer', { channel, respondent_ref, raw_answer, meta }),

  next: (channel: Channel, respondent_ref: string) =>
    get<OutboundPayload>(`/channels/next?channel=${channel}&respondent_ref=${encodeURIComponent(respondent_ref)}`),

  turns: (sessionId?: string, after = 0) =>
    get<{ turns: SandboxTurn[] }>(
      `/sandbox/turns?after=${after}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}`,
    ),

  sessions: () => get<{ sessions: any[]; backend: string }>('/sandbox/sessions'),
};

/**
 * Subscribe to the sandbox live stream over WS, with a 3s GET-polling fallback
 * when the WebSocket can't connect (no Redis / no tunnel).
 */
export function subscribeSandbox(onTurn: (turn: SandboxTurn) => void): () => void {
  const token = localStorage.getItem('satark_token') || '';
  let closed = false;
  let lastSeq = 0;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let ws: WebSocket | null = null;

  const startPolling = () => {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
      try {
        const { turns } = await channels.turns(undefined, lastSeq);
        for (const turn of turns) {
          lastSeq = Math.max(lastSeq, turn.seq);
          onTurn(turn);
        }
      } catch {
        /* keep polling */
      }
    }, 3000);
  };

  try {
    ws = new WebSocket(apiWsUrl('/v1/sandbox/live', token));
    ws.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.event === 'sandbox.turn') onTurn(payload as SandboxTurn);
      } catch {
        /* ignore */
      }
    };
    ws.onerror = () => startPolling();
    ws.onclose = () => { if (!closed) startPolling(); };
  } catch {
    startPolling();
  }

  return () => {
    closed = true;
    if (pollTimer) clearInterval(pollTimer);
    if (ws) ws.close();
  };
}
