import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Enumerator, Language, LiveFlag, Role, TrustLevel, User } from '../types';

interface AppState {
  currentUser: Omit<User, 'password'> | null;
  token: string | null;
  language: Language;
  colorBlind: boolean;
  fontScale: number;
  simulatedOffline: boolean;
  queuedCount: number;
  liveFlags: LiveFlag[];
  enumerators: Enumerator[];
  login: (user: Omit<User, 'password'>, token?: string | null) => void;
  logout: () => void;
  setLanguage: (language: Language) => void;
  toggleColorBlind: () => void;
  setFontScale: (fontScale: number) => void;
  setSimulatedOffline: (value: boolean) => void;
  setQueuedCount: (count: number) => void;
  addLiveFlag: (flag: LiveFlag) => void;
  updateEnumeratorTrust: (id: string, score: number, level: TrustLevel) => void;
  resetLocalState: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentUser: null,
      token: null,
      language: 'en',
      colorBlind: false,
      fontScale: 1,
      simulatedOffline: false,
      queuedCount: 0,
      liveFlags: [],
      enumerators: [],
      login: (user, token = null) =>
        set({
          currentUser: {
            username: user.username,
            role: user.role,
            name: user.name
          },
          token
        }),
      logout: () => set({ currentUser: null, token: null }),
      setLanguage: (language) => set({ language }),
      toggleColorBlind: () => set((state) => ({ colorBlind: !state.colorBlind })),
      setFontScale: (fontScale) => set({ fontScale: Math.min(1.18, Math.max(0.9, fontScale)) }),
      setSimulatedOffline: (value) => set({ simulatedOffline: value }),
      setQueuedCount: (count) => set({ queuedCount: count }),
      addLiveFlag: (flag) =>
        set((state) => ({
          liveFlags: [flag, ...state.liveFlags.filter((item) => item.id !== flag.id)].slice(0, 20)
        })),
      updateEnumeratorTrust: (id, score, level) =>
        set((state) => ({
          enumerators: state.enumerators.map((enumerator) =>
            enumerator.id === id
              ? {
                  ...enumerator,
                  trustScore: score,
                  trustLevel: level,
                  trustTrend: [...enumerator.trustTrend.slice(-6), score]
                }
              : enumerator
          )
        })),
      resetLocalState: () => set({ liveFlags: [], enumerators: [], queuedCount: 0 })
    }),
    {
      name: 'satark-session',
      partialize: (state) => ({
        currentUser: state.currentUser,
        token: state.token,
        language: state.language,
        colorBlind: state.colorBlind,
        fontScale: state.fontScale,
        simulatedOffline: state.simulatedOffline
      })
    }
  )
);

export const workspaceHome: Record<Role, string> = {
  admin: '/scd',
  sdrd: '/sdrd',
  fod: '/fod',
  dpd: '/dpd',
  scd: '/scd'
};
