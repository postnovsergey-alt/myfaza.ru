import { create } from "zustand";

type Theme = "auto" | "light" | "dark";
const KEY = "myfaza.theme";

const readSavedTheme = (): Theme => {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "auto") return v;
  } catch { /* SSR / приватный режим */ }
  return "auto";
};

interface UiState {
  theme: Theme;
  init: () => void;
  setTheme: (t: Theme) => void;
}

export const useUi = create<UiState>((set) => ({
  // Читаем сохранённое сразу при создании стора, чтобы первый рендер уже
  // видел выбранную тему и не моргал системной.
  theme: readSavedTheme(),
  init: () => {
    set({ theme: readSavedTheme() });
  },
  setTheme: (t) => {
    try { localStorage.setItem(KEY, t); } catch { /* см. выше */ }
    set({ theme: t });
  },
}));
