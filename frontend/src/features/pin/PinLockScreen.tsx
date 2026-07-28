import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { t } from "@/i18n";
import { haptic } from "@/platform";
import { useAuth } from "@/store/auth";
import { usePin } from "@/store/pin";

import {
  attemptsLeft,
  clearBackgrounded,
  clearPin,
  MAX_ATTEMPTS,
  PIN_LENGTH,
  verifyPin,
} from "./pinStorage";

/**
 * Экран блокировки: показывается поверх приложения, когда usePin.locked === true.
 * 4 клетки, цифропад 0–9, backspace. 5 промахов → сбрасываем ПИН и
 * выкидываем на форму входа паролем.
 */
export function PinLockScreen() {
  const unlock = usePin((s) => s.unlock);
  const refresh = usePin((s) => s.refresh);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();

  const [pin, setPin] = useState("");
  const [shake, setShake] = useState(false);
  const [left, setLeft] = useState(attemptsLeft());

  const submit = useCallback(
    async (value: string) => {
      const ok = await verifyPin(value);
      if (ok) {
        clearBackgrounded();
        setPin("");
        unlock();
        haptic("success");
        return;
      }
      haptic("warning");
      const leftNow = attemptsLeft();
      setLeft(leftNow);
      if (leftNow <= 0) {
        clearPin();
        refresh();
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setShake(true);
      window.setTimeout(() => {
        setShake(false);
        setPin("");
      }, 320);
    },
    [logout, navigate, refresh, unlock],
  );

  useEffect(() => {
    if (pin.length === PIN_LENGTH) void submit(pin);
  }, [pin, submit]);

  const press = (d: string) => {
    if (pin.length >= PIN_LENGTH) return;
    haptic("tap");
    setPin(pin + d);
  };
  const back = () => {
    if (!pin) return;
    haptic("tap");
    setPin(pin.slice(0, -1));
  };

  const forgot = () => {
    clearPin();
    refresh();
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-8 bg-[color:var(--bg)] px-6">
      <div className="flex flex-col items-center gap-2">
        <h1 className="text-[20px] font-medium">{t("pin.title")}</h1>
        <p className="text-[13px] text-[color:var(--text-soft)]">
          {left < MAX_ATTEMPTS
            ? t("pin.attempts_left", { n: left })
            : t("pin.enter")}
        </p>
      </div>

      <div
        className={[
          "flex gap-3",
          shake ? "animate-[pin-shake_0.32s_cubic-bezier(0.36,0.07,0.19,0.97)]" : "",
        ].join(" ")}
      >
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <span
            key={i}
            className={[
              "h-4 w-4 rounded-full border-[1.5px] transition-colors",
              i < pin.length
                ? "border-[color:var(--accent)] bg-[color:var(--accent)]"
                : "border-[color:var(--border-strong)]",
            ].join(" ")}
          />
        ))}
      </div>

      <div className="grid w-full max-w-[260px] grid-cols-3 gap-3">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
          <PadButton key={d} onClick={() => press(d)}>
            {d}
          </PadButton>
        ))}
        <span />
        <PadButton onClick={() => press("0")}>0</PadButton>
        <PadButton onClick={back} aria-label={t("pin.backspace")}>←</PadButton>
      </div>

      <button
        onClick={forgot}
        className="text-[13px] text-[color:var(--text-soft)] underline underline-offset-2"
      >
        {t("pin.forgot")}
      </button>

      <style>{`@keyframes pin-shake {
        10%, 90% { transform: translateX(-2px); }
        20%, 80% { transform: translateX(4px); }
        30%, 50%, 70% { transform: translateX(-8px); }
        40%, 60% { transform: translateX(8px); }
      }`}</style>
    </div>
  );
}

function PadButton({
  children,
  onClick,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-[56px] rounded-[var(--radius)] bg-[color:var(--surface-alt)] text-[22px] text-[color:var(--text)] transition-colors active:bg-[color:var(--surface)]"
      {...rest}
    >
      {children}
    </button>
  );
}
