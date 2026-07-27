import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";

/**
 * Публичная страница политики конфиденциальности. Доступна без
 * авторизации (важное требование 152-ФЗ — оператор обязан
 * опубликовать политику публично).
 *
 * Текст здесь дублирует docs/privacy-policy.md — на MVP держим
 * встроенным, чтобы не грузить дополнительный markdown-парсер.
 */
export function PrivacyPage() {
  const nav = useNavigate();
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1>{t("privacy.title")}</h1>
        <Button variant="ghost" size="md" onClick={() => nav(-1)}>
          {t("privacy.back")}
        </Button>
      </div>

      <p className="text-[13px] text-[color:var(--text-soft)]">
        Версия 1.0 · Дата: 2026-07-27
      </p>

      <Section title="Кто оператор">
        <p>
          «Моя фаза» — сервис учёта менструального цикла (myfaza.ru).
          Контакт: privacy@myfaza.ru.
        </p>
      </Section>

      <Section title="Какие данные мы собираем">
        <ul className="ml-4 list-disc">
          <li>Email или Telegram-идентификатор, хеш пароля.</li>
          <li>
            Даты менструаций, симптомы, настроение, заметки — заметки
            шифруются на уровне приложения.
          </li>
          <li>Настройки уведомлений и часовой пояс.</li>
        </ul>
        <p>
          Мы <b>не</b> собираем имя, фамилию, дату рождения, телефон,
          геолокацию, статистику для рекламы.
        </p>
      </Section>

      <Section title="Цели и правовое основание">
        <p>
          Данные о цикле — специальная категория (ст. 10 152-ФЗ).
          Обработка производится только на основании отдельного согласия,
          подписываемого в приложении. Единственная цель — прогноз даты
          следующей менструации и отправка напоминаний.
        </p>
      </Section>

      <Section title="Хранение и защита">
        <ul className="ml-4 list-disc">
          <li>Серверы в РФ.</li>
          <li>TLS 1.3, шифрование дисков, HSTS, CSP.</li>
          <li>Заметки шифруются AES-256-GCM.</li>
          <li>
            В логи и в трекер ошибок никогда не попадают даты циклов и
            содержимое заметок.
          </li>
        </ul>
      </Section>

      <Section title="Ваши права">
        <ul className="ml-4 list-disc">
          <li>Экспорт всех данных (CSV/JSON) в один клик.</li>
          <li>Отзыв согласия — физическое удаление данных.</li>
          <li>Удаление аккаунта в два тапа.</li>
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-[15px] font-medium">{title}</h2>
      <div className="text-[14px] leading-[1.55] text-[color:var(--text-soft)]">
        {children}
      </div>
    </div>
  );
}
