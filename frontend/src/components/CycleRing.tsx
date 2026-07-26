/**
 * Кольцо цикла (главный экран). Крупная цифра — день цикла,
 * заполнение — доля прошедших дней от общего цикла.
 *
 * Никаких вспышек и «крутящихся» цифр (DESIGN-SPEC 3.3).
 * Единственная разрешённая длинная анимация — заполнение кольца
 * при первом появлении экрана (~900 мс).
 */

interface Props {
  cycleDay: number;
  cycleLength: number;
  phaseLabel: string;    // "До менструации 12 дней" или "Задержка 3 дня"
  phaseTone?: "normal" | "attention"; // цвет обводки: акцент или тонкая
  confidenceHint?: string;
}

const SIZE = 220;
const STROKE = 12;
const R = (SIZE - STROKE) / 2;
const C = 2 * Math.PI * R;

export function CycleRing({ cycleDay, cycleLength, phaseLabel, phaseTone = "normal", confidenceHint }: Props) {
  const fraction = Math.min(1, Math.max(0, cycleDay / cycleLength));
  const dash = C * fraction;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} className="rotate-[-90deg]">
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            stroke="var(--surface-alt)"
            strokeWidth={STROKE}
            fill="none"
          />
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            stroke={phaseTone === "attention" ? "var(--accent)" : "var(--accent)"}
            strokeWidth={STROKE}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${C - dash}`}
            style={{
              transition: "stroke-dasharray var(--dur-slow) var(--ease-out)",
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[13px] text-[color:var(--text-soft)]">
            День цикла
          </div>
          <div
            className="font-medium leading-none"
            style={{ fontSize: 44 }}
          >
            {cycleDay}
          </div>
        </div>
      </div>
      <div className="flex flex-col items-center gap-1">
        <div className="text-[15px] text-[color:var(--text)]">{phaseLabel}</div>
        {confidenceHint && (
          <div className="text-[13px] text-[color:var(--text-soft)]">
            {confidenceHint}
          </div>
        )}
      </div>
    </div>
  );
}
