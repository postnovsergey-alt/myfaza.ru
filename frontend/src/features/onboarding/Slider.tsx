interface Props {
  value: number;
  min: number;
  max: number;
  unit: string;
  onChange: (n: number) => void;
  ariaLabel?: string;
}

export function Slider({ value, min, max, unit, onChange, ariaLabel }: Props) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="text-[44px] leading-none font-medium tabular-nums">
        {value}
        <span className="ml-2 text-[15px] text-[color:var(--text-soft)]">
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        aria-label={ariaLabel}
        onChange={(e) => onChange(Number(e.target.value))}
        className={[
          "w-full h-2 appearance-none rounded-full bg-[color:var(--surface-alt)]",
          "accent-[color:var(--accent)]",
        ].join(" ")}
      />
      <div className="flex w-full justify-between text-[11px] text-[color:var(--text-soft)]">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
