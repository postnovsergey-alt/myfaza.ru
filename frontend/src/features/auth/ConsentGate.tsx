import { useState } from "react";

import { api } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";

/**
 * Одноразовый экран согласия — показывается только тем, у кого
 * consent_given_at пусто. Обычно это TG-user'ы, попавшие в MiniApp
 * через /start (веб-регистрация ставит согласие в LoginPage).
 *
 * По 152-ФЗ ст. 10: сбор специальных категорий ПДн (о здоровье)
 * запрещён без явного согласия. Пока consent не проставлен —
 * никакая часть приложения с данными о цикле недоступна.
 */
export function ConsentGate() {
  const setUser = useAuth((s) => s.setUser);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const accept = async () => {
    setErr(null);
    setBusy(true);
    try {
      await api.post("/auth/consent", { version: "1.0" });
      const s = useAuth.getState();
      if (s.user) {
        setUser({
          ...s.user,
          consent_given_at: new Date().toISOString(),
          consent_version: "1.0",
        });
      }
    } catch {
      setErr(t("consent.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] flex-col justify-center gap-6">
      <div>
        <h1 className="text-[22px] font-medium">{t("consent.title")}</h1>
        <p className="mt-2 text-[color:var(--text-soft)]">{t("consent.body")}</p>
      </div>

      <label className="flex items-start gap-3 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="mt-1 h-5 w-5 accent-[color:var(--accent)]"
        />
        <span className="text-[14px]">{t("consent.confirm")}</span>
      </label>

      {err && (
        <div
          role="alert"
          className="rounded-[var(--radius)] bg-[color:var(--error-bg,#f8d7d5)] p-3 text-[14px] text-[color:var(--error,#8a1c1c)]"
        >
          {err}
        </div>
      )}

      <div className="mt-auto">
        <Button size="lg" fullWidth disabled={!checked || busy} onClick={accept}>
          {busy ? t("action.saving") : t("consent.continue")}
        </Button>
      </div>
    </div>
  );
}
