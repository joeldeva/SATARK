import React, { useEffect, useRef, useState } from 'react';
import { channels, subscribeSandbox, Channel, OutboundPayload, SandboxTurn, MethodResult } from '../../../lib/channels-client';
import { ConfidenceGauge, TrustBadge } from '../../../components/TrustComponents';

function confColor(c: number): string {
  if (c >= 80) return 'bg-emerald-500';
  if (c >= 50) return 'bg-amber-500';
  return 'bg-rose-500';
}

/** Per-method confidence with proof — which method ran, its score, did it flag. */
const MethodConfidence: React.FC<{ methods: MethodResult[] }> = ({ methods }) => (
  <div className="space-y-2">
    {methods.map((m) => {
      const c = Math.round(m.confidence ?? (m.status === 'pass' ? 100 : m.status === 'warn' ? 55 : 10));
      return (
        <div key={m.name} className={`rounded-lg border p-2 ${m.flagged ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-white'}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700">{m.name}</span>
            <span className={`text-[10px] font-bold ${m.flagged ? 'text-rose-600' : 'text-emerald-600'}`}>
              {m.flagged ? `FLAGGED · ${c}%` : `${c}%`}
            </span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded mt-1 overflow-hidden">
            <div className={`h-full ${confColor(c)}`} style={{ width: `${c}%` }} />
          </div>
          <p className="text-[10px] text-slate-500 mt-1">{m.method}</p>
          <p className="text-[10px] text-slate-600 mt-0.5">{m.reason}</p>
        </div>
      );
    })}
  </div>
);

interface Props {
  lang?: string;
  isColorBlind?: boolean;
}

interface TranscriptLine {
  dir: 'out' | 'in';
  text: string;
  node?: string | null;
}

const CHANNELS: { id: Channel; label: string; emoji: string }[] = [
  { id: 'whatsapp', label: 'WhatsApp', emoji: '💬' },
  { id: 'ivr', label: 'IVR', emoji: '☎️' },
  { id: 'avatar', label: 'AI Avatar', emoji: '🧑‍💼' },
  { id: 'web', label: 'Web', emoji: '🖥️' },
];

function randomRef(channel: Channel): string {
  const tail = Math.random().toString(36).slice(2, 8);
  if (channel === 'ivr') return `CALL-${tail}`;
  if (channel === 'whatsapp') return `+9199${Math.floor(100000 + Math.random() * 899999)}`;
  return `${channel}-${tail}`;
}

export const EnumeratorSandboxPage: React.FC<Props> = ({ isColorBlind = false }) => {
  const [channel, setChannel] = useState<Channel>('whatsapp');
  const [surveyId, setSurveyId] = useState('emp-2026');
  const [ref, setRef] = useState(() => randomRef('whatsapp'));
  const [current, setCurrent] = useState<OutboundPayload | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [simInput, setSimInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [liveTurns, setLiveTurns] = useState<SandboxTurn[]>([]);
  const [realSessions, setRealSessions] = useState<{ session_id: string; channel: string; node_id: string; risk_level?: string }[]>([]);
  const transcriptEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsub = subscribeSandbox((turn) => setLiveTurns((prev) => [...prev.slice(-50), turn]));
    // Poll the backend for REAL active channel sessions (WhatsApp/IVR/avatar
    // bridges that posted to the webhooks) so live citizen traffic shows here.
    const poll = setInterval(() => {
      channels.sessions().then((r) => setRealSessions(r.sessions || [])).catch(() => {});
    }, 3000);
    return () => { unsub(); clearInterval(poll); };
  }, []);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const lastResult = current?.last_result || (liveTurns.length ? liveTurns[liveTurns.length - 1].result : null);
  const adaptive = current?.adaptive || (liveTurns.length ? liveTurns[liveTurns.length - 1].adaptive : null);
  const activeSessions = Array.from(new Set([
    ...realSessions.map((s) => `${s.channel}:${(s.session_id || '').slice(0, 6)}`),
    ...liveTurns.map((t) => `${t.channel}:${t.session_id.slice(0, 6)}`),
  ]));

  async function startSession() {
    setBusy(true);
    setError('');
    try {
      const payload = await channels.start(surveyId, channel, ref);
      setCurrent(payload);
      setTranscript([{ dir: 'out', text: payload.prompt_text.en, node: payload.node_id }]);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  async function sendAnswer(raw: string) {
    if (!raw.trim() || !current) return;
    setBusy(true);
    setError('');
    setTranscript((prev) => [...prev, { dir: 'in', text: raw, node: current.node_id }]);
    try {
      const payload = await channels.answer(channel, ref, raw, {});
      setCurrent(payload);
      const label = payload.type === 'complete' ? '✅ Survey complete' : payload.prompt_text.en;
      setTranscript((prev) => [...prev, { dir: 'out', text: label, node: payload.node_id }]);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setSimInput('');
      setBusy(false);
    }
  }

  const started = !!current;
  const complete = current?.type === 'complete';

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Enumerator Sandbox</h2>
          <p className="text-xs text-slate-500">
            One question out · one answer in · validate · next — proof that WhatsApp, IVR and the AI avatar all
            drive the SAME deterministic intelligence pipeline.
          </p>
        </div>
        <div className="text-[10px] uppercase tracking-wide text-slate-400">
          Active sessions: {activeSessions.length ? activeSessions.join(' · ') : 'none'}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* LEFT — channel launcher */}
        <section className="border border-slate-200 rounded-xl p-4 bg-white">
          <h3 className="text-sm font-bold text-slate-700 mb-3">Channel launcher</h3>
          <div className="grid grid-cols-2 gap-2 mb-3">
            {CHANNELS.map((c) => (
              <button
                key={c.id}
                onClick={() => { setChannel(c.id); setRef(randomRef(c.id)); setCurrent(null); setTranscript([]); }}
                className={`px-2 py-2 rounded-lg text-xs font-semibold border ${
                  channel === c.id ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-slate-50 text-slate-600 border-slate-200'
                }`}
              >
                {c.emoji} {c.label}
              </button>
            ))}
          </div>
          <label className="block text-[11px] font-semibold text-slate-500">Survey</label>
          <input value={surveyId} onChange={(e) => setSurveyId(e.target.value)}
            className="w-full border border-slate-200 rounded px-2 py-1 text-sm mb-2" />
          <label className="block text-[11px] font-semibold text-slate-500">Respondent ref</label>
          <input value={ref} onChange={(e) => setRef(e.target.value)}
            className="w-full border border-slate-200 rounded px-2 py-1 text-sm mb-3 font-mono" />
          <button onClick={startSession} disabled={busy}
            className="w-full bg-emerald-600 text-white rounded-lg py-2 text-sm font-bold disabled:opacity-50">
            {started ? 'Restart session' : 'Start session'}
          </button>

          <p className="mt-3 text-[10px] text-slate-400 leading-snug">
            Live WhatsApp / IVR / AI-avatar sessions from real respondents appear here automatically
            when their bridges post to the channel webhooks — all scored by the same pipeline.
          </p>

          {/* operator console — drives the REAL pipeline (not mock data) */}
          {started && !complete && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <p className="text-[11px] font-semibold text-slate-500 mb-2">Operator console — drives the live pipeline ({channel})</p>
              {current?.options && channel === 'ivr' ? (
                <div className="grid grid-cols-3 gap-1">
                  {current.options.map((o, i) => (
                    <button key={o.value} onClick={() => sendAnswer(String(i + 1))} disabled={busy}
                      className="bg-slate-800 text-white rounded py-2 text-xs">
                      {i + 1}. {o.label_i18n.en}
                    </button>
                  ))}
                </div>
              ) : current?.options ? (
                <div className="flex flex-wrap gap-1">
                  {current.options.map((o) => (
                    <button key={o.value} onClick={() => sendAnswer(o.value)} disabled={busy}
                      className="bg-slate-100 text-slate-700 rounded px-2 py-1 text-xs border border-slate-200">
                      {o.label_i18n.en}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex gap-1">
                  <input value={simInput} onChange={(e) => setSimInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendAnswer(simInput)}
                    placeholder={channel === 'avatar' ? '🎤 dummy STT transcript…' : 'type answer…'}
                    className="flex-1 border border-slate-200 rounded px-2 py-1 text-sm" />
                  <button onClick={() => sendAnswer(simInput)} disabled={busy}
                    className="bg-indigo-600 text-white rounded px-3 text-sm">Send</button>
                </div>
              )}
            </div>
          )}
          {error && <p className="mt-3 text-xs text-rose-600">{error}</p>}
        </section>

        {/* CENTER — transcript per channel */}
        <section className="border border-slate-200 rounded-xl p-4 bg-white flex flex-col">
          <h3 className="text-sm font-bold text-slate-700 mb-3">
            {channel === 'whatsapp' ? 'WhatsApp chat' : channel === 'ivr' ? 'IVR call' : channel === 'avatar' ? 'AI avatar' : 'Web client'}
          </h3>
          <div className={`flex-1 min-h-[280px] max-h-[460px] overflow-y-auto space-y-2 p-2 rounded-lg ${
            channel === 'whatsapp' ? 'bg-[#e5ddd5]' : channel === 'ivr' ? 'bg-slate-900' : 'bg-slate-50'
          }`}>
            {transcript.map((line, idx) => (
              <div key={idx} className={`flex ${line.dir === 'in' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-xs ${bubbleClass(channel, line.dir)}`}>
                  {channel === 'ivr' && (
                    <span className="opacity-60 mr-1">{line.dir === 'out' ? '🔊' : '⌨️'}</span>
                  )}
                  {line.text}
                </div>
              </div>
            ))}
            <div ref={transcriptEnd} />
          </div>
        </section>

        {/* RIGHT — live intelligence readout */}
        <section className="border border-slate-200 rounded-xl p-4 bg-white">
          <h3 className="text-sm font-bold text-slate-700 mb-3">Live intelligence</h3>
          {!lastResult ? (
            <p className="text-xs text-slate-400">Answer a question to see the verdict lane light up.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <ConfidenceGauge score={lastResult.confidence} />
                <TrustBadge score={lastResult.confidence} band={lastResult.risk_level as any} isColorBlind={isColorBlind} />
              </div>
              {adaptive?.action && (
                <div className="text-xs bg-indigo-50 border border-indigo-100 rounded px-2 py-1">
                  <span className="font-bold text-indigo-700">{adaptive.action}</span>
                  <span className="text-slate-600"> — {adaptive.reason}</span>
                </div>
              )}
              {lastResult.flaggedBy && lastResult.flaggedBy.length > 0 && (
                <div className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 rounded px-2 py-1">
                  Flagged by: <span className="font-bold">{lastResult.flaggedBy.join(', ')}</span>
                </div>
              )}
              <div>
                <p className="text-[11px] font-semibold text-slate-500 mb-1">Validation methods & confidence</p>
                <MethodConfidence methods={(lastResult.methods && lastResult.methods.length ? lastResult.methods : lastResult.layers) as MethodResult[]} />
              </div>
            </div>
          )}

          <div className="mt-4 border-t border-slate-100 pt-2">
            <p className="text-[11px] font-semibold text-slate-500 mb-1">Live turns ({liveTurns.length})</p>
            <div className="max-h-40 overflow-y-auto space-y-1">
              {liveTurns.slice(-12).reverse().map((t) => (
                <div key={t.seq} className="text-[10px] text-slate-500 flex justify-between">
                  <span>{t.channel} · {t.node_id}</span>
                  <span className={t.result.risk_level === 'Red' ? 'text-rose-600 font-bold' : 'text-slate-400'}>
                    {t.result.risk_level} {Math.round(t.result.confidence)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

function bubbleClass(channel: Channel, dir: 'out' | 'in'): string {
  if (channel === 'whatsapp') {
    return dir === 'in' ? 'bg-[#dcf8c6] text-slate-800' : 'bg-white text-slate-800';
  }
  if (channel === 'ivr') {
    return dir === 'in' ? 'bg-emerald-700 text-white' : 'bg-slate-700 text-slate-100';
  }
  return dir === 'in' ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-700';
}

export default EnumeratorSandboxPage;
