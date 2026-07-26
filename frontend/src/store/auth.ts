import { create } from "zustand";

import type { TokenResponse, UserOut } from "@/api/client";

const REFRESH_KEY = "myfaza.refresh";

interface AuthState {
  user: UserOut | null;
  accessToken: string | null;
  refreshToken: string | null;
  ready: boolean;
  /**
   * true, пока мы пытаемся восстановить сессию из refresh-токена на старте.
   * ProtectedRoute смотрит на этот флаг и не редиректит на /login,
   * пока попытка не завершится.
   */
  restoring: boolean;
  init: () => void;
  setSession: (t: TokenResponse) => void;
  setUser: (u: UserOut) => void;
  setRestoring: (v: boolean) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  ready: false,
  restoring: false,

  init: () => {
    const refresh = localStorage.getItem(REFRESH_KEY);
    set({ refreshToken: refresh, ready: true, restoring: !!refresh });
  },

  setSession: (t) => {
    localStorage.setItem(REFRESH_KEY, t.refresh_token);
    set({
      user: t.user,
      accessToken: t.access_token,
      refreshToken: t.refresh_token,
      restoring: false,
    });
  },

  setUser: (u) => set({ user: u }),
  setRestoring: (v) => set({ restoring: v }),

  logout: () => {
    localStorage.removeItem(REFRESH_KEY);
    set({ user: null, accessToken: null, refreshToken: null, restoring: false });
  },
}));
