"""Тесты алгоритма прогноза — раздел 7.7 ТЗ.

Тесты писаны до реализации — они и есть спецификация алгоритма.
Работают на чистой функции `services.prediction.compute` без БД.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.services.prediction import PredictionInputs, PredictionResult, compute

# --------------------------------------------------------- вспомогательное


@dataclass
class Defaults:
    """Мини-заменитель UserSettings для юнит-тестов."""

    avg_cycle_length: int = 28
    avg_period_length: int = 5
    luteal_phase_length: int = 14


def _inputs(
    cycle_lengths: list[int], last_start: date, today: date | None = None
) -> PredictionInputs:
    """cycle_lengths — от свежих к старым (recent[0] = самый свежий)."""
    return PredictionInputs(
        completed_cycle_lengths=list(cycle_lengths),
        last_cycle_start=last_start,
        avg_cycle_length=Defaults().avg_cycle_length,
        avg_period_length=Defaults().avg_period_length,
        luteal_phase_length=Defaults().luteal_phase_length,
        today=today or last_start,  # для юнит-тестов чаще всего сегодня = last_start
    )


# --------------------------------------------------------- 7.7 обязательные


def test_no_data_uses_defaults_and_low_confidence():
    """Пользователь без залогированных циклов — дефолт 28, confidence=low."""
    r = compute(_inputs([], date(2026, 8, 1)))
    assert r.based_on_cycles == 0
    assert r.confidence == "low"
    assert r.margin_days == 5
    assert r.predicted_start == date(2026, 8, 29)  # 28 дней от last_start


def test_perfect_28_day_cycle_gives_high_confidence():
    """Идеально регулярный 28 × 6 → прогноз ровно 28, margin=1, high."""
    r = compute(_inputs([28] * 6, date(2026, 8, 1)))
    assert r.predicted_start == date(2026, 8, 29)
    assert r.margin_days == 1
    assert r.confidence == "high"
    assert r.based_on_cycles == 6


def test_irregular_sequence_marks_medium_with_wider_margin():
    """Нерегулярный ряд → confidence=medium, margin >= 5."""
    r = compute(_inputs([25, 35, 28, 40, 22, 31], date(2026, 8, 1)))
    assert r.confidence == "medium"
    assert r.margin_days >= 5


def test_single_outlier_is_removed():
    """Один длинный цикл 90 среди 28-х не должен ломать прогноз."""
    r = compute(_inputs([28, 28, 28, 90, 28, 28], date(2026, 8, 1)))
    # После отсечения выброса среднее ≈ 28
    assert abs((r.predicted_start - date(2026, 8, 29)).days) <= 1


def test_trend_of_lengthening_leans_towards_recent():
    """Тренд удлинения — прогноз ближе к 31, чем к простому среднему 28.5."""
    # recent[0] = 31 (самый свежий), ..., recent[5] = 26
    r = compute(_inputs([31, 30, 29, 28, 27, 26], date(2026, 8, 1)))
    simple_avg = 28  # round(28.5)
    weighted = (r.predicted_start - date(2026, 8, 1)).days
    assert weighted > simple_avg, f"weighted={weighted}, простое среднее={simple_avg}"
    assert weighted >= 29


def test_month_boundary_crossing():
    """Прогноз пересекает границу месяца."""
    r = compute(_inputs([28] * 6, date(2026, 8, 20)))
    assert r.predicted_start == date(2026, 9, 17)


def test_year_boundary_crossing():
    """Прогноз пересекает границу года."""
    r = compute(_inputs([28] * 6, date(2026, 12, 20)))
    assert r.predicted_start == date(2027, 1, 17)


def test_leap_year_february():
    """Пересечение февраля високосного года считается корректно."""
    # 2028 — високосный. 28 дней от 2028-02-01 → 2028-02-29.
    r = compute(_inputs([28] * 6, date(2028, 2, 1)))
    assert r.predicted_start == date(2028, 2, 29)


# --------------------------------------------------------- дополнительные
# (не требуются ТЗ напрямую, но покрывают край алгоритма)


def test_one_or_two_cycles_uses_medium_and_mixed_average():
    """1–2 цикла → medium, margin=3, длина = round(0.6·наблюдение + 0.4·дефолт)."""
    r = compute(_inputs([30, 30], date(2026, 8, 1)))
    assert r.confidence == "medium"
    assert r.margin_days == 3
    # round(0.6*30 + 0.4*28) = round(29.2) = 29
    assert r.predicted_start == date(2026, 8, 30)


def test_ovulation_and_fertile_window_from_end_of_cycle():
    """7.4: овуляция = predicted_start - luteal_phase_length; окно −5..+1."""
    r = compute(_inputs([28] * 6, date(2026, 8, 1)))
    # predicted_start = 2026-08-29, luteal_phase = 14 → овуляция 2026-08-15
    assert r.ovulation_date == date(2026, 8, 15)
    assert r.fertile_window_start == date(2026, 8, 10)
    assert r.fertile_window_end == date(2026, 8, 16)


def test_predicted_end_uses_avg_period_length():
    """predicted_end = predicted_start + avg_period_length - 1."""
    r = compute(_inputs([28] * 6, date(2026, 8, 1)))
    assert r.predicted_end == date(2026, 9, 2)  # 29 + 5 - 1 = день 3


def test_current_cycle_day_and_days_until_period():
    r = compute(
        _inputs([28] * 6, last_start=date(2026, 8, 1), today=date(2026, 8, 12))
    )
    assert r.current_cycle_day == 12
    assert r.days_until_period == 17
    assert r.is_overdue is False


def test_overdue_state():
    """Задержка: today > predicted_start."""
    r = compute(
        _inputs([28] * 6, last_start=date(2026, 8, 1), today=date(2026, 9, 3))
    )
    # predicted_start = 2026-08-29, today = 2026-09-03 → 5 дней задержки
    assert r.is_overdue is True
    assert r.overdue_days == 5
    assert r.days_until_period == 0


def test_no_data_still_produces_valid_ovulation():
    """При n=0 овуляция считается от прогнозной даты по luteal_phase_length."""
    r = compute(_inputs([], date(2026, 8, 1)))
    # predicted_start = 2026-08-29; luteal_phase=14; ovulation = 2026-08-15
    assert r.ovulation_date == date(2026, 8, 15)


def test_outlier_kept_in_stats_only_removed_from_prediction():
    """Отсечение выбросов не «удаляет» данные — оно только не участвует
    в вычислении. У нас это отражается тем, что based_on_cycles = сколько
    было исходно, а не сколько осталось после фильтра."""
    r = compute(_inputs([28, 28, 28, 90, 28, 28], date(2026, 8, 1)))
    assert r.based_on_cycles == 6


def test_only_last_six_are_used_for_prediction():
    """7.1: recent = последние 6, старые не влияют."""
    # 6 свежих по 28, 6 старых по 40 — прогноз должен быть ≈ 28
    r = compute(_inputs([28] * 6 + [40] * 6, date(2026, 8, 1)))
    assert r.predicted_start == date(2026, 8, 29)


# --------------------------------------------------------- регулярность


def test_regularity_classification():
    """7.5: sigma ≤ 3 regular, 3 < s ≤ 7 slightly_irregular, > 7 irregular."""
    from app.services.prediction import classify_regularity

    assert classify_regularity([28, 28, 29, 28, 27]) == "regular"
    # σ ≈ 3.96 — попадает в (3, 7]
    assert classify_regularity([22, 30, 25, 32, 27]) == "slightly_irregular"
    assert classify_regularity([21, 45, 22, 44, 21]) == "irregular"


# --------------------------------------------------------- смок / инварианты


@pytest.mark.parametrize("lens", [[], [28], [28, 30], [28, 30, 32], [28] * 12])
def test_prediction_result_is_well_formed(lens):
    r: PredictionResult = compute(_inputs(lens, date(2026, 8, 1)))
    assert r.margin_days >= 1
    assert r.confidence in {"low", "medium", "high"}
    assert r.based_on_cycles == len(lens)
    assert r.predicted_end >= r.predicted_start
    assert r.fertile_window_end >= r.fertile_window_start
