import { useEffect } from "react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";

interface Props {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

/**
 * Инлайн-модалка подтверждения. Заменяет window.confirm(): тот
 * ненадёжно ведёт себя в PWA/установленном приложении и в Telegram
 * Mini App, а нам нужны предсказуемые последствия у деструктивных
 * действий (удаление аккаунта, отзыв согласия, удаление цикла).
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  danger,
  busy,
  onConfirm,
  onClose,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && !busy && onClose();
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [open, busy, onClose]);

  return (
    <div
      aria-hidden={!open}
      className={[
        "fixed inset-0 z-50 flex items-center justify-center px-4",
        "transition-opacity duration-[var(--dur-base)]",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <button
        aria-label={t("action.cancel")}
        onClick={() => !busy && onClose()}
        className="absolute inset-0 bg-black/50"
      />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className={[
          "relative w-full max-w-[400px] rounded-[var(--radius-lg)]",
          "bg-[color:var(--surface)] p-5 shadow-[0_20px_60px_rgba(0,0,0,0.25)]",
          "transition-transform duration-[var(--dur-base)]",
          open ? "translate-y-0" : "translate-y-4",
        ].join(" ")}
      >
        <h2 id="confirm-title" className="mb-2 text-[17px] font-medium">
          {title}
        </h2>
        {description && (
          <div className="mb-4 text-[14px] text-[color:var(--text-soft)]">
            {description}
          </div>
        )}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            variant="ghost"
            size="md"
            onClick={onClose}
            disabled={busy}
          >
            {cancelLabel ?? t("action.cancel")}
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            size="md"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? t("action.saving") : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
