import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, type TokenResponse } from "@/api/client";
import { t } from "@/i18n";
import { getInitData } from "@/platform";
import { useAuth } from "@/store/auth";

/**
 * В Telegram Mini App логин происходит автоматически: initData → JWT.
 * На вебе initData нет — просто редирект на /login.
 */
export function TelegramGate() {
  const setSession = useAuth((s) => s.setSession);
  const navigate = useNavigate();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const initData = getInitData();
    if (!initData) {
      navigate("/login", { replace: true });
      return;
    }
    (async () => {
      try {
        const r = await api.post<TokenResponse>("/auth/telegram", {
          init_data: initData,
        });
        setSession(r);
        navigate(r.user.onboarding_completed ? "/" : "/onboarding", {
          replace: true,
        });
      } catch {
        setErr(t("error.generic"));
      }
    })();
  }, [navigate, setSession]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center text-[color:var(--text-soft)]">
      {err ?? t("action.loading")}
    </div>
  );
}
