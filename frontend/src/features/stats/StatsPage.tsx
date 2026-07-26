import { useQuery } from "@tanstack/react-query";

import { api, type Cycle } from "@/api/client";
import { t } from "@/i18n";

/**
 * Экран аналитики. В этом спринте — только структура (три числа и
 * минимальный график). Полноценные графики добавит спринт 6.
 */
export function StatsPage() {
  const data = useQuery({
    queryKey: ["cycles"],
    queryFn: () => api.get<Cycle[]>("/cycles"),
    staleTime: 30_000,
  });

  const cycles = data.data ?? [];
  const withLen = cycles
    .map((c) => c.cycle_length)
    .filter((n): n is number => typeof n === "number");
  const avgLen = withLen.length
    ? Math.round(withLen.reduce((a, b) => a + b, 0) / withLen.length)
    : null;

  const periods = cycles
    .map((c) => c.period_length)
    .filter((n): n is number => typeof n === "number");
  const avgPeriod = periods.length
    ? Math.round(periods.reduce((a, b) => a + b, 0) / periods.length)
    : null;

  const sigma = withLen.length >= 2
    ? Math.round(stdev(withLen))
    : null;

  return (
    <div className="flex flex-col gap-6">
      <h1>{t("nav.stats")}</h1>
      <div className="grid grid-cols-3 gap-3">
        <Metric value={avgLen} label="Средняя длина" />
        <Metric value={avgPeriod} label="Длительность" />
        <Metric value={sigma} label="σ" />
      </div>
      <div className="rounded-[var(--radius)] bg-[color:var(--surface)] p-4">
        <div className="mb-3 text-[13px] text-[color:var(--text-soft)]">
          Последние {withLen.length} циклов
        </div>
        <MiniBar values={withLen.slice(-12)} />
      </div>
    </div>
  );
}

function Metric({ value, label }: { value: number | null; label: string }) {
  return (
    <div className="rounded-[var(--radius)] bg-[color:var(--surface)] p-3">
      <div className="text-[26px] font-medium tabular-nums">
        {value ?? "—"}
      </div>
      <div className="text-[11px] text-[color:var(--text-soft)]">{label}</div>
    </div>
  );
}

function MiniBar({ values }: { values: number[] }) {
  const max = Math.max(30, ...values);
  return (
    <div className="flex items-end gap-1 h-24">
      {values.length === 0 ? (
        <div className="text-[13px] text-[color:var(--text-soft)]">Пока пусто</div>
      ) : (
        values.map((v, i) => (
          <div
            key={i}
            className="flex-1 rounded-t-[6px] bg-[color:var(--accent)]"
            style={{ height: `${(v / max) * 100}%` }}
            aria-label={`${v} дней`}
          />
        ))
      )}
    </div>
  );
}

function stdev(values: number[]): number {
  const m = values.reduce((a, b) => a + b, 0) / values.length;
  const v =
    values.reduce((a, b) => a + (b - m) ** 2, 0) / (values.length - 1);
  return Math.sqrt(v);
}
