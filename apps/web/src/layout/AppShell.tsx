import { type ReactNode, useMemo } from 'react';
import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BarChart3, ClipboardList, Code2, Database, Home, LogOut, MapPinned, Monitor, PenTool, ShieldCheck, Users } from 'lucide-react';
import { LanguageSwitcher, OfflineBanner, SyncIndicator } from '../components/ui';
import { cn } from '../lib/format';
import { useAppStore, workspaceHome } from '../store/appStore';
import type { Role } from '../types';

const workspaceLabels: Record<Role, string> = {
  admin: 'Admin',
  sdrd: 'SDRD',
  fod: 'FOD',
  dpd: 'DPD',
  scd: 'SCD'
};

const navByRole: Record<Role, Array<{ to: string; label: string; icon: typeof Home }>> = {
  admin: [
    { to: '/scd', label: 'Command center', icon: Monitor },
    { to: '/sdrd', label: 'Survey design', icon: PenTool },
    { to: '/fod', label: 'Field operations', icon: Users },
    { to: '/dpd', label: 'Processing', icon: Code2 },
    { to: '/collect/emp-2026', label: 'Collection client', icon: ClipboardList }
  ],
  sdrd: [
    { to: '/sdrd', label: 'My surveys', icon: PenTool },
    { to: '/sdrd?tab=bank', label: 'Question bank', icon: Database },
    { to: '/sdrd?tab=codes', label: 'Code library', icon: Code2 },
    { to: '/collect/emp-2026', label: 'Collection client', icon: ClipboardList }
  ],
  fod: [
    { to: '/fod', label: 'Enumerators', icon: Users },
    { to: '/fod?tab=assignments', label: 'Assignments', icon: MapPinned },
    { to: '/collect/emp-2026', label: 'Collection client', icon: ClipboardList }
  ],
  dpd: [
    { to: '/dpd', label: 'Coding review', icon: Code2 },
    { to: '/dpd?tab=validation', label: 'Validation queue', icon: ShieldCheck },
    { to: '/collect/emp-2026', label: 'Collection client', icon: ClipboardList }
  ],
  scd: [
    { to: '/scd', label: 'Command center', icon: Monitor },
    { to: '/scd?tab=quality', label: 'Quality dashboard', icon: ShieldCheck },
    { to: '/scd?tab=analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/collect/emp-2026', label: 'Collection client', icon: ClipboardList }
  ]
};

export function RequireAuth({ children }: { children: ReactNode }) {
  const currentUser = useAppStore((state) => state.currentUser);
  const location = useLocation();

  if (!currentUser) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

export function RoleRedirect() {
  const currentUser = useAppStore((state) => state.currentUser);
  if (!currentUser) return <Navigate to="/login" replace />;
  return <Navigate to={workspaceHome[currentUser.role]} replace />;
}

export function AppShell() {
  const { t } = useTranslation();
  const currentUser = useAppStore((state) => state.currentUser);
  const logout = useAppStore((state) => state.logout);
  const fontScale = useAppStore((state) => state.fontScale);
  const setFontScale = useAppStore((state) => state.setFontScale);
  const colorBlind = useAppStore((state) => state.colorBlind);
  const toggleColorBlind = useAppStore((state) => state.toggleColorBlind);

  const navigation = useMemo(() => navByRole[currentUser?.role || 'scd'], [currentUser?.role]);

  if (!currentUser) return null;

  return (
    <div className="min-h-screen bg-gov-surface text-slate-900" style={{ fontSize: `${fontScale}rem` }}>
      <OfflineBanner />
      <header className="sticky top-0 z-40 border-b border-gov-primaryDark bg-gov-primary text-white shadow-sm">
        <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-md border border-white/25 bg-white/10" aria-hidden="true">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold tracking-wide">SATARK</span>
                <span className="rounded-full bg-gov-teal px-2 py-0.5 text-[11px] font-semibold">{t('official')}</span>
                <span className="rounded-full bg-gov-green px-2 py-0.5 text-[11px] font-semibold">{t('realtime')}</span>
              </div>
              <p className="text-xs text-white/75">Ministry of Statistics & Programme Implementation</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <LanguageSwitcher />
            <button
              type="button"
              onClick={toggleColorBlind}
              className={cn(
                'rounded-full border border-white/30 px-3 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-white',
                colorBlind ? 'bg-white text-gov-primary' : 'bg-white/10 text-white'
              )}
              aria-pressed={colorBlind}
            >
              {t('colorBlind')}
            </button>
            <div className="inline-flex rounded-full border border-white/30 bg-white/10 p-0.5">
              <button className="rounded-full px-2 py-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white" type="button" onClick={() => setFontScale(fontScale - 0.05)}>
                A-
              </button>
              <button className="rounded-full px-2 py-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white" type="button" onClick={() => setFontScale(fontScale + 0.05)}>
                A+
              </button>
            </div>
            <SyncIndicator />
            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-gov-primary">{workspaceLabels[currentUser.role]}</span>
            <div className="flex items-center gap-2 rounded-full border border-white/30 bg-white/10 py-1 pl-1 pr-3">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-white text-xs font-semibold text-gov-primary">
                {currentUser.name
                  .split(' ')
                  .map((part) => part[0])
                  .join('')
                  .slice(0, 2)}
              </span>
              <span className="text-sm font-medium">{currentUser.name}</span>
              <button
                type="button"
                onClick={logout}
                className="rounded-full p-1 text-white/80 hover:text-white focus:outline-none focus:ring-2 focus:ring-white"
                aria-label={t('signOut')}
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[16rem_1fr]">
        <aside className="border-b border-slate-200 bg-white lg:border-b-0 lg:border-r">
          <nav className="flex gap-2 overflow-x-auto p-3 lg:flex-col lg:overflow-visible lg:p-4" aria-label="Workspace navigation">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      'inline-flex min-w-max items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-gov-teal',
                      isActive ? 'bg-gov-primary text-white' : 'hover:bg-slate-100'
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
