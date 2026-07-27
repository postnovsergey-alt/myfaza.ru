import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { IosInstallHint } from "@/features/push/IosInstallHint";
import {
  detectCapability,
  isSubscribed,
  subscribe,
  unsubscribe,
} from "@/features/push/pushClient";
import { t } from "@/i18n";
import { applyColorScheme, getColorScheme } from "@/platform";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/settings";

const THEMES = ["auto", "light", "dark"] as const;
const CHANNELS = ["telegram", "web", "both", "none"] as const;
const DAYS_OPTIONS = [1, 2, 3, 5, 7] as const;

interface ServerSettings {
  notify_before_days: number;
  notify_time: string;
  notify_channel: string;
  discreet_mode: boolean;
}

export function SettingsPage() {
  const theme = useUi((s) => s.theme);
  const setTheme = useUi((s) => s.setTheme);
  const logout = useAuth((s) => s.logout);
  const user = useAuth((s) => s.user);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<ServerSettings>("/settings"),
  });

  const patch = useMutation({
    mutationFn: (body: Partial<ServerSettings>) =>
      api.patch<ServerSettings>("/settings", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  const cap = detectCapability();
  const [pushOn, setPushOn] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);
  useEffect(() => {
    void isSubscribed().then(setPushOn);
  }, []);

  const changeTheme = (v: (typeof THEMES)[number]) => {
    setTheme(v);
    applyColorScheme(getColorScheme(v));
  };

  const togglePush = async () => {
    setPushBusy(true);
    try {
      if (pushOn) {
        await unsubscribe();
        setPushOn(false);
      } else {
        const sub = await subscribe();
        setPushOn(sub !== null);
      }
    } finally {
      setPushBusy(false);
    }
  };

  const sendTest = useMutation({
    mutationFn: () => api.post<{ sent_web: number; sent_telegram: number }>("/push/test"),
  });

  return (
    <div className="flex flex-col gap-6">
      <h1>{t("settings.title")}</h1>

      {user && (
        <button
          onClick={() => navigate("/account")}
          className="rounded-[var(--radius)] bg-[color:var(--surface)] p-4 text-left"
        >
          <div className="text-[14px] text-[color:var(--text)]">
            {user.display_name ?? user.email ?? user.telegram_username ?? "Профиль"}
          </div>
          <div className="text-[12px] text-[color:var(--text-soft)]">
            {t("account.title")} →
          </div>
        </button>
      )}

      <Section title={t("settings.theme")}>
        <div className="grid grid-cols-3 gap-2">
          {THEMES.map((v) => (
            <button
              key={v}
              onClick={() => changeTheme(v)}
              className={pill(theme === v)}
            >
              {t(`settings.theme.${v}`)}
            </button>
          ))}
        </div>
      </Section>

      <Section title={t("settings.notif")}>
        <div className="flex flex-col gap-3">
          <RowGroup label={t("settings.notif.days", { n: settings.data?.notify_before_days ?? 3 })}>
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => patch.mutate({ notify_before_days: d })}
                className={pillSmall(settings.data?.notify_before_days === d)}
              >
                {d}
              </button>
            ))}
          </RowGroup>

          <RowGroup label={t("settings.notif.channel")}>
            {CHANNELS.map((c) => (
              <button
                key={c}
                onClick={() => patch.mutate({ notify_channel: c })}
                className={pillSmall(settings.data?.notify_channel === c)}
              >
                {t(`settings.notif.channel.${c}`)}
              </button>
            ))}
          </RowGroup>

          <label className="flex items-center justify-between gap-3 rounded-[var(--radius-sm)] bg-[color:var(--surface-alt)] p-3">
            <span className="text-[14px]">{t("settings.notif.discreet")}</span>
            <input
              type="checkbox"
              className="h-5 w-5 accent-[color:var(--accent)]"
              checked={settings.data?.discreet_mode ?? true}
              onChange={(e) => patch.mutate({ discreet_mode: e.target.checked })}
            />
          </label>

          {cap === "ios-needs-pwa" && <IosInstallHint />}
          {cap === "supported" && (
            <div className="flex flex-col gap-2">
              <Button
                variant={pushOn ? "secondary" : "primary"}
                size="md"
                onClick={togglePush}
                disabled={pushBusy}
              >
                {pushOn ? t("push.disable") : t("push.enable")}
              </Button>
              <Button
                variant="ghost"
                size="md"
                onClick={() => sendTest.mutate()}
                disabled={sendTest.isPending}
              >
                {t("settings.notif.test")}
              </Button>
            </div>
          )}
          {cap === "denied" && (
            <p className="text-[13px] text-[color:var(--text-soft)]">{t("push.denied")}</p>
          )}
          {cap === "unsupported" && (
            <p className="text-[13px] text-[color:var(--text-soft)]">{t("push.unsupported")}</p>
          )}
        </div>
      </Section>

      <Section title={t("settings.privacy")}>
        <div className="flex flex-col gap-2">
          <Button variant="ghost" size="md">
            {t("settings.export")}
          </Button>
          <Button variant="danger" size="md">
            {t("settings.consent.revoke")}
          </Button>
          <Button variant="danger" size="md">
            {t("settings.delete")}
          </Button>
        </div>
      </Section>

      <Button
        variant="ghost"
        size="lg"
        onClick={() => {
          logout();
          navigate("/login", { replace: true });
        }}
      >
        {t("settings.logout")}
      </Button>
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

function RowGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-[13px] text-[color:var(--text-soft)]">{label}</div>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

function pill(active: boolean): string {
  return [
    "min-h-[44px] rounded-[var(--radius-sm)] text-[14px] transition-colors px-3",
    active
      ? "bg-[color:var(--accent)] text-[color:var(--on-accent)]"
      : "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
  ].join(" ");
}

function pillSmall(active: boolean): string {
  return [
    "min-h-[36px] rounded-[var(--radius-sm)] text-[13px] px-3 transition-colors",
    active
      ? "bg-[color:var(--accent)] text-[color:var(--on-accent)]"
      : "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
  ].join(" ");
}
