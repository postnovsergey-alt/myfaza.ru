import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Field, Input } from "@/components/ui/Field";
import { t } from "@/i18n";
import { useAuth } from "@/store/auth";

type ConfirmKind =
  | "delete-account"
  | "revoke-consent"
  | "logout-all"
  | "unlink-tg"
  | "unlink-email";

interface LinkOut {
  token: string;
  link_url: string;
  expires_at: string;
}

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
  const [linkWebUrl, setLinkWebUrl] = useState<string | null>(null);
  const [linkTgUrl, setLinkTgUrl] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const [confirmKind, setConfirmKind] = useState<ConfirmKind | null>(null);

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

  const linkWeb = useMutation({
    mutationFn: () => api.post<LinkOut>("/auth/link/create", { direction: "tg_to_web" }),
    onSuccess: (data) => {
      setLinkTgUrl(null);
      setLinkError(null);
      setLinkCopied(false);
      setLinkWebUrl(data.link_url);
    },
    onError: () => setLinkError(t("account.link.error")),
  });

  const linkTg = useMutation({
    mutationFn: () => api.post<LinkOut>("/auth/link/create", { direction: "web_to_tg" }),
    onSuccess: (data) => {
      setLinkWebUrl(null);
      setLinkError(null);
      setLinkTgUrl(data.link_url);
    },
    onError: () => setLinkError(t("account.link.error")),
  });

  const unlinkTg = useMutation({
    mutationFn: () => api.del("/me/telegram"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        alert(t("account.unlink.last"));
      }
    },
  });

  const unlinkEmail = useMutation({
    mutationFn: () => api.del("/me/email"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        alert(t("account.unlink.last"));
      }
    },
  });

  const copyLink = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      // clipboard может быть недоступен (не https/insecure context) —
      // хотя бы покажем URL текстом, чтобы пользователь скопировал руками
    }
  };

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
        <div className="flex flex-col gap-3 rounded-[var(--radius)] bg-[color:var(--surface)] p-3 text-[14px]">
          {/* Telegram row */}
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div>Telegram</div>
              <div className="text-[12px] text-[color:var(--text-soft)]">
                {u.auth_methods.telegram.linked
                  ? "@" + (u.auth_methods.telegram.username ?? t("account.telegram.linked"))
                  : "—"}
              </div>
            </div>
            {u.auth_methods.telegram.linked ? (
              <Button
                variant="ghost"
                size="md"
                onClick={() => setConfirmKind("unlink-tg")}
                disabled={unlinkTg.isPending}
              >
                {t("account.telegram.unlink")}
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="md"
                onClick={() => linkTg.mutate()}
                disabled={linkTg.isPending}
              >
                {t("account.telegram.link")}
              </Button>
            )}
          </div>

          {/* Email row */}
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div>Email</div>
              <div className="truncate text-[12px] text-[color:var(--text-soft)]">
                {u.auth_methods.email.address ?? "—"}
              </div>
            </div>
            {u.auth_methods.email.linked ? (
              <Button
                variant="ghost"
                size="md"
                onClick={() => setConfirmKind("unlink-email")}
                disabled={unlinkEmail.isPending}
              >
                {t("account.email.unlink")}
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="md"
                onClick={() => linkWeb.mutate()}
                disabled={linkWeb.isPending}
              >
                {t("account.web.link")}
              </Button>
            )}
          </div>

          {/* Пароль — только информация; смена пароля — отдельный экран,
              пока не встроен. Если password_set=false и email привязан —
              есть смысл добавить кнопку задать пароль. */}
          <div className="flex items-center justify-between text-[12px] text-[color:var(--text-soft)]">
            <span>{t("account.password.change")}</span>
            <span>{u.auth_methods.password_set ? "✓" : "—"}</span>
          </div>
        </div>

        {/* Показ сгенерированной ссылки */}
        {linkTgUrl && (
          <div className="mt-3 flex flex-col gap-2 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3">
            <div className="text-[13px] text-[color:var(--text-soft)]">
              {t("account.link.tg.help")}
            </div>
            <a
              href={linkTgUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block rounded-[var(--radius-sm)] bg-[color:var(--accent)] px-4 py-2 text-center text-[14px] text-[color:var(--on-accent)]"
            >
              {t("account.link.tg.open")}
            </a>
          </div>
        )}
        {linkWebUrl && (
          <div className="mt-3 flex flex-col gap-2 rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-3">
            <div className="text-[13px] text-[color:var(--text-soft)]">
              {t("account.link.web.help")}
            </div>
            <div className="break-all rounded-[var(--radius-sm)] bg-[color:var(--surface)] p-2 text-[12px] text-[color:var(--text)]">
              {linkWebUrl}
            </div>
            <Button variant="secondary" size="md" onClick={() => copyLink(linkWebUrl)}>
              {linkCopied ? t("account.link.web.copied") : t("account.link.web.copy")}
            </Button>
          </div>
        )}
        {linkError && (
          <div
            role="alert"
            className="mt-3 rounded-[var(--radius)] bg-[color:var(--error-bg,#f8d7d5)] p-3 text-[13px] text-[color:var(--error,#8a1c1c)]"
          >
            {linkError}
          </div>
        )}
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
            onClick={() => setConfirmKind("logout-all")}
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
            onClick={() => setConfirmKind("revoke-consent")}
          >
            {t("settings.consent.revoke")}
          </Button>
          <Button
            variant="danger"
            size="md"
            onClick={() => setConfirmKind("delete-account")}
          >
            {t("settings.delete")}
          </Button>
        </div>
      </Section>

      <ConfirmDialog
        open={confirmKind === "delete-account"}
        title={t("confirm.delete.account.title")}
        description={t("confirm.delete.account.desc")}
        confirmLabel={t("confirm.delete.account.yes")}
        danger
        busy={deleteAccount.isPending}
        onConfirm={() => deleteAccount.mutate()}
        onClose={() => setConfirmKind(null)}
      />
      <ConfirmDialog
        open={confirmKind === "revoke-consent"}
        title={t("confirm.revoke.consent.title")}
        description={t("confirm.revoke.consent.desc")}
        confirmLabel={t("confirm.revoke.consent.yes")}
        danger
        busy={revokeConsent.isPending}
        onConfirm={() => revokeConsent.mutate()}
        onClose={() => setConfirmKind(null)}
      />
      <ConfirmDialog
        open={confirmKind === "logout-all"}
        title={t("confirm.logout.all.title")}
        description={t("confirm.logout.all.desc")}
        confirmLabel={t("confirm.logout.all.yes")}
        danger
        busy={revokeAll.isPending}
        onConfirm={() => revokeAll.mutate()}
        onClose={() => setConfirmKind(null)}
      />
      <ConfirmDialog
        open={confirmKind === "unlink-tg"}
        title={t("account.unlink.title")}
        description={t("account.unlink.desc")}
        confirmLabel={t("account.unlink.yes")}
        busy={unlinkTg.isPending}
        onConfirm={() => {
          unlinkTg.mutate();
          setConfirmKind(null);
        }}
        onClose={() => setConfirmKind(null)}
      />
      <ConfirmDialog
        open={confirmKind === "unlink-email"}
        title={t("account.unlink.title")}
        description={t("account.unlink.desc")}
        confirmLabel={t("account.unlink.yes")}
        busy={unlinkEmail.isPending}
        onConfirm={() => {
          unlinkEmail.mutate();
          setConfirmKind(null);
        }}
        onClose={() => setConfirmKind(null)}
      />
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
