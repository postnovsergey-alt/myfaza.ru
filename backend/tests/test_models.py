"""Проверки схемы БД. Ловят расхождения моделей с разделом 6 ТЗ."""
from sqlalchemy import Enum as SAEnum

from app.db.enums import NotificationType, NotifyChannel
from app.db.models import Base, Notification, UserSettings


def test_all_tables_present():
    expected = {
        "users", "user_settings", "cycles", "daily_logs",
        "push_subscriptions", "notifications", "sessions",
        "account_link_tokens", "audit_log",
    }
    assert expected == set(Base.metadata.tables)


def test_notification_dedup_constraint():
    """FR-4.8: дедупликация уведомлений обеспечивается БД, а не воркером."""
    uq = next(
        c for c in Notification.__table__.constraints
        if getattr(c, "name", None) == "uq_notifications_dedup"
    )
    assert {c.name for c in uq.columns} == {"user_id", "type", "target_date", "channel"}


def test_notify_before_days_defaults_to_three():
    """FR-4.1: напоминание за 3 дня — значение по умолчанию."""
    assert UserSettings.__table__.c.notify_before_days.default.arg == 3


def test_discreet_mode_on_by_default():
    """FR-4.7: дискретный режим включён по умолчанию."""
    assert UserSettings.__table__.c.discreet_mode.default.arg is True


def test_enum_labels_use_values_not_member_names():
    """Метки Postgres-типов должны совпадать со значениями из ТЗ (lowercase)."""
    col = Notification.__table__.c.type
    assert isinstance(col.type, SAEnum)
    assert set(col.type.enums) == {e.value for e in NotificationType}
    assert "period_upcoming" in col.type.enums

    ch = UserSettings.__table__.c.notify_channel
    assert set(ch.type.enums) == {e.value for e in NotifyChannel}


def test_cascade_delete_from_users():
    """FR-7.2: удаление аккаунта должно физически стирать связанные записи."""
    for table in ("cycles", "daily_logs", "sessions", "push_subscriptions",
                  "notifications", "account_link_tokens", "user_settings"):
        fks = [fk for fk in Base.metadata.tables[table].foreign_keys
               if fk.column.table.name == "users"]
        assert fks, f"{table}: нет FK на users"
        assert all(fk.ondelete == "CASCADE" for fk in fks), f"{table}: FK без CASCADE"
