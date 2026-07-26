import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";
import { applyColorScheme, getColorScheme } from "@/platform";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/settings";

const THEMES = ["auto", "light", "dark"] as const;

export function SettingsPage() {
  const theme = useUi((s) => s.theme);
  const setTheme = useUi((s) => s.setTheme);
  const logout = useAuth((s) => s.logout);
  const user = useAuth((s) => s.user);
  const navigate = useNavigate();

  const changeTheme = (v: (typeof THEMES)[number]) => {
    setTheme(v);
    applyColorScheme(getColorScheme(v));
  };

  return (
    <div className="flex flex-col gap-6">
      <h1>{t("settings.title")}</h1>

      {user && (
        <div className="rounded-[var(--radius)] bg-[color:var(--surface)] p-4 text-[13px] text-[color:var(--text-soft)]">
          {user.email ?? user.telegram_username ?? user.id}
        </div>
      )}

      <Section title={t("settings.theme")}>
        <div className="grid grid-cols-3 gap-2">
          {THEMES.map((v) => (
            <button
              key={v}
              onClick={() => changeTheme(v)}
              className={[
                "min-h-[44px] rounded-[var(--radius-sm)] text-[14px] transition-colors",
                theme === v
                  ? "bg-[color:var(--accent)] text-[color:var(--on-accent)]"
                  : "bg-[color:var(--surface-alt)] text-[color:var(--text)]",
              ].join(" ")}
            >
              {t(`settings.theme.${v}`)}
            </button>
          ))}
        </div>
      </Section>

      <Section title={t("settings.notif")}>
        {/*
          Управление уведомлениями появляется, когда бэкенд отдаст /settings
          в спринте 6. Сейчас — статичное описание и заглушка теста.
        */}
        <p className="text-[13px] text-[color:var(--text-soft)]">
          {t("settings.notif.days", { n: 3 })} · 10:00 · {t("settings.notif.channel.both")}
        </p>
        <div className="mt-3">
          <Button variant="secondary" size="md">
            {t("settings.notif.test")}
          </Button>
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
