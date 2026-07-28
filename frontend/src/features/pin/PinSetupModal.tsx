import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";
import { haptic } from "@/platform";
import { usePin } from "@/store/pin";

import { PIN_LENGTH, setPin } from "./pinStorage";

type Step = "first" | "confirm" | "done";

interface Props {
  onClose: () => void;
}

/**
 * Двухшаговая установка ПИНа: ввод → повтор. Если совпало — сохраняем
 * хеш и закрываем. Если нет — сбрасываем на первый шаг.
 */
export function PinSetupModal({ onClose }: Props) {
  const refresh = usePin((s) => s.refresh);
  const [step, setStep] = useState<Step>("first");
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const current = step === "confirm" ? second : first;

  const submitSecond = useCallback(async () => {
    if (second !== first) {
      haptic("warning");
      setErr(t("pin.setup.mismatch"));
      setFirst("");
      setSecond("");
      setStep("first");
      return;
    }
    await setPin(first);
    refresh();
    haptic("success");
    setStep("done");
    onClose();
  }, [first, onClose, refresh, second]);

  useEffect(() => {
    if (step === "first" && first.length === PIN_LENGTH) {
      setErr(null);
      setStep("confirm");
    }
  }, [first, step]);

  useEffect(() => {
    if (step === "confirm" && second.length === PIN_LENGTH) {
      void submitSecond();
    }
  }, [second, step, submitSecond]);

  const press = (d: string) => {
    if (current.length >= PIN_LENGTH) return;
    haptic("tap");
    if (step === "first") setFirst(first + d);
    else setSecond(second + d);
  };
  const back = () => {
    haptic("tap");
    if (step === "first") setFirst(first.slice(0, -1));
    else setSecond(second.slice(0, -1));
  };

  return (
    <div className="fixed inset-0 z-[110] flex flex-col items-center justify-center gap-8 bg-[color:var(--bg)] px-6">
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-[20px] font-medium">
          {step === "confirm" ? t("pin.setup.confirm") : t("pin.setup.enter")}
        </h1>
        {err && (
          <p className="text-[13px] text-[color:var(--accent)]">{err}</p>
        )}
      </div>

      <div className="flex gap-3">
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <span
            key={i}
            className={[
              "h-4 w-4 rounded-full border-[1.5px] transition-colors",
              i < current.length
                ? "border-[color:var(--accent)] bg-[color:var(--accent)]"
                : "border-[color:var(--border-strong)]",
            ].join(" ")}
          />
        ))}
      </div>

      <div className="grid w-full max-w-[260px] grid-cols-3 gap-3">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => press(d)}
            className="min-h-[56px] rounded-[var(--radius)] bg-[color:var(--surface-alt)] text-[22px] active:bg-[color:var(--surface)]"
          >
            {d}
          </button>
        ))}
        <span />
        <button
          type="button"
          onClick={() => press("0")}
          className="min-h-[56px] rounded-[var(--radius)] bg-[color:var(--surface-alt)] text-[22px] active:bg-[color:var(--surface)]"
        >
          0
        </button>
        <button
          type="button"
          onClick={back}
          className="min-h-[56px] rounded-[var(--radius)] bg-[color:var(--surface-alt)] text-[22px] active:bg-[color:var(--surface)]"
        >
          ←
        </button>
      </div>

      <Button variant="ghost" size="md" onClick={onClose}>
        {t("pin.setup.cancel")}
      </Button>
    </div>
  );
}
