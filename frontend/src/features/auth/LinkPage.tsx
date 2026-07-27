import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError, type TokenResponse } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";

/**
 * Публичный экран приёма ссылки `/link?token=<token>`, которую
 * пользователь получил в MiniApp через AccountPage → «Привязать
 * веб-доступ». Здесь задаётся email + пароль, они привязываются к
 * существующему TG-user'у, а на выходе — валидная веб-сессия.
 */
export function LinkPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErr(t("link.error.expired"));
      return;
    }
    setErr(null);
    setBusy(true);
    try {
      const r = await api.post<TokenResponse>("/auth/link/confirm", {
        token,
        email,
        password,
      });
      setSession(r);
      navigate("/", { replace: true });
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.code === "LINK_TOKEN_INVALID" || e.code === "LINK_TOKEN_EXPIRED" || e.code === "LINK_TOKEN_USED") {
          setErr(t("link.error.expired"));
        } else if (e.code === "EMAIL_ALREADY_USED") {
          setErr(t("link.error.email_used"));
        } else {
          setErr(t("link.error.generic"));
        }
      } else {
        setErr(t("link.error.generic"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] flex-col justify-center gap-6">
      <div>
        <h1 className="text-[22px] font-medium">{t("link.title")}</h1>
        <p className="mt-2 text-[color:var(--text-soft)]">{t("link.body")}</p>
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
          help={t("auth.password.hint")}
          error={err ?? undefined}
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        <Button type="submit" size="lg" fullWidth disabled={busy || !token}>
          {busy ? t("action.saving") : t("link.submit")}
        </Button>
      </form>
    </div>
  );
}
