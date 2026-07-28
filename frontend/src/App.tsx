import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { AccountPage } from "@/features/account/AccountPage";
import { ConsentGate } from "@/features/auth/ConsentGate";
import { LinkPage } from "@/features/auth/LinkPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { TelegramGate } from "@/features/auth/TelegramGate";
import { CalendarPage } from "@/features/calendar/CalendarPage";
import { HomePage } from "@/features/home/HomePage";
import { PinLockScreen } from "@/features/pin/PinLockScreen";
import {
  clearBackgrounded,
  hasPin,
  markBackgrounded,
  needsLockAfterBackground,
} from "@/features/pin/pinStorage";
import { PrivacyPage } from "@/features/privacy/PrivacyPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { StatsPage } from "@/features/stats/StatsPage";
import { applyColorScheme, getColorScheme, initPlatform, subscribeThemeChanges } from "@/platform";
import { useAuth } from "@/store/auth";
import { usePin } from "@/store/pin";
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
  // Если согласие ещё не дано (обычно TG-user из /start MiniApp) —
  // блокируем доступ к любой странице кроме consent-экрана.
  // Веб-регистрация проставляет согласие в LoginPage.
  if (!user.consent_given_at) {
    return <AppShell bare><ConsentGate /></AppShell>;
  }
  return children;
}

function Bootstrap() {
  const initAuth = useAuth((s) => s.init);
  const initUi = useUi((s) => s.init);
  const theme = useUi((s) => s.theme);
  const lockPin = usePin((s) => s.lock);
  const refreshPin = usePin((s) => s.refresh);

  useEffect(() => {
    initPlatform();
    initAuth();
    initUi();
    // ПИН: при холодном запуске сразу блокируем, если он установлен.
    // Экран блокировки сидит поверх приложения, пользователь не видит
    // содержимого до ввода. См. features/pin/pinStorage.ts.
    refreshPin();
    if (hasPin()) lockPin();

    const onVisibility = () => {
      if (!hasPin()) return;
      if (document.visibilityState === "hidden") {
        markBackgrounded();
      } else if (document.visibilityState === "visible") {
        if (needsLockAfterBackground()) lockPin();
        clearBackgrounded();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
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
    const unsub = subscribeThemeChanges(
      () => useUi.getState().theme,
      (scheme) => applyColorScheme(scheme),
    );
    return () => {
      unsub();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [initAuth, initUi, lockPin, refreshPin]);

  useEffect(() => {
    applyColorScheme(getColorScheme(theme));
  }, [theme]);

  return null;
}

function PinOverlay() {
  const locked = usePin((s) => s.locked);
  const accessToken = useAuth((s) => s.accessToken);
  // На /login/entry/link не блокируем: пользователь может использовать
  // «Забыли ПИН?» → login. Оверлей нужен только когда есть активная сессия.
  if (!locked || !accessToken) return null;
  return <PinLockScreen />;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Bootstrap />
        <PinOverlay />
        <Routes>
          <Route path="/entry" element={<AppShell bare><TelegramGate /></AppShell>} />
          <Route path="/login" element={<AppShell bare><LoginPage /></AppShell>} />
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
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AppShell><AccountPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route path="/privacy" element={<AppShell bare><PrivacyPage /></AppShell>} />
          <Route path="/link" element={<AppShell bare><LinkPage /></AppShell>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
