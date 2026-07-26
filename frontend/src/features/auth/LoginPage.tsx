import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, type TokenResponse } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";

type Mode = "login" | "register";

export function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const body: Record<string, string> = { email, password };
      if (mode === "register") body.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const r = await api.post<TokenResponse>(path, body);
      setSession(r);
      if (!r.user.onboarding_completed) navigate("/onboarding", { replace: true });
      else navigate("/", { replace: true });
    } catch (e) {
      const err = e as { code?: string };
      if (err.code === "INVALID_CREDENTIALS") setErr(t("auth.error.credentials"));
      else if (err.code === "EMAIL_ALREADY_USED") setErr(t("auth.error.dup"));
      else setErr(t("auth.error.generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] flex-col justify-center gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-[22px] font-medium">{t("app.name")}</h1>
        <p className="text-[13px] text-[color:var(--text-soft)]">{t("app.tagline")}</p>
      </div>

      <div className="flex rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-1">
        {(["login", "register"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={[
              "flex-1 rounded-[var(--radius-sm)] py-2 text-[14px] transition-colors",
              mode === m
                ? "bg-[color:var(--surface)] text-[color:var(--text)]"
                : "text-[color:var(--text-soft)]",
            ].join(" ")}
          >
            {t(m === "login" ? "auth.tab.login" : "auth.tab.register")}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t("auth.email")} htmlFor="email">
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field
          label={t("auth.password")}
          htmlFor="password"
          help={mode === "register" ? t("auth.password.hint") : undefined}
          error={err ?? undefined}
        >
          <Input
            id="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "register" ? 8 : 1}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        <Button type="submit" size="lg" fullWidth disabled={busy}>
          {t(mode === "login" ? "auth.login" : "auth.register")}
        </Button>
      </form>
    </div>
  );
}
