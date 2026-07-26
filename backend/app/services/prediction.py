"""Прогноз следующего цикла — раздел 7 ТЗ.

Идея алгоритма (ТЗ 7.1):
- нет данных   → берём длину из онбординга, low, ±5 дней;
- 1–2 цикла    → смешиваем наблюдение с заявленной длиной 60/40, medium, ±3;
- 3+ циклов    → взвешенное среднее последних 6 без выбросов,
                 margin по σ, high при σ ≤ 3, иначе medium.

Овуляция считается от прогнозной даты СЛЕДУЮЩЕГО цикла минус
лютеиновая фаза (14 дней по умолчанию, ТЗ 7.4) — не от начала текущего.
Фертильное окно: −5..+1 от овуляции.

Функция `compute` — чистая. HTTP-слой отдельно собирает входы из БД.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median, stdev
from typing import Literal

Confidence = Literal["low", "medium", "high"]
Regularity = Literal["regular", "slightly_irregular", "irregular"]


# ---------------------------------------------------------------- вход/выход


@dataclass
class PredictionInputs:
    """Всё, что нужно алгоритму. HTTP-слой собирает это из БД + настроек."""

    # cycle_lengths от свежих к старым (recent[0] — самый свежий цикл)
    completed_cycle_lengths: list[int]
    last_cycle_start: date
    avg_cycle_length: int
    avg_period_length: int
    luteal_phase_length: int
    today: date


@dataclass
class PredictionResult:
    predicted_start: date
    predicted_end: date
    margin_days: int
    confidence: Confidence
    based_on_cycles: int
    ovulation_date: date
    fertile_window_start: date
    fertile_window_end: date
    current_cycle_day: int
    days_until_period: int
    is_overdue: bool
    overdue_days: int


# ---------------------------------------------------------------- ядро


# Диапазон «приемлемо в природе» — ТЗ 7.2. Всё, что вне, — выброс.
_PHYSIO_MIN = 21
_PHYSIO_MAX = 45
_RECENT_WINDOW = 6
_WEIGHTS = [6, 5, 4, 3, 2, 1]  # для recent[0..5]


def _weighted_mean(values: list[int]) -> float:
    """Взвешенное среднее. values в порядке recent-first."""
    weights = _WEIGHTS[: len(values)]
    return sum(v * w for v, w in zip(values, weights, strict=True)) / sum(weights)


def _remove_outliers(values: list[int]) -> list[int]:
    """Отсекает выбросы (ТЗ 7.2):
    - вне физиологического диапазона [21, 45];
    - отклонение от медианы > 2σ.
    Если после отсечения осталось меньше 3 значений — возвращаем исходное
    (данных слишком мало, чтобы разбрасываться).
    """
    if not values:
        return []
    physio = [v for v in values if _PHYSIO_MIN <= v <= _PHYSIO_MAX]
    if len(physio) < 3:
        return values
    med = median(physio)
    if len(physio) < 2:
        return physio
    sd = stdev(physio)
    cleaned = physio if sd == 0 else [v for v in physio if abs(v - med) <= 2 * sd]
    if len(cleaned) < 3:
        return values
    return cleaned


def _confidence_and_margin(cleaned: list[int]) -> tuple[Confidence, int]:
    """ТЗ 7.1: margin по σ, high при σ ≤ 3."""
    if len(cleaned) < 2:
        return "medium", 3
    sd = stdev(cleaned)
    confidence: Confidence = "high" if sd <= 3 else "medium"
    margin = max(1, min(7, round(sd)))
    return confidence, margin


def classify_regularity(cycle_lengths: Iterable[int]) -> Regularity:
    """ТЗ 7.5. Ожидает последние 6 циклов."""
    values = list(cycle_lengths)
    if len(values) < 2:
        return "regular"
    sd = stdev(values)
    if sd <= 3:
        return "regular"
    if sd <= 7:
        return "slightly_irregular"
    return "irregular"


# ---------------------------------------------------------------- главное


def compute(inputs: PredictionInputs) -> PredictionResult:
    cycles = inputs.completed_cycle_lengths
    n = len(cycles)

    # --- длина следующего цикла и уверенность ---
    if n == 0:
        length = inputs.avg_cycle_length
        confidence: Confidence = "low"
        margin = 5
    elif n < 3:
        observed = sum(cycles) / n
        length = round(0.6 * observed + 0.4 * inputs.avg_cycle_length)
        confidence = "medium"
        margin = 3
    else:
        recent = cycles[:_RECENT_WINDOW]
        cleaned = _remove_outliers(recent)
        length = round(_weighted_mean(cleaned))
        confidence, margin = _confidence_and_margin(cleaned)

    predicted_start = inputs.last_cycle_start + timedelta(days=length)
    predicted_end = predicted_start + timedelta(days=inputs.avg_period_length - 1)

    # --- овуляция и фертильное окно ---
    ovulation_date = predicted_start - timedelta(days=inputs.luteal_phase_length)
    fertile_start = ovulation_date - timedelta(days=5)
    fertile_end = ovulation_date + timedelta(days=1)

    # --- состояние сегодня ---
    days_from_start = (inputs.today - inputs.last_cycle_start).days
    current_cycle_day = max(1, days_from_start + 1)
    diff = (predicted_start - inputs.today).days
    if diff >= 0:
        days_until_period = diff
        is_overdue = False
        overdue_days = 0
    else:
        days_until_period = 0
        is_overdue = True
        overdue_days = -diff

    return PredictionResult(
        predicted_start=predicted_start,
        predicted_end=predicted_end,
        margin_days=margin,
        confidence=confidence,
        based_on_cycles=n,
        ovulation_date=ovulation_date,
        fertile_window_start=fertile_start,
        fertile_window_end=fertile_end,
        current_cycle_day=current_cycle_day,
        days_until_period=days_until_period,
        is_overdue=is_overdue,
        overdue_days=overdue_days,
    )
