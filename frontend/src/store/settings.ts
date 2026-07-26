import { create } from "zustand";

type Theme = "auto" | "light" | "dark";
const KEY = "myfaza.theme";

interface UiState {
  theme: Theme;
  init: () => void;
  setTheme: (t: Theme) => void;
}

export const useUi = create<UiState>((set) => ({
  theme: "auto",
  init: () => {
    const saved = (localStorage.getItem(KEY) as Theme | null) ?? "auto";
    set({ theme: saved });
  },
  setTheme: (t) => {
    localStorage.setItem(KEY, t);
    set({ theme: t });
  },
}));
