import { NavLink } from "react-router-dom";

import { t } from "@/i18n";

// Нижняя навигация. Иконки — тонкие абстрактные SVG (не тематические,
// см. DESIGN-SPEC 1.1). Только 4 пункта в MVP.
const items = [
  { to: "/", key: "nav.home", icon: HomeIcon },
  { to: "/calendar", key: "nav.calendar", icon: CalendarIcon },
  { to: "/stats", key: "nav.stats", icon: StatsIcon },
  { to: "/settings", key: "nav.settings", icon: SettingsIcon },
] as const;

export function BottomNav() {
  return (
    <nav
      className={[
        "fixed inset-x-0 bottom-0 z-30",
        "border-t border-[color:var(--border)]",
        "bg-[color:var(--surface)]/95 backdrop-blur",
        "pb-[max(env(safe-area-inset-bottom),4px)] pt-1",
      ].join(" ")}
      aria-label={t("nav.home") + " и другие вкладки"}
    >
      <ul className="mx-auto flex max-w-[480px] items-stretch">
        {items.map((it) => (
          <li key={it.to} className="flex-1">
            <NavLink
              to={it.to}
              end={it.to === "/"}
              className={({ isActive }) =>
                [
                  "flex min-h-[52px] flex-col items-center justify-center gap-0.5",
                  "text-[11px] transition-colors",
                  isActive
                    ? "text-[color:var(--accent)]"
                    : "text-[color:var(--text-soft)]",
                ].join(" ")
              }
            >
              <it.icon />
              <span>{t(it.key)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function HomeIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" />
    </svg>
  );
}
function CalendarIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="4" y="6" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 10h16M8 4v3M16 4v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function StatsIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M5 19V11M10 19V6M15 19V13M20 19V9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function SettingsIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
      />
    </svg>
  );
}
