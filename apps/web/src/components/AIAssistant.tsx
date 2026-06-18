import React, { useMemo, useState } from 'react';
import { Bot, Loader2, MessageCircle, Navigation, Search, Send, X } from 'lucide-react';
import { api } from '../api';

type WindowId = 'survey-design' | 'field-ops' | 'data-quality' | 'national-intel';

type AssistantWindow = {
  id: WindowId;
  label: string;
  subtitle: string;
};

type AssistantMessage = {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  sources?: string[];
};

interface AIAssistantProps {
  windows: AssistantWindow[];
  activeWindow: WindowId;
  onNavigate: (windowId: WindowId) => void;
}

const routeHints: Array<{ id: WindowId; terms: string[] }> = [
  { id: 'survey-design', terms: ['survey design', 'builder', 'questionnaire', 'database', 'code library', 'translation'] },
  { id: 'field-ops', terms: ['field', 'enumerator', 'collection', 'assignment', 'whatsapp', 'respondent'] },
  { id: 'data-quality', terms: ['quality', 'validation', 'coding review', 'nic', 'nco', 'flags'] },
  { id: 'national-intel', terms: ['national', 'dashboard', 'analytics', 'export', 'metrics', 'output'] }
];

function findNavigationTarget(text: string, windows: AssistantWindow[]): WindowId | null {
  const value = text.toLowerCase();
  const allowed = new Set(windows.map(windowItem => windowItem.id));
  const match = routeHints.find(route => allowed.has(route.id) && route.terms.some(term => value.includes(term)));
  return match?.id || null;
}

function sourceLabels(sources: any[] = []) {
  return sources
    .slice(0, 3)
    .map(source => source?.metadata?.source_document || source?.metadata?.filename || source?.id || 'SATARK knowledge base')
    .filter(Boolean);
}

export const AIAssistant: React.FC<AIAssistantProps> = ({ windows, activeWindow, onNavigate }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'I can search SATARK knowledge, explain NIC/NCO workflows, and move you through your authorized windows.'
    }
  ]);

  const activeLabel = useMemo(
    () => windows.find(windowItem => windowItem.id === activeWindow)?.label || 'current workspace',
    [activeWindow, windows]
  );

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    const userMessage: AssistantMessage = { id: `user_${Date.now()}`, role: 'user', text: question };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    const target = findNavigationTarget(question, windows);
    if (target && question.toLowerCase().match(/\b(open|go|show|take|switch|navigate)\b/)) {
      onNavigate(target);
      const label = windows.find(windowItem => windowItem.id === target)?.label || target;
      setMessages(prev => [...prev, {
        id: `assistant_nav_${Date.now()}`,
        role: 'assistant',
        text: `Opened ${label}. You can ask me to find a code, explain a validation flag, or locate the next workflow step.`
      }]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.askAssistant(`${question}\n\nCurrent SATARK window: ${activeLabel}`);
      const sources = sourceLabels(response.sources);
      setMessages(prev => [...prev, {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        text: response.answer,
        sources
      }]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        id: `assistant_error_${Date.now()}`,
        role: 'assistant',
        text: `I could not reach the Gemma/RAG assist lane yet. I can still navigate: ${windows.map(windowItem => windowItem.label).join(', ')}.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full border border-slate-200 bg-white text-[#0B2E5E] shadow-2xl transition hover:-translate-y-0.5 hover:shadow-indigo-200"
        title="Open SATARK AI assist"
        aria-label="Open SATARK AI assist"
      >
        <img src="/mascot.svg" alt="" className="h-10 w-10 object-contain" />
      </button>
    );
  }

  return (
    <section className="fixed bottom-5 right-5 z-50 flex h-[560px] w-[360px] max-w-[calc(100vw-24px)] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl" aria-label="SATARK AI assist">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-900 px-3 py-2 text-white">
        <div className="flex items-center gap-2 min-w-0">
          <img src="/mascot.svg" alt="" className="h-9 w-9 rounded-lg bg-white/95 object-contain p-0.5" />
          <div className="min-w-0">
            <h2 className="text-xs font-black uppercase tracking-wide">SATARK AI Assist</h2>
            <p className="truncate text-[10px] font-semibold text-slate-300">Gemma grounded help for {activeLabel}</p>
          </div>
        </div>
        <button onClick={() => setIsOpen(false)} className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white" aria-label="Close SATARK AI assist">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="border-b border-slate-100 bg-slate-50 px-3 py-2">
        <div className="grid grid-cols-2 gap-1.5">
          {windows.map(windowItem => (
            <button
              key={windowItem.id}
              onClick={() => onNavigate(windowItem.id)}
              className={`flex items-center gap-1.5 rounded-lg border px-2 py-1.5 text-left text-[10px] font-bold transition ${
                activeWindow === windowItem.id ? 'border-indigo-200 bg-indigo-50 text-indigo-800' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-100'
              }`}
              title={`Open ${windowItem.label}`}
            >
              <Navigation className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{windowItem.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto bg-[#F7F8FA] p-3">
        {messages.map(message => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-xl border px-3 py-2 text-xs leading-relaxed ${
              message.role === 'user'
                ? 'border-indigo-200 bg-[#0B2E5E] text-white'
                : 'border-slate-200 bg-white text-slate-700'
            }`}>
              <div className="flex items-start gap-1.5">
                {message.role === 'assistant' && <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#138808]" />}
                <p className="whitespace-pre-wrap">{message.text}</p>
              </div>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 border-t border-slate-100 pt-1.5 text-[10px] font-bold text-slate-500">
                  Sources: {message.sources.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-[11px] font-bold text-slate-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Searching SATARK knowledge
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white p-3">
        <div className="mb-2 flex gap-1.5">
          {['Find NIC code', 'Open data quality'].map(prompt => (
            <button
              key={prompt}
              onClick={() => setInput(prompt)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-bold text-slate-600 hover:bg-slate-100"
            >
              {prompt.includes('Find') ? <Search className="h-3 w-3" /> : <MessageCircle className="h-3 w-3" />}
              {prompt}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-1.5">
          <input
            value={input}
            onChange={event => setInput(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter') sendMessage();
            }}
            placeholder="Ask or navigate..."
            className="min-w-0 flex-1 bg-transparent px-2 text-xs font-semibold text-slate-800 outline-none"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#0B2E5E] text-white disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Send assistant message"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </section>
  );
};
