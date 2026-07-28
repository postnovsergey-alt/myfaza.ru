import { create } from "zustand";

import { hasPin } from "@/features/pin/pinStorage";

interface PinState {
  /** Установлен ли вообще ПИН. */
  enabled: boolean;
  /** Показать экран блокировки поверх приложения. */
  locked: boolean;
  refresh: () => void;
  lock: () => void;
  unlock: () => void;
}

export const usePin = create<PinState>((set) => ({
  enabled: hasPin(),
  // Стартовое значение вычислим в App.tsx: если ПИН включён — сразу locked=true.
  locked: false,
  refresh: () => set({ enabled: hasPin() }),
  lock: () => set({ locked: true }),
  unlock: () => set({ locked: false }),
}));
