import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, type CalendarOut } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";

import { LogSheet } from "@/features/logs/LogSheet";

function monthLabel(y: number, m: number): string {
  // «июль 2026 г.» — Intl добавляет «г.», не всегда нужно; убираем его
  // и делаем первую букву заглавной вручную (Tailwind capitalize капит
  // ализирует каждое слово, «Июль 2026 Г.» — некрасиво).
  const raw = new Intl.DateTimeFormat("ru", { month: "long", year: "numeric" })
    .format(new Date(y, m - 1, 1))
    .replace(/\s*г\.$/, "");
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function shift(y: number, m: number, delta: number): { y: number; m: number } {
  const t = new Date(y, m - 1 + delta, 1);
  return { y: t.getFullYear(), m: t.getMonth() + 1 };
}

const RU_WEEKDAYS = ["П", "В", "С", "Ч", "П", "С", "В"];

export function CalendarPage() {
  const now = new Date();
  const [y, setY] = useState(now.getFullYear());
  const [m, setM] = useState(now.getMonth() + 1);
  const [selected, setSelected] = useState<string | null>(null);

  const monthKey = `${y}-${String(m).padStart(2, "0")}`;
  const data = useQuery({
    queryKey: ["calendar", monthKey],
    queryFn: () =>
      api.get<CalendarOut>(`/predictions/calendar?month=${monthKey}`),
    staleTime: 30_000,
  });

  // Первый день месяца — понедельник = 1
  const first = new Date(y, m - 1, 1);
  const firstDow = (first.getDay() + 6) % 7; // 0=Пн … 6=Вс

  const days = data.data?.days ?? [];

  return (
    <div className="flex flex-col gap-4">
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
            onOpen={() => setSelected(d.date)}
          />
        ))}
      </div>

      <Legend />

      <p className="text-[11px] text-[color:var(--text-soft)] mt-2">
        {t("calendar.disclaimer")}
      </p>

      <LogSheet
        open={selected !== null}
        date={selected}
        onClose={() => setSelected(null)}
      />
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

  // Стили ячейки — по разделу 2.1 DESIGN-SPEC.
  let cls = "text-[color:var(--text)] bg-transparent";
  let borderCls = "";
  if (state === "period_actual") {
    cls = "bg-[color:var(--accent)] text-[color:var(--on-accent)]";
  } else if (state === "period_predicted") {
    cls = "bg-transparent text-[color:var(--text)]";
    borderCls =
      "border-[1.5px] border-dashed border-[color:var(--accent)]";
  } else if (state === "fertile") {
    // 20% заливка = softer background
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
