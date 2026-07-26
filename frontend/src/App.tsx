import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { TelegramGate } from "@/features/auth/TelegramGate";
import { CalendarPage } from "@/features/calendar/CalendarPage";
import { HomePage } from "@/features/home/HomePage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { StatsPage } from "@/features/stats/StatsPage";
import { applyColorScheme, getColorScheme, initPlatform, subscribeThemeChanges } from "@/platform";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/settings";

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: 1,
    },
  },
});

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, accessToken, ready, restoring } = useAuth();
  const location = useLocation();
  if (!ready || restoring) return null;
  if (!accessToken || !user) {
    return <Navigate to="/entry" replace state={{ from: location }} />;
  }
  // Онбординг форсим ТОЛЬКО у только-что зарегистрировавшихся,
  // у кого точно нет ни одного цикла. Если пользователь возвращается
  // с уже накопленными данными (флаг onboarding_completed мог быть не
  // проставлен из-за исторических багов), HomePage сам разберётся:
  // при пустом состоянии редиректит на /onboarding.
  return children;
}

function Bootstrap() {
  const initAuth = useAuth((s) => s.init);
  const initUi = useUi((s) => s.init);
  const theme = useUi((s) => s.theme);

  useEffect(() => {
    initPlatform();
    initAuth();
    initUi();
    // Возвращающийся пользователь: есть refresh — пробуем поднять сессию
    // без формы входа. Клиент API сам сделает refresh при первом же 401.
    (async () => {
      const state = useAuth.getState();
      if (!state.refreshToken || state.accessToken) return;
      try {
        const r = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ refresh_token: state.refreshToken }),
        });
        if (r.ok) {
          const body = await r.json();
          useAuth.getState().setSession(body);
        } else {
          useAuth.getState().logout();
        }
      } catch {
        // Оффлайн: сессию не восстановили, но и не роняем refresh —
        // пусть при появлении сети пользователь попробует ещё раз.
        useAuth.getState().setRestoring(false);
      }
    })();
    const unsub = subscribeThemeChanges((scheme) => applyColorScheme(scheme));
    return () => unsub();
  }, [initAuth, initUi]);

  useEffect(() => {
    applyColorScheme(getColorScheme(theme));
  }, [theme]);

  return null;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Bootstrap />
        <Routes>
          <Route path="/entry" element={<AppShell bare><TelegramGate /></AppShell>} />
          <Route path="/login" element={<AppShell bare><LoginPage /></AppShell>} />
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <AppShell bare><OnboardingPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell><HomePage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/calendar"
            element={
              <ProtectedRoute>
                <AppShell><CalendarPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/stats"
            element={
              <ProtectedRoute>
                <AppShell><StatsPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <AppShell><SettingsPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
