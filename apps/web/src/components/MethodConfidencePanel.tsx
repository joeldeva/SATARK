import React from 'react';
import { ValidationMethod } from '../types';

function qualityColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 50) return 'bg-amber-500';
  return 'bg-rose-500';
}

export const MethodConfidencePanel: React.FC<{ methods?: ValidationMethod[]; title?: string }> = ({ methods, title }) => {
  if (!methods || !methods.length) {
    return <p className="text-xs text-slate-400">No validation methods ran for this response yet.</p>;
  }

  const flagged = methods.filter((method) => method.flagged).map((method) => method.name);

  return (
    <div className="space-y-2">
      {title && <p className="text-[11px] font-semibold text-slate-500">{title}</p>}
      {flagged.length > 0 && (
        <p className="text-[11px] text-rose-600 font-semibold">Flagged by: {flagged.join(', ')}</p>
      )}
      {methods.map((method) => {
        const score = Math.round(method.confidence ?? (method.status === 'pass' ? 100 : method.status === 'warn' ? 55 : 10));
        return (
          <div key={method.name} className={`rounded-lg border p-2 ${method.flagged ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-white'}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-700">{method.name}</span>
              <span className={`text-[10px] font-bold ${method.flagged ? 'text-rose-600' : score >= 80 ? 'text-emerald-600' : 'text-amber-600'}`}>
                {method.flagged ? `FLAGGED / ${score}%` : `${score}% quality`}
              </span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded mt-1 overflow-hidden">
              <div className={`h-full ${qualityColor(score)}`} style={{ width: `${score}%` }} />
            </div>
            {method.method && <p className="text-[10px] text-slate-500 mt-1">{method.method}</p>}
            <p className="text-[10px] text-slate-600 mt-0.5 italic">"{method.reason}"</p>
          </div>
        );
      })}
    </div>
  );
};

export default MethodConfidencePanel;
