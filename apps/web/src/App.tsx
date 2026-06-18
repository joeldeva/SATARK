/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { api } from './api';
import { User, UserRole } from './types';
import { translations } from './i18n';
import { SDRDWorkspace } from './components/SDRDWorkspace';
import { FODWorkspace } from './components/FODWorkspace';
import { DPDWorkspace } from './components/DPDWorkspace';
import { SCDWorkspace } from './components/SCDWorkspace';
import { AIAssistant } from './components/AIAssistant';
import {
  Bell,
  ChevronRight,
  ClipboardCheck,
  Eye,
  FolderLock,
  LayoutDashboard,
  LogOut,
  Search,
  Settings,
  ShieldAlert,
  Users
} from 'lucide-react';

type WindowId = 'survey-design' | 'field-ops' | 'data-quality' | 'national-intel';

const ROLE_PROFILES: Record<UserRole, { label: string; division: string; username: string; password: string }> = {
  hsd: { label: 'HSD', division: 'Household Survey Division', username: 'hsd', password: 'hsd123' },
  ensd: { label: 'EnSD', division: 'Enterprise Survey Division', username: 'ensd', password: 'ensd123' },
  fod: { label: 'FOD', division: 'Field Operations Division', username: 'fod', password: 'field123' },
  cqcd: { label: 'C&QCD', division: 'Collection & Quality Control Division', username: 'cqcd', password: 'quality123' },
  diid: { label: 'DIID', division: 'Data Informatics & Innovation Division', username: 'diid', password: 'diid123' },
  aspd: { label: 'ASPD', division: 'Analytics & Statistical Products Division', username: 'aspd', password: 'aspd123' },
  cicd: { label: 'CICD', division: 'Central Informatics Coordination Division', username: 'cicd', password: 'cicd123' },
  cdd: { label: 'CDD', division: 'Coordination & Dissemination Division', username: 'cdd', password: 'cdd123' }
};

const ROLE_ACCESS: Record<UserRole, WindowId[]> = {
  hsd: ['survey-design'],
  ensd: ['survey-design'],
  fod: ['field-ops', 'data-quality'],
  cqcd: ['data-quality'],
  diid: ['national-intel'],
  aspd: ['national-intel'],
  cicd: ['national-intel'],
  cdd: ['national-intel']
};

const WINDOW_CONFIG: Record<WindowId, { label: string; subtitle: string; icon: typeof Settings }> = {
  'survey-design': {
    label: 'Survey Design',
    subtitle: 'HSD + EnSD',
    icon: Settings
  },
  'field-ops': {
    label: 'Field Operation',
    subtitle: 'FOD',
    icon: Users
  },
  'data-quality': {
    label: 'Data Collection & Quality Assurance Hub',
    subtitle: 'C&QCD',
    icon: ClipboardCheck
  },
  'national-intel': {
    label: 'National Intelligence & Statistical Output Hub',
    subtitle: 'Data Governance Vertical: DIID + ASPD + CICD + CDD',
    icon: LayoutDashboard
  }
};

const isKnownRole = (role: string): role is UserRole => role in ROLE_PROFILES;
const getDefaultWindowForRole = (role: UserRole): WindowId => ROLE_ACCESS[role][0];

