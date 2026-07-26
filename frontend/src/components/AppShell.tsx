import type { ReactNode } from "react";

import { BottomNav } from "@/components/BottomNav";

interface Props {
  children: ReactNode;
  /** Скрывает нижнюю навигацию (для онбординга, логина) */
  bare?: boolean;
}

/**
 * Общая обёртка экранов. Держит центральную колонку 480px,
 * оставляет место снизу под нижнюю навигацию.
 */
export function AppShell({ children, bare }: Props) {
  return (
    <div className="min-h-screen">
      <main className={["mx-auto max-w-[480px] px-5 pt-5", bare ? "pb-8" : "pb-24"].join(" ")}>
        {children}
      </main>
      {!bare && <BottomNav />}
    </div>
  );
}
