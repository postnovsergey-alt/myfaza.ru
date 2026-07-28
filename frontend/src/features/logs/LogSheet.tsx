import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, ApiError, type Cycle, type DailyLogRow } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { t } from "@/i18n";

interface Props {
  open: boolean;
  date: string | null;
  onClose: () => void;
}

const FLOWS = ["spotting", "light", "medium", "heavy"] as const;
const MOODS = ["great", "good", "neutral", "low", "bad"] as const;
const SYMPTOMS = [
  "cramps", "headache", "bloating", "fatigue", "acne", "breast_tenderness",
] as const;

type Flow = (typeof FLOWS)[number];
type Mood = (typeof MOODS)[number];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function shiftISO(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function LogSheet({ open, date, onClose }: Props) {
  const qc = useQueryClient();
  const isFuture = !!date && date > todayISO();

  const existing = useQuery({
    queryKey: ["log", date],
    enabled: open && !!date,
    queryFn: async () => {
      if (!date) return null;
      try {
        const list = await api.get<DailyLogRow[]>(
          `/logs?from=${date}&to=${date}`,
        );
        return list.find((r) => r.date === date) ?? null;
      } catch (e) {
        if (e instanceof ApiError) return null;
        throw e;
      }
    },
  });

  // Ищем цикл, в диапазон которого попадает выбранная дата.
  // Окно назад ~45 дней — достаточно, чтобы поймать открытый цикл или
  // недавно закрытый; вперёд смотрим на 1 день, чтобы включить start-day.
  const cycleForDate = useQuery({
    queryKey: ["cycle-for-date", date],
    enabled: open && !!date && !isFuture,
    queryFn: async () => {
      if (!date) return null;
      const from = shiftISO(date, -45);
      const to = date;
      const list = await api.get<Cycle[]>(`/cycles?from=${from}&to=${to}`);
      // list — циклы, у которых start_date попал в [from..to]. Проверяем
      // покрытие: start_date <= date && (end_date IS NULL || end_date >= date).
      return (
        list.find(
          (c) =>
            c.start_date <= date &&
            (c.end_date === null || c.end_date >= date),
        ) ?? null
      );
    },
  });

  const [flow, setFlow] = useState<Flow | null>(null);
  const [mood, setMood] = useState<Mood | null>(null);
  const [symptoms, setSymptoms] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Локальный черновик дат цикла — заполняется, когда клик пришёл на
  // день из существующего цикла. Пустая строка в endDraft = «ещё идёт».
  const [startDraft, setStartDraft] = useState("");
  const [endDraft, setEndDraft] = useState("");
  const [cycleError, setCycleError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const row = existing.data;
    setFlow((row?.flow as Flow | null) ?? null);
    setMood((row?.mood as Mood | null) ?? null);
    setSymptoms(new Set(row?.symptoms ?? []));
    setNote(row?.note ?? "");
    setError(null);
  }, [open, existing.data]);

  useEffect(() => {
    if (!open) return;
    const cyc = cycleForDate.data;
    setStartDraft(cyc?.start_date ?? "");
    setEndDraft(cyc?.end_date ?? "");
    setCycleError(null);
  }, [open, cycleForDate.data]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["calendar"] });
    qc.invalidateQueries({ queryKey: ["log"] });
    qc.invalidateQueries({ queryKey: ["cycle-for-date"] });
    qc.invalidateQueries({ queryKey: ["prediction"] });
  };

  const save = useMutation({
    mutationFn: async () => {
      if (!date) return;
      await api.put(`/logs/${date}`, {
        flow,
        mood,
        symptoms: Array.from(symptoms),
        note: note || null,
      });
    },
    onSuccess: () => {
      invalidate();
      onClose();
    },
    onError: () => setError(t("log.delete.error")),
  });

  const deleteEntry = useMutation({
    mutationFn: async () => {
      if (!date) return;
      await api.del(`/logs/${date}`);
    },
    onSuccess: () => {
      invalidate();
      onClose();
    },
    onError: () => setError(t("log.delete.error")),
  });

  const deleteCycle = useMutation({
    mutationFn: async () => {
      const cyc = cycleForDate.data;
      if (!cyc) return;
      await api.del(`/cycles/${cyc.id}`);
    },
    onSuccess: () => {
      invalidate();
      onClose();
    },
    onError: () => setError(t("log.delete.error")),
  });

  const patchCycle = useMutation({
    mutationFn: async () => {
      const cyc = cycleForDate.data;
      if (!cyc) return;
      const body: { start_date?: string; end_date: string | null } = {
        end_date: endDraft || null,
      };
      if (startDraft && startDraft !== cyc.start_date) {
        body.start_date = startDraft;
      }
      await api.patch<Cycle>(`/cycles/${cyc.id}`, body);
    },
    onSuccess: () => {
      invalidate();
      setCycleError(null);
    },
    onError: (e) => {
      if (e instanceof ApiError) {
        const code = e.code;
        if (code === "CYCLE_OVERLAP") setCycleError(t("log.cycle.error.overlap"));
        else if (code === "CYCLE_END_BEFORE_START")
          setCycleError(t("log.cycle.error.end_before_start"));
        else if (code === "CYCLE_FUTURE") setCycleError(t("log.cycle.error.future"));
        else if (code === "CYCLE_TOO_OLD") setCycleError(t("log.cycle.error.too_old"));
        else setCycleError(t("log.cycle.error.generic"));
      } else {
        setCycleError(t("log.cycle.error.generic"));
      }
    },
  });

  const validateAndSaveCycle = () => {
    const cyc = cycleForDate.data;
    if (!cyc) return;
    if (!startDraft) {
      setCycleError(t("log.cycle.error.start_required"));
      return;
    }
    if (endDraft && endDraft < startDraft) {
      setCycleError(t("log.cycle.error.end_before_start"));
      return;
    }
    const today = todayISO();
    if (startDraft > today || (endDraft && endDraft > today)) {
      setCycleError(t("log.cycle.error.future"));
      return;
    }
    setCycleError(null);
    patchCycle.mutate();
  };

  const toggle = (s: string) =>
    setSymptoms((old) => {
      const next = new Set(old);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });

  const canDeleteEntry = !!existing.data;
  const canDeleteCycle = !!cycleForDate.data;

  return (
    <Sheet open={open} onClose={onClose} title={t("log.title")}>
      {date && (
        <div className="mb-3 text-[13px] text-[color:var(--text-soft)]">
          {new Intl.DateTimeFormat("ru", {
            weekday: "long",
            day: "numeric",
            month: "long",
          }).format(new Date(date + "T00:00:00Z"))}
        </div>
      )}

      {isFuture && (
        <div
          role="alert"
          className="mb-3 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3 text-[13px] text-[color:var(--text-soft)]"
        >
          {t("log.future.banner")}
        </div>
      )}

      <SectionTitle>{t("log.flow")}</SectionTitle>
      <Grid>
        {FLOWS.map((f) => (
          <ChoicePill
            key={f}
            active={flow === f}
            disabled={isFuture}
            onClick={() => setFlow(flow === f ? null : f)}
          >
            {t(`log.flow.${f}`)}
          </ChoicePill>
        ))}
      </Grid>

      <SectionTitle>{t("log.mood")}</SectionTitle>
      <Grid>
        {MOODS.map((mo) => (
          <ChoicePill
            key={mo}
            active={mood === mo}
            disabled={isFuture}
            onClick={() => setMood(mood === mo ? null : mo)}
          >
            {t(`log.mood.${mo}`)}
          </ChoicePill>
        ))}
      </Grid>

      <SectionTitle>{t("log.symptoms")}</SectionTitle>
      <Grid>
        {SYMPTOMS.map((s) => (
          <ChoicePill
            key={s}
            active={symptoms.has(s)}
            disabled={isFuture}
            onClick={() => toggle(s)}
          >
            {t(`log.symptom.${s}`)}
          </ChoicePill>
        ))}
      </Grid>

      <SectionTitle>{t("log.note")}</SectionTitle>
      <textarea
        value={note}
        maxLength={500}
        disabled={isFuture}
        onChange={(e) => setNote(e.target.value)}
        placeholder={t("log.note.placeholder")}
        className={[
          "w-full min-h-[96px] p-3 rounded-[var(--radius-sm)]",
          "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
          "border border-[color:var(--border)]",
          "focus:border-[color:var(--accent)] outline-none",
          isFuture ? "opacity-50" : "",
        ].join(" ")}
      />

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-[var(--radius)] bg-[color:var(--error-bg,#f8d7d5)] p-3 text-[13px] text-[color:var(--error,#8a1c1c)]"
        >
          {error}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <Button variant="ghost" size="lg" onClick={onClose}>
          {t("log.cancel")}
        </Button>
        <Button
          size="lg"
          fullWidth
          onClick={() => save.mutate()}
          disabled={save.isPending || isFuture}
        >
          {save.isPending ? t("action.saving") : t("log.save")}
        </Button>
      </div>

      {canDeleteCycle && !isFuture && (
        <div className="mt-6 flex flex-col gap-3 border-t border-[color:var(--border)] pt-4">
          <div className="text-[13px] text-[color:var(--text-soft)]">
            {t("log.cycle.title")}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="flex flex-1 flex-col gap-1 text-[12px] text-[color:var(--text-soft)]">
              <span>{t("log.cycle.start")}</span>
              <input
                type="date"
                value={startDraft}
                max={todayISO()}
                onChange={(e) => setStartDraft(e.target.value)}
                className="w-full rounded-[var(--radius-sm)] border border-[color:var(--border)] bg-[color:var(--surface-alt)] p-2 text-[14px] text-[color:var(--text)] focus:border-[color:var(--accent)] outline-none"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-[12px] text-[color:var(--text-soft)]">
              <span>{t("log.cycle.end")}</span>
              <input
                type="date"
                value={endDraft}
                min={startDraft || undefined}
                max={todayISO()}
                onChange={(e) => setEndDraft(e.target.value)}
                className="w-full rounded-[var(--radius-sm)] border border-[color:var(--border)] bg-[color:var(--surface-alt)] p-2 text-[14px] text-[color:var(--text)] focus:border-[color:var(--accent)] outline-none"
              />
            </label>
          </div>
          {endDraft && (
            <button
              type="button"
              onClick={() => setEndDraft("")}
              className="self-start text-[12px] text-[color:var(--text-soft)] underline underline-offset-2"
            >
              {t("log.cycle.end.clear")}
            </button>
          )}
          {cycleError && (
            <div
              role="alert"
              className="rounded-[var(--radius-sm)] bg-[color:var(--error-bg,#f8d7d5)] p-2 text-[13px] text-[color:var(--error,#8a1c1c)]"
            >
              {cycleError}
            </div>
          )}
          {(() => {
            const cyc = cycleForDate.data;
            const changed =
              !!cyc &&
              (startDraft !== cyc.start_date ||
                (endDraft || null) !== (cyc.end_date ?? null));
            return (
              <Button
                size="md"
                variant="secondary"
                onClick={validateAndSaveCycle}
                disabled={patchCycle.isPending || !changed}
              >
                {patchCycle.isPending
                  ? t("action.saving")
                  : t("log.cycle.save")}
              </Button>
            );
          })()}
        </div>
      )}

      {(canDeleteEntry || canDeleteCycle) && !isFuture && (
        <div className="mt-6 flex flex-col gap-2 border-t border-[color:var(--border)] pt-4">
          {canDeleteEntry && (
            <Button
              variant="ghost"
              size="md"
              onClick={() => {
                if (confirm(t("log.delete.entry.confirm"))) deleteEntry.mutate();
              }}
              disabled={deleteEntry.isPending}
            >
              {t("log.delete.entry")}
            </Button>
          )}
          {canDeleteCycle && (
            <Button
              variant="danger"
              size="md"
              onClick={() => {
                if (confirm(t("log.delete.cycle.confirm"))) deleteCycle.mutate();
              }}
              disabled={deleteCycle.isPending}
            >
              {t("log.delete.cycle")}
            </Button>
          )}
        </div>
      )}
    </Sheet>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 mt-4 text-[13px] text-[color:var(--text-soft)]">
      {children}
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap gap-1.5">{children}</div>;
}

function ChoicePill(props: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={props.onClick}
      disabled={props.disabled}
      className={[
        "min-h-[44px] px-3 rounded-[var(--radius-sm)] text-[14px] transition-colors",
        props.active
          ? "bg-[color:var(--accent)] text-[color:var(--on-accent)]"
          : "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
        props.disabled ? "opacity-50 cursor-not-allowed" : "",
      ].join(" ")}
    >
      {props.children}
    </button>
  );
}
