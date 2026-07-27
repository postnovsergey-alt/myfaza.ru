import { t } from "@/i18n";

/**
 * Показывается, когда браузер — Safari на iOS, а PWA не установлено.
 * Web Push на iOS работает только для PWA на домашнем экране (iOS 16.4+).
 */
export function IosInstallHint() {
  return (
    <div className="rounded-[var(--radius)] bg-[color:var(--surface-alt)] p-4 text-[13px] leading-[1.5]">
      <div className="mb-2 font-medium text-[color:var(--text)]">
        {t("push.ios.title")}
      </div>
      <ol className="ml-4 list-decimal text-[color:var(--text-soft)]">
        <li>{t("push.ios.step1")}</li>
        <li>{t("push.ios.step2")}</li>
        <li>{t("push.ios.step3")}</li>
      </ol>
    </div>
  );
}
