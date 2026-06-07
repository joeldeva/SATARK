import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Navigate, useNavigate } from 'react-router-dom';
import { LockKeyhole, ShieldCheck } from 'lucide-react';
import { seedData } from '../data/seed';
import { login } from '../lib/apiClient';
import { cn } from '../lib/format';
import { useAppStore, workspaceHome } from '../store/appStore';
import { LanguageSwitcher } from '../components/ui';
import type { User } from '../types';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const currentUser = useAppStore((state) => state.currentUser);
  const loginStore = useAppStore((state) => state.login);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [message, setMessage] = useState('');

  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: ({ data }) => {
      const fullUser = seedData.users.find((item) => item.username === data.user.username);
      loginStore(fullUser || ({ ...data.user, password: '' } as User));
      navigate(workspaceHome[data.user.role], { replace: true });
    },
    onError: () => setMessage('Invalid username or password')
  });

  if (currentUser) {
    return <Navigate to={workspaceHome[currentUser.role]} replace />;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    mutation.mutate();
  }

  function prefill(user: User) {
    setUsername(user.username);
    setPassword(user.password);
    setMessage('');
  }

  return (
    <main className="grid min-h-screen place-items-center bg-gov-surface p-4">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-card">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-gov-primary text-white">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-lg font-semibold text-gov-primary">SATARK</p>
              <p className="text-xs text-slate-500">Ministry of Statistics & Programme Implementation</p>
            </div>
          </div>
          <div className="rounded-full bg-gov-primary p-1">
            <LanguageSwitcher />
          </div>
        </div>

        <h1 className="text-2xl font-semibold text-slate-900">{t('signIn')}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{t('tagline')}</p>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">{t('username')}</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
              autoComplete="username"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">{t('password')}</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-gov-teal focus:outline-none focus:ring-2 focus:ring-gov-teal/25"
              autoComplete="current-password"
            />
          </label>

          {message ? <p className="rounded-lg border border-gov-red bg-red-50 px-3 py-2 text-sm text-gov-red">{message}</p> : null}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gov-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-gov-primaryDark focus:outline-none focus:ring-2 focus:ring-gov-teal disabled:opacity-60"
          >
            <LockKeyhole className="h-4 w-4" />
            {mutation.isPending ? 'Signing in...' : t('signInButton')}
          </button>
        </form>

        <div className="mt-5 flex flex-wrap gap-2" aria-label="Demo roles">
          {seedData.users.map((user) => (
            <button
              type="button"
              key={user.username}
              onClick={() => prefill(user)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-gov-teal',
                username === user.username ? 'border-gov-primary bg-gov-primary text-white' : 'border-slate-200 bg-slate-50 text-slate-700'
              )}
            >
              {user.role.toUpperCase()}
            </button>
          ))}
        </div>

        <p className="mt-6 border-t border-slate-100 pt-4 text-center text-xs text-slate-500">
          Secure · Consent-first · Built on India's Digital Public Infrastructure
        </p>
      </section>
    </main>
  );
}
