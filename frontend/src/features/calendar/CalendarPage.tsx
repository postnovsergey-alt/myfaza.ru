import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError, type CalendarOut, type Cycle } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { t } from "@/i18n";

import { LogSheet } from "@/features/logs/LogSheet";

function monthLabel(y: number, m: number): string {
  const raw = new Intl.DateTimeFormat("ru", { month: "long", year: "numeric" })
    .format(new Date(y, m - 1, 1))
    .replace(/\s*г\.$/, "");
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function shift(y: number, m: number, delta: number): { y: number; m: number } {
  const t = new Date(y, m - 1 + delta, 1);
  return { y: t.getFullYear(), m: t.getMonth() + 1 };
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(iso: string): string {
  return new Intl.DateTimeFormat("ru", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(iso + "T00:00:00Z"));
}

const RU_WEEKDAYS = ["П", "В", "С", "Ч", "П", "С", "В"];

type Intent = "mark-start" | "mark-end" | null;

export function CalendarPage() {
  const now = new Date();
  const [y, setY] = useState(now.getFullYear());
  const [m, setM] = useState(now.getMonth() + 1);
  const [selected, setSelected] = useState<string | null>(null);

  const [params, setParams] = useSearchParams();
  const rawIntent = params.get("intent");
  const intent: Intent =
    rawIntent === "mark-start" || rawIntent === "mark-end" ? rawIntent : null;

  const [pendingDate, setPendingDate] = useState<string | null>(null);
  const [intentError, setIntentError] = useState<string | null>(null);

  const qc = useQueryClient();
  const navigate = useNavigate();

  const monthKey = `${y}-${String(m).padStart(2, "0")}`;
  const data = useQuery({
    queryKey: ["calendar", monthKey],
    queryFn: () =>
      api.get<CalendarOut>(`/predictions/calendar?month=${monthKey}`),
    staleTime: 30_000,
  });

  const clearIntent = () => {
    setPendingDate(null);
    setIntentError(null);
    setParams({}, { replace: true });
  };

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["prediction"] });
    qc.invalidateQueries({ queryKey: ["calendar"] });
    qc.invalidateQueries({ queryKey: ["cycle-for-date"] });
  };

  const markStart = useMutation({
    mutationFn: async (date: string) => {
      await api.post<Cycle>("/cycles", { start_date: date, source: "web" });
    },
    onSuccess: () => {
      invalidateAll();
      clearIntent();
      navigate("/", { replace: true });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "CYCLE_OVERLAP") {
        setIntentError(t("calendar.intent.error.overlap"));
      } else {
        setIntentError(t("calendar.intent.error.generic"));
      }
    },
  });

  const markEnd = useMutation({
    mutationFn: async (date: string) => {
      await api.post<Cycle>("/cycles/current/end", { end_date: date });
    },
    onSuccess: () => {
      invalidateAll();
      clearIntent();
      navigate("/", { replace: true });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "NO_OPEN_CYCLE") {
        setIntentError(t("calendar.intent.error.no_open"));
      } else {
        setIntentError(t("calendar.intent.error.generic"));
      }
    },
  });

  const onDayClick = (dateIso: string) => {
    // Обычный режим — открываем sheet с симптомами/удалением
    if (!intent) {
      setSelected(dateIso);
      return;
    }
    // Intent-режим: проверяем дату и открываем confirm
    if (dateIso > todayISO()) {
      setIntentError(t("calendar.intent.future"));
      return;
    }
    setIntentError(null);
    setPendingDate(dateIso);
  };

  const confirmIntent = () => {
    if (!pendingDate || !intent) return;
    if (intent === "mark-start") markStart.mutate(pendingDate);
    else markEnd.mutate(pendingDate);
  };

  // Первый день месяца — понедельник = 1
  const first = new Date(y, m - 1, 1);
  const firstDow = (first.getDay() + 6) % 7;

  const days = data.data?.days ?? [];
  const isBusy = markStart.isPending || markEnd.isPending;

  return (
    <div className="flex flex-col gap-4">
      {intent && (
        <div className="sticky top-0 z-10 -mx-4 flex flex-col gap-2 border-b border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3">
          <div className="text-[15px] font-medium">
            {t(
              intent === "mark-start"
                ? "calendar.intent.start.title"
                : "calendar.intent.end.title",
            )}
          </div>
          <div className="text-[13px] text-[color:var(--text-soft)]">
            {t(
              intent === "mark-start"
                ? "calendar.intent.start.body"
                : "calendar.intent.end.body",
            )}
          </div>
          {intentError && (
            <div
              role="alert"
              className="rounded-[var(--radius-sm)] bg-[color:var(--error-bg,#f8d7d5)] p-2 text-[13px] text-[color:var(--error,#8a1c1c)]"
            >
              {intentError}
            </div>
          )}
          <div className="flex justify-end">
            <Button variant="ghost" size="md" onClick={clearIntent}>
              {t("calendar.intent.cancel")}
            </Button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="md"
          aria-label={t("calendar.prev")}
          onClick={() => {
            const s = shift(y, m, -1);
            setY(s.y); setM(s.m);
          }}
        >
          ‹
        </Button>
        <h1 className="text-[17px] font-medium">{monthLabel(y, m)}</h1>
        <Button
          variant="ghost"
          size="md"
          aria-label={t("calendar.next")}
          onClick={() => {
            const s = shift(y, m, 1);
            setY(s.y); setM(s.m);
          }}
        >
          ›
        </Button>
      </div>

      <div
        className="grid grid-cols-7 gap-1 text-center text-[11px] text-[color:var(--text-soft)]"
        aria-hidden
      >
        {RU_WEEKDAYS.map((d, i) => <div key={i}>{d}</div>)}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: firstDow }).map((_, i) => (
          <div key={`e${i}`} />
        ))}
        {days.map((d) => (
          <DayCell
            key={d.date}
            date={d.date}
            state={d.state}
            hasLog={d.has_log}
            isToday={d.is_today}
            cycleDay={d.cycle_day}
            onOpen={() => onDayClick(d.date)}
          />
        ))}
      </div>

      <Legend />

      <p className="text-[11px] text-[color:var(--text-soft)] mt-2">
        {t("calendar.disclaimer")}
      </p>

      {/* Обычный режим — LogSheet за день */}
      <LogSheet
        open={!intent && selected !== null}
        date={selected}
        onClose={() => setSelected(null)}
      />

      {/* Intent-режим — confirm-Sheet */}
      <Sheet
        open={!!pendingDate}
        onClose={() => setPendingDate(null)}
        title={t(
          intent === "mark-end"
            ? "calendar.intent.confirm.end.title"
            : "calendar.intent.confirm.start.title",
        )}
      >
        {pendingDate && (
          <div className="mb-3 text-[14px]">{fmtDate(pendingDate)}</div>
        )}
        <div className="flex flex-col gap-2">
          <Button size="lg" fullWidth onClick={confirmIntent} disabled={isBusy}>
            {isBusy ? t("action.saving") : t("calendar.intent.confirm.yes")}
          </Button>
          <Button
            variant="ghost"
            size="lg"
            fullWidth
            onClick={() => setPendingDate(null)}
            disabled={isBusy}
          >
            {t("calendar.intent.confirm.no")}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}

