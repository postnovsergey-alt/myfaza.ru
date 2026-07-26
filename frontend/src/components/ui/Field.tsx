import type { InputHTMLAttributes, ReactNode } from "react";

interface FieldProps {
  label: string;
  help?: string;
  error?: string;
  children: ReactNode;
  htmlFor?: string;
}

export function Field({ label, help, error, children, htmlFor }: FieldProps) {
  const helpId = help ? `${htmlFor}-help` : undefined;
  const errId = error ? `${htmlFor}-err` : undefined;
  return (
    <label className="flex flex-col gap-1.5" htmlFor={htmlFor}>
      <span className="text-[13px] text-[color:var(--text-soft)]">{label}</span>
      <div aria-describedby={[helpId, errId].filter(Boolean).join(" ") || undefined}>
        {children}
      </div>
      {help && !error && (
        <span id={helpId} className="text-[13px] text-[color:var(--text-soft)]">
          {help}
        </span>
      )}
      {error && (
        <span
          id={errId}
          className="text-[13px] text-[color:var(--accent)]"
          role="alert"
        >
          {error}
        </span>
      )}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={[
        "w-full min-h-[44px] px-3 py-2",
        "bg-[color:var(--surface)] text-[color:var(--text)]",
        "border border-[color:var(--border)] rounded-[var(--radius-sm)]",
        "focus:border-[color:var(--accent)] outline-none",
        "placeholder:text-[color:var(--text-soft)]",
        props.className ?? "",
      ].join(" ")}
    />
  );
}
