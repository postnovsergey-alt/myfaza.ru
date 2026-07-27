import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError, type Cycle, type PredictionOut } from "@/api/client";
import { CycleRing } from "@/components/CycleRing";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { t } from "@/i18n";

function fmtDate(iso: string): string {
  return new Intl.DateTimeFormat("ru", {
    day: "numeric",
    month: "long",
  }).format(new Date(iso + "T00:00:00Z"));
}

const TODAY = () => new Date().toISOString().slice(0, 10);

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function HomePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [markOpen, setMarkOpen] = useState(false);
  const [endOpen, setEndOpen] = useState(false);

  const prediction = useQuery({
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

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["prediction"] });
    qc.invalidateQueries({ queryKey: ["calendar"] });
  };

  const mark = useMutation({
    mutationFn: async (date: string) => {
      await api.post<Cycle>("/cycles", { start_date: date, source: "web" });
    },
    onSuccess: () => {
      invalidate();
      setMarkOpen(false);
    },
  });

  const markEnd = useMutation({
    mutationFn: async (date: string) => {
      await api.post<Cycle>("/cycles/current/end", { end_date: date });
    },
    onSuccess: () => {
      invalidate();
      setEndOpen(false);
    },
  });

  if (prediction.isLoading) {
    return <div className="pt-20 text-center text-[color:var(--text-soft)]">{t("action.loading")}</div>;
  }

  if (!prediction.data) {
    // Нет циклов — редиректим на онбординг
    setTimeout(() => navigate("/onboarding", { replace: true }), 0);
    return null;
  }

  const p = prediction.data;
  const phaseTone = p.is_overdue ? "attention" : "normal";
  const phaseLabel = p.is_overdue
    ? t("home.overdue", { n: p.overdue_days })
    : t("home.until") + " " + t("home.days", { n: p.days_until_period });

  const confidenceHint =
    p.confidence === "low"
      ? t("home.confidence.low")
      : p.confidence === "medium"
      ? t("home.confidence.medium")
      : t("home.confidence.high");

  // Оценочная длина цикла для заполнения кольца
  const cycleLen = Math.max(p.current_cycle_day + p.days_until_period, 21);

  return (
    <div className="flex min-h-[70vh] flex-col items-stretch gap-6">
      <div className="pt-4">
        <CycleRing
          cycleDay={p.current_cycle_day}
          cycleLength={cycleLen}
          phaseLabel={phaseLabel}
          phaseTone={phaseTone}
          confidenceHint={confidenceHint}
        />
      </div>

      <div className="rounded-[var(--radius)] bg-[color:var(--surface)] p-4">
        <div className="text-[13px] text-[color:var(--text-soft)]">
          {t("home.expected", { date: fmtDate(p.predicted_start) })}
          {p.margin_days > 0 ? ` ± ${p.margin_days}` : ""}
        </div>
      </div>

      <div className="mt-auto flex flex-col gap-3">
        {p.is_period_active ? (
          <Button size="lg" fullWidth onClick={() => setEndOpen(true)}>
            {t("home.mark.end")}
          </Button>
        ) : (
          <Button size="lg" fullWidth onClick={() => setMarkOpen(true)}>
            {t("home.mark")}
          </Button>
        )}
      </div>

      <Sheet
        open={markOpen}
        onClose={() => setMarkOpen(false)}
        title={t("home.mark")}
      >
        <div className="flex flex-col gap-2">
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            onClick={() => mark.mutate(todayISO(0))}
            disabled={mark.isPending}
          >
            {t("home.today")} · {fmtDate(TODAY())}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            onClick={() => mark.mutate(todayISO(-1))}
            disabled={mark.isPending}
          >
            {t("home.yesterday")} · {fmtDate(todayISO(-1))}
          </Button>
          <Button
            variant="ghost"
            size="lg"
            fullWidth
            onClick={() => {
              setMarkOpen(false);
              navigate("/calendar");
            }}
          >
            {t("home.pick.date")}
          </Button>
        </div>
      </Sheet>

      <Sheet
        open={endOpen}
        onClose={() => setEndOpen(false)}
        title={t("home.mark.end.title")}
      >
        <div className="flex flex-col gap-2">
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            onClick={() => markEnd.mutate(todayISO(0))}
            disabled={markEnd.isPending}
          >
            {t("home.today")} · {fmtDate(TODAY())}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            onClick={() => markEnd.mutate(todayISO(-1))}
            disabled={markEnd.isPending}
          >
            {t("home.yesterday")} · {fmtDate(todayISO(-1))}
          </Button>
          <Button
            variant="ghost"
            size="lg"
            fullWidth
            onClick={() => {
              setEndOpen(false);
              navigate("/calendar");
            }}
          >
            {t("home.pick.date")}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}
