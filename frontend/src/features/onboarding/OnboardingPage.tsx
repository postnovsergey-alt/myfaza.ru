import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError, type Cycle, type PredictionOut, type UserOut } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";
import { Slider } from "./Slider";

const TODAY = new Date().toISOString().slice(0, 10);

export function OnboardingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const setUser = useAuth((s) => s.setUser);

  // Guard: если уже есть циклы (онбординг пройден), уводим на главную.
  // Не даём случайно пройти онбординг второй раз.
  const existing = useQuery({
    queryKey: ["prediction"],
    queryFn: async () => {
      try {
        return await api.get<PredictionOut>("/predictions/next");
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
    staleTime: 30_000,
  });

  useEffect(() => {
    if (existing.data) {
      navigate("/", { replace: true });
    }
  }, [existing.data, navigate]);

  const [consent, setConsent] = useState(false);
  const [lastStart, setLastStart] = useState<string>(TODAY);
  const [cycleLen, setCycleLen] = useState(28);
  const [periodLen, setPeriodLen] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!consent) {
      setError(t("onboarding.error.consent"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/consent", { version: "1.0" });
      await api
        .patch("/settings", {
          avg_cycle_length: cycleLen,
          avg_period_length: periodLen,
        })
        .catch(() => {
          // settings не критичны — прогноз пересчитается по циклам
        });
      try {
        await api.post<Cycle>("/cycles", {
          start_date: lastStart,
          source: "web",
        });
      } catch (e) {
        // CYCLE_OVERLAP значит цикл уже был — пользователь повторно
        // онбордится (например, после отказа сохранить в прошлый раз).
        // Не блокируем — идём как будто успех, guard в next render уведёт на /.
        if (!(e instanceof ApiError && e.code === "CYCLE_OVERLAP")) {
          throw e;
        }
      }
      const state = useAuth.getState();
      if (state.user) {
        setUser({ ...state.user, onboarding_completed: true } as UserOut);
      }
      // Инвалидируем — HomePage при монтировании подтянет свежий prediction.
      qc.invalidateQueries({ queryKey: ["prediction"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      navigate("/", { replace: true });
    } catch (e) {
      console.error("onboarding submit failed", e);
      setError(t("onboarding.error.generic"));
    } finally {
      setBusy(false);
    }
  };

  // Ждём проверку — иначе будет мелькание формы у уже онбордившихся.
  if (existing.isLoading) {
    return (
      <div className="pt-20 text-center text-[color:var(--text-soft)]">
        {t("action.loading")}
      </div>
    );
  }

  return (
    <div className="flex min-h-[80vh] flex-col gap-6">
      <div>
        <h1>{t("onboarding.title")}</h1>
        <p className="mt-1 text-[color:var(--text-soft)]">
          {t("onboarding.subtitle")}
        </p>
      </div>

      <Field
        label={t("onboarding.field.lastStart")}
        htmlFor="lastStart"
        help={t("onboarding.field.lastStart.help")}
      >
        <Input
          id="lastStart"
          type="date"
          max={TODAY}
          value={lastStart}
          onChange={(e) => setLastStart(e.target.value)}
        />
      </Field>

      <Field label={t("onboarding.field.cycleLen")} htmlFor="cycleLen">
        <Slider
          value={cycleLen}
          min={21}
          max={40}
          unit={t("onboarding.q2.unit")}
          onChange={setCycleLen}
          ariaLabel={t("onboarding.field.cycleLen")}
        />
      </Field>

      <Field label={t("onboarding.field.periodLen")} htmlFor="periodLen">
        <Slider
          value={periodLen}
          min={2}
          max={10}
          unit={t("onboarding.q3.unit")}
          onChange={setPeriodLen}
          ariaLabel={t("onboarding.field.periodLen")}
        />
      </Field>

      <label className="flex items-start gap-3 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-1 h-5 w-5 accent-[color:var(--accent)]"
        />
        <span className="text-[14px]">{t("consent.confirm")}</span>
      </label>

      {error && (
        <div
          role="alert"
          className="rounded-[var(--radius)] bg-[color:var(--error-bg,#f8d7d5)] p-3 text-[14px] text-[color:var(--error,#8a1c1c)]"
        >
          {error}
        </div>
      )}

      <div className="mt-auto">
        <Button size="lg" fullWidth onClick={submit} disabled={busy}>
          {busy ? t("action.saving") : t("onboarding.submit")}
        </Button>
      </div>
    </div>
  );
}
