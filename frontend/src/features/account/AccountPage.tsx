import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";

interface Me {
  id: string;
  display_name: string | null;
  timezone: string;
  locale: string;
  auth_methods: {
    telegram: { linked: boolean; username: string | null };
    email: { linked: boolean; address: string | null; verified: boolean };
    password_set: boolean;
  };
  consent: { given_at: string | null; version: string | null };
  cycle_status: {
    current_cycle_day: number | null;
    days_until_period: number | null;
    is_overdue: boolean;
  };
}

interface SessionRow {
  id: string;
  channel: string;
  device_label: string | null;
  last_used_at: string | null;
  created_at: string;
}

export function AccountPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const logout = useAuth((s) => s.logout);

  const me = useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/me") });
  const sessions = useQuery({
    queryKey: ["me-sessions"],
    queryFn: () => api.get<SessionRow[]>("/me/sessions"),
  });

  const [displayName, setDisplayName] = useState<string>("");

  const patchMe = useMutation({
    mutationFn: (body: Partial<Me>) => api.patch<Me>("/me", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });

  const revokeSession = useMutation({
    mutationFn: (id: string) => api.del(`/me/sessions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me-sessions"] }),
  });

  const revokeAll = useMutation({
    mutationFn: () => api.del("/me/sessions"),
    onSuccess: () => {
      logout();
      navigate("/login", { replace: true });
    },
  });

  const revokeConsent = useMutation({
    mutationFn: () => api.post("/account/consent/revoke"),
    onSuccess: () => {
      logout();
      navigate("/login", { replace: true });
    },
  });

  const deleteAccount = useMutation({
    mutationFn: () =>
      api.del("/account", { confirm: "DELETE" }),
    onSuccess: () => {
      logout();
      navigate("/login", { replace: true });
    },
  });

  const exportJson = () => {
    // Открываем экспорт в новой вкладке — сервер вернёт файл с attachment
    window.location.href = "/api/v1/export?format=json";
  };

  if (me.isLoading || !me.data) {
    return <div className="pt-20 text-center text-[color:var(--text-soft)]">{t("action.loading")}</div>;
  }

  const u = me.data;

  return (
    <div className="flex flex-col gap-6">
      <h1>{t("account.title")}</h1>

      <Section title={t("account.profile")}>
        <Field label={t("account.display_name")} htmlFor="name">
          <Input
            id="name"
            defaultValue={u.display_name ?? ""}
            onChange={(e) => setDisplayName(e.target.value)}
            onBlur={() => {
              if (displayName && displayName !== u.display_name) {
                patchMe.mutate({ display_name: displayName } as Partial<Me>);
              }
            }}
          />
        </Field>
        <Field label={t("account.timezone")} htmlFor="tz">
          <Input
            id="tz"
            defaultValue={u.timezone}
            onBlur={(e) => {
              const v = e.target.value.trim();
              if (v && v !== u.timezone) {
                patchMe.mutate({ timezone: v } as Partial<Me>);
              }
            }}
          />
        </Field>
      </Section>

      <Section title={t("account.login_methods")}>
        <div className="rounded-[var(--radius)] bg-[color:var(--surface)] p-3 text-[14px]">
          <div className="mb-2 flex items-center justify-between">
            <span>Telegram</span>
            <span className="text-[color:var(--text-soft)]">
              {u.auth_methods.telegram.linked
                ? "@" + (u.auth_methods.telegram.username ?? "linked")
                : "—"}
            </span>
          </div>
          <div className="mb-2 flex items-center justify-between">
            <span>Email</span>
            <span className="text-[color:var(--text-soft)]">
              {u.auth_methods.email.address ?? "—"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>{t("account.password.change")}</span>
            <span className="text-[color:var(--text-soft)]">
              {u.auth_methods.password_set ? "✓" : "—"}
            </span>
          </div>
        </div>
      </Section>

      <Section title={t("account.sessions")}>
        <div className="flex flex-col gap-2">
          {sessions.data?.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded-[var(--radius-sm)] bg-[color:var(--surface)] p-3 text-[13px]"
            >
              <div>
                <div>{s.device_label ?? s.channel}</div>
                <div className="text-[11px] text-[color:var(--text-soft)]">
                  {s.last_used_at ?? s.created_at}
                </div>
              </div>
              <Button
                variant="ghost"
                size="md"
                onClick={() => revokeSession.mutate(s.id)}
              >
                {t("account.sessions.end")}
              </Button>
            </div>
          ))}
          <Button
            variant="danger"
            size="md"
            onClick={() => {
              if (confirm(t("confirm.logout.all"))) revokeAll.mutate();
            }}
          >
            {t("account.sessions.end.all")}
          </Button>
        </div>
      </Section>

      <Section title={t("settings.privacy")}>
        <div className="flex flex-col gap-2">
          <Button variant="ghost" size="md" onClick={exportJson}>
            {t("settings.export")}
          </Button>
          <Button variant="ghost" size="md" onClick={() => navigate("/privacy")}>
            {t("privacy.title")}
          </Button>
          <Button
            variant="danger"
            size="md"
            onClick={() => {
              if (confirm(t("confirm.revoke.consent"))) revokeConsent.mutate();
            }}
          >
            {t("settings.consent.revoke")}
          </Button>
          <Button
            variant="danger"
            size="md"
            onClick={() => {
              if (confirm(t("confirm.delete.account"))) deleteAccount.mutate();
            }}
          >
            {t("settings.delete")}
          </Button>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-[15px] font-medium">{title}</h2>
      {children}
    </div>
  );
}
