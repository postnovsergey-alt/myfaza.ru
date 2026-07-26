import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { haptic } from "@/platform";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
  fullWidth?: boolean;
}

const base =
  "inline-flex items-center justify-center gap-2 select-none " +
  "font-medium transition-[transform,background,color] " +
  "active:scale-[0.975] disabled:opacity-50 disabled:cursor-not-allowed";

const sizes: Record<Size, string> = {
  md: "min-h-[44px] px-4 py-2 rounded-[var(--radius)] text-[15px]",
  lg: "min-h-[52px] px-6 py-3 rounded-[var(--radius)] text-[16px]",
};

// Все цвета из CSS-переменных дизайн-системы, чтобы Tailwind
// не тянул свою палитру.
const variants: Record<Variant, string> = {
  primary:
    "bg-[color:var(--accent)] text-[color:var(--on-accent)] hover:bg-[color:var(--accent-hi)]",
  secondary:
    "bg-[color:var(--surface-alt)] text-[color:var(--text)] " +
    "hover:bg-[color:var(--border)]",
  ghost:
    "bg-transparent text-[color:var(--text)] hover:bg-[color:var(--surface-alt)]",
  danger:
    "bg-transparent text-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]",
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "primary", size = "md", fullWidth, className = "", children, onClick, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        onClick={(e) => {
          haptic("tap");
          onClick?.(e);
        }}
        className={[
          base,
          sizes[size],
          variants[variant],
          fullWidth ? "w-full" : "",
          "duration-[var(--dur-instant)] ease-[cubic-bezier(0.22,1,0.36,1)]",
          className,
        ].join(" ")}
        {...rest}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
