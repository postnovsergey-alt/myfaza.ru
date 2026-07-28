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

// telegram-web-app.js подключён в index.html и создаёт window.Telegram.WebApp
// даже в обычном браузере — с дефолтным colorScheme="light". Поэтому «мы в
// Telegram» — это именно наличие initData, а не наличие объекта WebApp.
const inTelegram = () => !!tg()?.initData;

export function detectPlatform(): Platform {
  return inTelegram() ? "telegram" : "web";
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
  if (inTelegram()) {
    const scheme = tg()?.colorScheme;
    if (scheme) return scheme;
  }
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

/** Инициализация — вызывается один раз при старте.
 *  Схему НЕ применяем здесь: это делает App через useEffect по [theme],
 *  когда UI-стор уже поднял сохранённый override из localStorage. Иначе
 *  успеваем моргнуть системной темой поверх выбранной пользователем. */
export function initPlatform(): { platform: Platform } {
  const t = tg();
  const platform = detectPlatform();
  if (t && inTelegram()) {
    t.ready();
    try {
      t.expand();
    } catch { /* некоторые версии не поддерживают */ }
  }
  // Локаль на будущее — сейчас всегда ru
  setLocale("ru");
  return { platform };
}

/** Слушаем смену темы в системе и в Telegram.
 *  Колбэк получает override пользователя, чтобы «auto» шёл за системой,
 *  а явно выбранная тема НЕ перезатиралась при смене системной. */
export function subscribeThemeChanges(
  getOverride: () => "auto" | "light" | "dark",
  onChange: (s: ColorScheme) => void,
): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const mediaHandler = () => onChange(getColorScheme(getOverride()));
  media.addEventListener("change", mediaHandler);
  const t = tg();
  const tgHandler = () => onChange(getColorScheme(getOverride()));
  if (inTelegram()) t?.onEvent("themeChanged", tgHandler);
  return () => {
    media.removeEventListener("change", mediaHandler);
    if (inTelegram()) t?.offEvent("themeChanged", tgHandler);
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
