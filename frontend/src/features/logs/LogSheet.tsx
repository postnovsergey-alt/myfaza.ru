import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, ApiError, type DailyLogRow } from "@/api/client";
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

export function LogSheet({ open, date, onClose }: Props) {
  const qc = useQueryClient();

  const existing = useQuery({
    queryKey: ["log", date],
    enabled: open && !!date,
    queryFn: async () => {
      if (!date) return null;
      try {
        // Нет отдельного /logs/{date} GET, но есть list с range —
        // берём диапазон одного дня.
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

  const [flow, setFlow] = useState<Flow | null>(null);
  const [mood, setMood] = useState<Mood | null>(null);
  const [symptoms, setSymptoms] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!open) return;
    const row = existing.data;
    setFlow((row?.flow as Flow | null) ?? null);
    setMood((row?.mood as Mood | null) ?? null);
    setSymptoms(new Set(row?.symptoms ?? []));
    setNote(row?.note ?? "");
  }, [open, existing.data]);

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
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: ["log"] });
      onClose();
    },
  });

  const toggle = (s: string) =>
    setSymptoms((old) => {
      const next = new Set(old);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });

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

      <SectionTitle>{t("log.flow")}</SectionTitle>
      <Grid>
        {FLOWS.map((f) => (
          <ChoicePill
            key={f}
            active={flow === f}
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
            onClick={() => setMood(mood === mo ? null : mo)}
          >
            {t(`log.mood.${mo}`)}
          </ChoicePill>
        ))}
      </Grid>

      <SectionTitle>{t("log.symptoms")}</SectionTitle>
      <Grid>
        {SYMPTOMS.map((s) => (
          <ChoicePill key={s} active={symptoms.has(s)} onClick={() => toggle(s)}>
            {t(`log.symptom.${s}`)}
          </ChoicePill>
        ))}
      </Grid>

      <SectionTitle>{t("log.note")}</SectionTitle>
      <textarea
        value={note}
        maxLength={500}
        onChange={(e) => setNote(e.target.value)}
        placeholder={t("log.note.placeholder")}
        className={[
          "w-full min-h-[96px] p-3 rounded-[var(--radius-sm)]",
          "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
          "border border-[color:var(--border)]",
          "focus:border-[color:var(--accent)] outline-none",
        ].join(" ")}
      />

      <div className="mt-4 flex gap-2">
        <Button variant="ghost" size="lg" onClick={onClose}>
          {t("log.cancel")}
        </Button>
        <Button
          size="lg"
          fullWidth
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? t("action.saving") : t("log.save")}
        </Button>
      </div>
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
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={props.onClick}
      className={[
        "min-h-[44px] px-3 rounded-[var(--radius-sm)] text-[14px] transition-colors",
        props.active
          ? "bg-[color:var(--accent)] text-[color:var(--on-accent)]"
          : "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
      ].join(" ")}
    >
      {props.children}
    </button>
  );
}
