import { useEffect } from "react";
import type { ReactNode } from "react";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
}

/**
 * Нижний лист-модалка. Открывается снизу, закрывается свайпом
 * (простой — щелчок по подложке или крестик). Появление — CSS-переход.
 */
export function Sheet({ open, onClose, children, title }: SheetProps) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [open, onClose]);

  return (
    <div
      aria-hidden={!open}
      className={[
        "fixed inset-0 z-40 transition-opacity",
        "duration-[var(--dur-base)] ease-[cubic-bezier(0.22,1,0.36,1)]",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <button
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={[
          "absolute inset-x-0 bottom-0 bg-[color:var(--surface)]",
          "rounded-t-[var(--radius-lg)] px-5 pb-[max(env(safe-area-inset-bottom),20px)] pt-4",
          "shadow-[0_-20px_60px_rgba(0,0,0,0.15)] transition-transform",
          "duration-[var(--dur-base)] ease-[cubic-bezier(0.22,1,0.36,1)]",
          open ? "translate-y-0" : "translate-y-full",
          "max-h-[90vh] overflow-auto",
        ].join(" ")}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-[color:var(--border-strong)]" />
        {title && <h2 className="mb-4 text-[17px] font-medium">{title}</h2>}
        {children}
      </div>
    </div>
  );
}