function DayCell(props: {
  date: string;
  state: "period_actual" | "period_predicted" | "fertile" | "ovulation" | "normal";
  hasLog: boolean;
  isToday: boolean;
  cycleDay: number | null;
  onOpen: () => void;
}) {
  const { date, state, hasLog, isToday, onOpen } = props;
  const day = Number(date.slice(8, 10));

  let cls = "text-[color:var(--text)] bg-transparent";
  let borderCls = "";
  if (state === "period_actual") {
    cls = "bg-[color:var(--accent)] text-[color:var(--on-accent)]";
  } else if (state === "period_predicted") {
    cls = "bg-transparent text-[color:var(--text)]";
    borderCls =
      "border-[1.5px] border-dashed border-[color:var(--accent)]";
  } else if (state === "fertile") {
    cls = "bg-[color:var(--second-soft)] text-[color:var(--text)]";
  }

  return (
    <button
      onClick={onOpen}
      className={[
        "relative aspect-square rounded-[10px] flex items-center justify-center",
        "text-[14px] transition-colors",
        cls,
        borderCls,
        isToday ? "outline outline-2 outline-[color:var(--border-strong)]" : "",
      ].join(" ")}
      aria-label={`${day}, ${state}`}
    >
      <span>{day}</span>
      {state === "ovulation" && (
        <span className="absolute bottom-1 h-1.5 w-1.5 rounded-full bg-[color:var(--second-dark)]" />
      )}
      {hasLog && state !== "ovulation" && (
        <span className="absolute bottom-1 h-1.5 w-1.5 rounded-full bg-[color:var(--text-soft)]" />
      )}
    </button>
  );
}

function Legend() {
  const items = [
    { key: "calendar.legend.actual",     style: "bg-[color:var(--accent)]" },
    { key: "calendar.legend.predicted",  style: "bg-transparent border-[1.5px] border-dashed border-[color:var(--accent)]" },
    { key: "calendar.legend.fertile",    style: "bg-[color:var(--second-soft)]" },
    { key: "calendar.legend.ovulation",  style: "bg-[color:var(--second-dark)]" },
  ];
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-[12px] text-[color:var(--text-soft)]">
      {items.map((it) => (
        <li key={it.key} className="flex items-center gap-2">
          <span className={["inline-block h-3 w-3 rounded-full", it.style].join(" ")} />
          <span>{t(it.key)}</span>
        </li>
      ))}
    </ul>
  );
}