export default function App() {
  const storedUser = api.getCurrentUser();
  const initialUser = storedUser && isKnownRole(storedUser.role) ? storedUser : null;

  const [currentUser, setCurrentUser] = useState<User | null>(initialUser);
  const [lang, setLang] = useState<'en' | 'hi' | 'ta'>('en');
  const [isColorBlind, setIsColorBlind] = useState<boolean>(false);
  const [textSize, setTextSize] = useState<'normal' | 'large' | 'extra'>('normal');
  const [selectedRole, setSelectedRole] = useState<UserRole>('hsd');
  const [username, setUsername] = useState<string>(ROLE_PROFILES.hsd.username);
  const [password, setPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<WindowId>(initialUser ? getDefaultWindowForRole(initialUser.role) : 'survey-design');
  const [searchQuery, setSearchQuery] = useState('');
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const t = translations[lang];
  const activeRoleProfile = currentUser ? ROLE_PROFILES[currentUser.role] : ROLE_PROFILES[selectedRole];
  const authorizedWindows = currentUser ? ROLE_ACCESS[currentUser.role] : [];

  const applyTextSizeClass = () => {
    if (textSize === 'large') return 'text-[1.1rem]';
    if (textSize === 'extra') return 'text-[1.2rem] pb-4';
    return '';
  };

  const handleLogin = async () => {
    if (!username.trim()) {
      setLoginError('Official ID is required');
      return;
    }
    if (!password.trim()) {
      setLoginError('Password is required');
      return;
    }

    try {
      const user = await api.login(username, password, selectedRole);
      setCurrentUser(user);
      setActiveTab(getDefaultWindowForRole(user.role));
      setLoginError('');
      setIsUserMenuOpen(false);
      setIsNotificationOpen(false);
    } catch {
      setLoginError('Authentication verification failed. Check role, official ID, and password.');
    }
  };

  const handleSignout = async () => {
    await api.logout();
    setCurrentUser(null);
    setPassword('');
    setLoginError('');
    setActiveTab('survey-design');
    setIsUserMenuOpen(false);
    setIsNotificationOpen(false);
  };

  const handleRoleChange = (role: UserRole) => {
    setSelectedRole(role);
    setUsername(ROLE_PROFILES[role].username);
    setPassword('');
    setLoginError('');
  };

  const renderWorkspace = () => {
    if (!currentUser || !ROLE_ACCESS[currentUser.role].includes(activeTab)) {
      return null;
    }

    if (activeTab === 'survey-design') {
      return <SDRDWorkspace lang={lang} isColorBlind={isColorBlind} onSurveyPublished={() => {}} />;
    }
    if (activeTab === 'field-ops') {
      return <FODWorkspace lang={lang} isColorBlind={isColorBlind} />;
    }
    if (activeTab === 'data-quality') {
      return <DPDWorkspace lang={lang} isColorBlind={isColorBlind} />;
    }
    return <SCDWorkspace lang={lang} isColorBlind={isColorBlind} />;
  };

  return (
    <div className={`min-h-screen bg-[#F7F8FA] flex flex-col font-sans transition-all selection:bg-indigo-100 ${applyTextSizeClass()}`}>
      <div className="h-[3px] w-full bg-gradient-to-r from-[#FF9933] via-white to-[#138808] shrink-0" role="presentation" />

      <div className="bg-slate-900 text-slate-300 text-[11px] h-8 px-6 flex items-center justify-between font-medium border-b border-slate-800 shrink-0 select-none">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-200">Government of India</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Ministry of Statistics & Programme Implementation</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="#app-workspace-shell" className="hover:text-white transition-all hidden md:inline">Skip to main content</a>
          <span className="text-slate-800 hidden md:inline">|</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setTextSize('normal')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${textSize === 'normal' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>A-</button>
            <button onClick={() => setTextSize('large')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${textSize === 'large' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>A</button>
            <button onClick={() => setTextSize('extra')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${textSize === 'extra' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>A+</button>
          </div>
          <button
            onClick={() => setIsColorBlind(!isColorBlind)}
            className={`p-1 hover:text-white transition-colors duration-150 flex items-center gap-1.5 ${isColorBlind ? 'text-[#FF9933]' : 'text-slate-400'}`}
            title="Toggle contrast assistance"
          >
            <Eye className="w-3.5 h-3.5" />
            <span className="text-[10px] uppercase tracking-wider font-extrabold hidden sm:inline">Contrast Assist</span>
          </button>
          <div className="flex items-center gap-1 rounded border border-slate-800 bg-slate-800 p-0.5">
            <button onClick={() => setLang('en')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${lang === 'en' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>EN</button>
            <button onClick={() => setLang('hi')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${lang === 'hi' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>HI</button>
            <button onClick={() => setLang('ta')} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${lang === 'ta' ? 'bg-[#0B2E5E] text-white' : 'hover:text-white text-slate-400'}`}>TA</button>
          </div>
        </div>
      </div>

      <header className="bg-white border-b border-slate-200 px-6 h-16 flex items-center justify-between gap-4 shadow-sm shrink-0 relative z-40">
        <div className="flex items-center gap-3.5">
          <img src="/icon.svg" alt="SATARK" className="h-11 w-11 rounded-xl border border-slate-200 bg-white object-contain p-1 shadow-sm shrink-0" />
          <div className="flex flex-col text-left">
            <span className="text-[9px] sm:text-[11px] font-bold text-[#5A6577] uppercase tracking-wide leading-none">Ministry of Statistics & Programme Implementation</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-base font-black text-[#0B2E5E] tracking-tight leading-none">SATARK</span>
              <span className="text-[10px] text-slate-450 border-l border-slate-300 pl-2 leading-none font-medium hidden sm:inline">
                Adaptive Survey Intelligence & Validation Layer
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {currentUser && (
            <div className="relative hidden md:block">
              <div className="flex w-64 items-center rounded-xl border border-slate-250 bg-slate-50">
                <Search className="w-4 h-4 text-slate-400 ml-3 shrink-0" />
                <input
                  type="text"
                  placeholder="Search authorized workspace..."
                  value={searchQuery}
                  onChange={event => setSearchQuery(event.target.value)}
                  className="w-full p-2 pl-2 bg-transparent text-xs text-slate-800 focus:outline-none"
                />
              </div>
            </div>
          )}

          {currentUser && (
            <div className="relative">
              <button
                onClick={() => { setIsNotificationOpen(!isNotificationOpen); setIsUserMenuOpen(false); }}
                className="p-2 hover:bg-slate-100 rounded-xl text-slate-500 hover:text-slate-800 relative border border-slate-200/60 transition-colors"
                title="System notifications"
              >
                <Bell className="w-4 h-4" />
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500" />
              </button>

              {isNotificationOpen && (
                <div className="absolute right-0 top-11 w-80 bg-white border border-slate-300 rounded-xl shadow-xl z-50 overflow-hidden">
                  <div className="bg-slate-900 p-3 flex justify-between text-white border-b border-slate-800">
                    <span className="text-[10px] uppercase font-black tracking-widest font-mono text-slate-300">Access Monitor</span>
                    <span className="bg-emerald-600 text-white text-[8px] font-black px-1.5 rounded uppercase">RBAC Active</span>
                  </div>
                  <div className="p-3 text-xs text-slate-650 font-semibold">
                    {activeRoleProfile.label} can access {authorizedWindows.length} SATARK window{authorizedWindows.length === 1 ? '' : 's'}.
                  </div>
                </div>
              )}
            </div>
          )}

          {currentUser ? (
            <div className="relative">
              <button
                onClick={() => { setIsUserMenuOpen(!isUserMenuOpen); setIsNotificationOpen(false); }}
                className="w-8 h-8 rounded-full bg-[#0B2E5E] text-white text-xs font-black flex items-center justify-center border border-slate-350 hover:ring-2 hover:ring-indigo-100 transition-all font-mono uppercase shadow-inner"
              >
                {currentUser.name ? currentUser.name.split(' ').map(name => name[0]).join('') : activeRoleProfile.label.slice(0, 2)}
              </button>

              {isUserMenuOpen && (
                <div className="absolute right-0 top-11 w-72 bg-white border border-slate-300 rounded-xl shadow-xl z-50 p-3.5 space-y-3.5">
                  <div className="border-b pb-2 text-left">
                    <div className="text-xs font-bold text-slate-900">{currentUser.name}</div>
                    <span className="text-[9px] uppercase font-bold text-[#5A6577] block font-mono">UID: #{currentUser.id}</span>
                    <span className="inline-block bg-indigo-50 border border-indigo-150 text-indigo-700 rounded px-1.5 py-0.5 mt-1 text-[9px] font-black uppercase">
                      {activeRoleProfile.label} Account
                    </span>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-left">
                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider block">Authenticated division</span>
                    <div className="mt-1 text-xs font-bold text-slate-800">{activeRoleProfile.division}</div>
                    <div className="mt-1 text-[10px] font-semibold text-slate-500">
                      Access: {authorizedWindows.map(windowId => WINDOW_CONFIG[windowId].label).join(', ')}
                    </div>
                  </div>
                  <button
                    onClick={handleSignout}
                    className="w-full py-1.5 px-3 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 border border-rose-100 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    {t.logOut}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-slate-400 font-mono tracking-tight flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-rose-500 rounded-full" />
              Not Authenticated
            </div>
          )}
        </div>
      </header>

      {!currentUser ? (
        <section className="flex-1 flex flex-col justify-center items-center py-10 px-4 bg-slate-100">
          <div className="w-full max-w-xl bg-white rounded-xl border border-slate-300 p-8 space-y-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]" />

            <div className="text-center space-y-1.5">
              <img src="/mascot.svg" alt="SATARK assist mascot" className="mx-auto mb-3 h-20 w-20 rounded-2xl border border-slate-200 bg-slate-50 object-contain p-1 shadow-sm" />
              <span className="text-xs font-black tracking-widest text-[#0B2E5E] uppercase font-mono block">Government Grade Role Based Access Control</span>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans">SATARK Official Login</h1>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">Select your MoSPI division, authenticate, and open only the windows authorized for that role.</p>
            </div>

            {loginError && (
              <div className="p-3 bg-rose-50 text-rose-800 border border-rose-100 rounded-lg text-xs font-medium flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{loginError}</span>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1" htmlFor="role">Division / Role</label>
                <select
                  id="role"
                  value={selectedRole}
                  onChange={event => handleRoleChange(event.target.value as UserRole)}
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl bg-slate-50 focus:bg-white focus:outline-indigo-500 transition-colors font-bold text-slate-800"
                >
                  {(Object.keys(ROLE_PROFILES) as UserRole[]).map(role => (
                    <option key={role} value={role}>
                      {ROLE_PROFILES[role].label} - {ROLE_PROFILES[role].division}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1" htmlFor="username">Official ID</label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={event => setUsername(event.target.value)}
                  placeholder={`e.g., ${ROLE_PROFILES[selectedRole].username}`}
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl bg-slate-50 focus:bg-white focus:outline-indigo-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1" htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  placeholder="Enter division password"
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl bg-slate-50 focus:bg-white focus:outline-indigo-500 transition-colors"
                />
              </div>

              <button
                onClick={handleLogin}
                className="w-full py-3 bg-[#0B2E5E] hover:bg-[#071f42] text-white font-bold text-xs rounded-xl shadow-md transition-colors"
              >
                Authenticate & Open SATARK
              </button>
            </div>

            <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider flex items-center gap-1">
                <FolderLock className="w-3.5 h-3.5" />
                Access after authentication
              </span>
              <div className="flex gap-1.5 flex-wrap">
                {ROLE_ACCESS[selectedRole].map(windowId => (
                  <span key={windowId} className="py-1 px-2.5 bg-white border border-indigo-100 text-indigo-700 rounded-lg text-[10px] font-bold shadow-sm">
                    {WINDOW_CONFIG[windowId].label}
                  </span>
                ))}
              </div>
              <p className="text-[10px] font-semibold text-slate-500">
                Demo credential: <span className="font-mono font-black text-slate-700">{ROLE_PROFILES[selectedRole].username}</span> / <span className="font-mono font-black text-slate-700">{ROLE_PROFILES[selectedRole].password}</span>
              </p>
            </div>

            <div className="border-t border-slate-150 pt-4 text-center">
              <p className="text-[9px] text-slate-400 tracking-tight font-medium uppercase">
                {t.secureNotice}
              </p>
            </div>
          </div>
        </section>
      ) : (
        <div className="flex-1 flex flex-col md:flex-row items-stretch" id="app-workspace-shell">
          <nav className="w-full md:w-72 bg-white border-r border-slate-200 py-4 px-3 flex flex-col gap-5 justify-between shrink-0">
            <div className="space-y-5">
              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl space-y-1">
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 block">Workspace access</span>
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <FolderLock className="w-4 h-4 text-indigo-700 shrink-0" />
                  <span>{activeRoleProfile.label} - {activeRoleProfile.division}</span>
                </div>
              </div>

              <div className="space-y-1.5" role="tablist">
                {authorizedWindows.map(windowId => {
                  const config = WINDOW_CONFIG[windowId];
                  const IconComponent = config.icon;
                  return (
                    <button
                      key={windowId}
                      onClick={() => setActiveTab(windowId)}
                      className={`w-full text-left py-2 px-3.5 rounded-lg flex items-center justify-between transition-colors ${
                        activeTab === windowId ? 'bg-indigo-750 text-white font-bold shadow' : 'text-slate-650 hover:bg-slate-50 hover:text-slate-900 font-semibold text-xs'
                      }`}
                      role="tab"
                      aria-selected={activeTab === windowId}
                    >
                      <span className="flex items-center gap-2 text-xs">
                        <IconComponent className="w-4 h-4 shrink-0" />
                        <span>
                          <span className="block">{config.label}</span>
                          <span className="block text-[9px] opacity-70">{config.subtitle}</span>
                        </span>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 opacity-50" />
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex md:hidden items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-800">{currentUser.name}</div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">{activeRoleProfile.label} office</span>
              </div>
              <button onClick={handleSignout} className="px-3 py-1 bg-rose-50 text-rose-600 rounded text-xs font-semibold">
                {t.logOut}
              </button>
            </div>
          </nav>

          <div className="flex-1 p-4 md:p-6 overflow-y-auto">
            {renderWorkspace()}
          </div>
        </div>
      )}
      {currentUser && (
        <AIAssistant
          activeWindow={activeTab}
          windows={authorizedWindows.map(windowId => ({
            id: windowId,
            label: WINDOW_CONFIG[windowId].label,
            subtitle: WINDOW_CONFIG[windowId].subtitle
          }))}
          onNavigate={setActiveTab}
        />
      )}
    </div>
  );
}
