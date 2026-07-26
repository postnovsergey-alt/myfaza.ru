/**
 * Platform-адаптер. Фичи не знают, где они запущены (Telegram Mini App
 * или обычный веб) — они спрашивают у этого модуля.
 *
 * Обёртка над window.Telegram.WebApp тонкая: initData, тема, haptics,
 * BackButton. Всё остальное — стандартный веб.
 */

import { setLocale } from "@/i18n";

export type Platform = "telegram" | "web";
export type ColorScheme = "light" | "dark";

interface TelegramWebApp {
  initData: string;
  colorScheme: ColorScheme;
  themeParams?: { bg_color?: string };
  ready: () => void;
  expand: () => void;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred: (style: "error" | "success" | "warning") => void;
    selectionChanged: () => void;
  };
  onEvent: (event: string, cb: () => void) => void;
  offEvent: (event: string, cb: () => void) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

const tg = () => window.Telegram?.WebApp;

export function detectPlatform(): Platform {
  return tg()?.initData ? "telegram" : "web";
}

export function getInitData(): string | null {
  return tg()?.initData || null;
}

/**
 * Возвращает светлую/тёмную схему.
 * В Telegram наследуем от него. На вебе — из системной настройки или
 * из локального override пользователя.
 */
export function getColorScheme(override?: "auto" | "light" | "dark"): ColorScheme {
  if (override === "light") return "light";
  if (override === "dark") return "dark";
  const t = tg();
  if (t?.colorScheme) return t.colorScheme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyColorScheme(scheme: ColorScheme) {
  document.documentElement.setAttribute("data-theme", scheme);
}

/** Тактильный отклик — работает только в Telegram, на вебе — no-op */
export function haptic(kind: "tap" | "success" | "warning" = "tap") {
  const hf = tg()?.HapticFeedback;
  if (!hf) return;
  if (kind === "tap") hf.impactOccurred("light");
  else hf.notificationOccurred(kind);
}

/** Инициализация — вызывается один раз при старте */
export function initPlatform(): { platform: Platform; scheme: ColorScheme } {
  const t = tg();
  const platform = detectPlatform();
  if (t) {
    t.ready();
    try {
      t.expand();
    } catch { /* некоторые версии не поддерживают */ }
  }
  // Локаль на будущее — сейчас всегда ru
  setLocale("ru");
  const scheme = getColorScheme();
  applyColorScheme(scheme);
  return { platform, scheme };
}

/** Слушаем смену темы в системе и в Telegram */
export function subscribeThemeChanges(onChange: (s: ColorScheme) => void): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const mediaHandler = () => onChange(getColorScheme());
  media.addEventListener("change", mediaHandler);
  const t = tg();
  const tgHandler = () => onChange(getColorScheme());
  t?.onEvent("themeChanged", tgHandler);
  return () => {
    media.removeEventListener("change", mediaHandler);
    t?.offEvent("themeChanged", tgHandler);
  };
}

/** BackButton в шапке Telegram Mini App */
export function useTgBackButton(show: boolean, onClick: () => void) {
  const t = tg();
  if (!t) return;
  if (show) {
    t.BackButton.show();
    t.BackButton.onClick(onClick);
    return () => {
      t.BackButton.hide();
      t.BackButton.offClick(onClick);
    };
  }
  t.BackButton.hide();
}
