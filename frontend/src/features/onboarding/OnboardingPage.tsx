import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, type Cycle, type PredictionOut, type UserOut } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";
import { Slider } from "./Slider";

const TODAY = new Date().toISOString().slice(0, 10);
const TOTAL_STEPS = 4;

function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function fmtDate(iso: string): string {
  return new Intl.DateTimeFormat("ru", {
    day: "numeric",
    month: "long",
  }).format(new Date(iso + "T00:00:00Z"));
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const setUser = useAuth((s) => s.setUser);

  const [step, setStep] = useState(0);
  const [consent, setConsent] = useState(false);
  const [lastStart, setLastStart] = useState<string>(TODAY);
  const [cycleLen, setCycleLen] = useState(28);
  const [periodLen, setPeriodLen] = useState(5);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<PredictionOut | null>(null);

  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const finish = async () => {
    setBusy(true);
    try {
      // 1) Согласие
      await api.post("/auth/consent", { version: "1.0" });
      // 2) Настройки цикла
      await api.patch("/settings", {
        avg_cycle_length: cycleLen,
        avg_period_length: periodLen,
      }).catch(() => {}); // эндпоинт /settings появится в спринте 6 — не блокируем
      // 3) Первый цикл — от даты, введённой пользовательницей
      await api.post<Cycle>("/cycles", {
        start_date: lastStart,
        source: "web",
      });
      // 4) Прогноз для превью
      const p = await api.get<PredictionOut>("/predictions/next");
      setPreview(p);
      // Отметим onboarding_completed на клиенте — бэкенд обновит при первом
      // изменении user (спринт 6 добавит эндпоинт PATCH /me)
      const state = useAuth.getState();
      if (state.user) {
        setUser({ ...state.user, onboarding_completed: true } as UserOut);
      }
      setStep(TOTAL_STEPS - 1);
    } finally {
      setBusy(false);
    }
  };

  const canProceed =
    (step === 0 && consent) || step === 1 || step === 2 || step === 3;

  return (
    <div className="flex min-h-[80vh] flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="text-[13px] text-[color:var(--text-soft)]">
          {t("onboarding.step", { n: step + 1, total: TOTAL_STEPS })}
        </div>
        <Dots current={step} total={TOTAL_STEPS} />
      </div>

      {step === 0 && (
        <div className="flex flex-1 flex-col gap-4">
          <h1>{t("consent.title")}</h1>
          <p className="text-[color:var(--text-soft)]">{t("consent.body")}</p>
          <label className="mt-2 flex items-start gap-3 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-1 h-5 w-5 accent-[color:var(--accent)]"
            />
            <span className="text-[14px]">{t("consent.confirm")}</span>
          </label>
        </div>
      )}

      {step === 1 && (
        <div className="flex flex-1 flex-col gap-6">
          <h1>{t("onboarding.q1.title")}</h1>
          <Field label="" htmlFor="lastStart" help={t("onboarding.q1.help")}>
            <Input
              id="lastStart"
              type="date"
              max={TODAY}
              value={lastStart}
              onChange={(e) => setLastStart(e.target.value)}
            />
          </Field>
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-1 flex-col gap-6">
          <h1>{t("onboarding.q2.title")}</h1>
          <Slider
            value={cycleLen}
            min={21}
            max={40}
            unit={t("onboarding.q2.unit")}
            onChange={setCycleLen}
            ariaLabel={t("onboarding.q2.title")}
          />
          <Slider
            value={periodLen}
            min={2}
            max={10}
            unit={t("onboarding.q3.unit")}
            onChange={setPeriodLen}
            ariaLabel={t("onboarding.q3.title")}
          />
          <p className="text-[13px] text-[color:var(--text-soft)]">
            {t("onboarding.q3.title")}
          </p>
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-1 flex-col gap-4">
          <h1>{t("onboarding.q4.title")}</h1>
          <p className="text-[color:var(--text-soft)]">
            {t("onboarding.q4.body", {
              date: preview
                ? fmtDate(preview.predicted_start)
                : fmtDate(addDays(lastStart, cycleLen)),
            })}
          </p>
        </div>
      )}

      <div className="mt-auto flex flex-col gap-2">
        {step === 0 && (
          <Button size="lg" fullWidth disabled={!canProceed} onClick={next}>
            {t("consent.continue")}
          </Button>
        )}
        {step === 1 && (
          <div className="flex gap-2">
            <Button variant="ghost" size="lg" onClick={back}>
              {t("onboarding.back")}
            </Button>
            <Button size="lg" fullWidth onClick={next}>
              {t("onboarding.next")}
            </Button>
          </div>
        )}
        {step === 2 && (
          <div className="flex gap-2">
            <Button variant="ghost" size="lg" onClick={back}>
              {t("onboarding.back")}
            </Button>
            <Button size="lg" fullWidth onClick={finish} disabled={busy}>
              {busy ? t("action.saving") : t("onboarding.next")}
            </Button>
          </div>
        )}
        {step === 3 && (
          <Button size="lg" fullWidth onClick={() => navigate("/", { replace: true })}>
            {t("onboarding.start")}
          </Button>
        )}
      </div>
    </div>
  );
}

function Dots({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex gap-1.5" aria-hidden>
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={[
            "h-1.5 w-1.5 rounded-full transition-colors",
            i <= current
              ? "bg-[color:var(--accent)]"
              : "bg-[color:var(--border)]",
          ].join(" ")}
        />
      ))}
    </div>
  );
}
