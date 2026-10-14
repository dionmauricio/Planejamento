from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from .models import CurvePeriod

ZERO = Decimal("0")


def as_decimal(value: Any, field: str = "peso") -> Decimal:
    try:
        number = Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise ValueError(f"{field} deve ser um número válido.") from exc
    if not number.is_finite() or number < ZERO:
        raise ValueError(f"{field} deve ser um número finito e não negativo.")
    if number > Decimal("99999999999.999"):
        raise ValueError(f"{field} excede o limite de 99.999.999.999,999 kg.")
    return number.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def fraction(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator else ZERO


def curve_rows(entries: Iterable[CurvePeriod]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(entries, key=lambda entry: (entry.period_date, entry.sequence))
    planned_total = sum((entry.planned_kg for entry in ordered), ZERO)
    actual_total = sum((entry.actual_kg for entry in ordered), ZERO)
    planned_running = ZERO
    actual_running = ZERO
    rows: list[dict[str, Any]] = []
    for entry in ordered:
        planned_running += entry.planned_kg
        actual_running += entry.actual_kg
        planned_progress = fraction(planned_running, planned_total)
        actual_progress = fraction(actual_running, planned_total)
        rows.append(
            {
                "id": entry.id,
                "sequence": entry.sequence,
                "period_date": entry.period_date.isoformat(),
                "planned_kg": float(entry.planned_kg),
                "planned_cumulative_kg": float(planned_running),
                "planned_progress": float(planned_progress),
                "actual_kg": float(entry.actual_kg),
                "actual_cumulative_kg": float(actual_running),
                "actual_progress": float(actual_progress),
                "deviation_kg": float(actual_running - planned_running),
                "deviation_progress": float(actual_progress - planned_progress),
                "status": "No prazo" if actual_progress >= planned_progress else "Atrasado",
            }
        )
    current_rows = [row for row in rows if date.fromisoformat(row["period_date"]) <= date.today()]
    current = current_rows[-1] if current_rows else (rows[0] if rows else None)
    summary = {
        "planned_kg": float(planned_total),
        "actual_kg": float(actual_total),
        "progress": float(fraction(actual_total, planned_total)),
        "deviation_kg": float(actual_total - planned_total),
        "as_of_date": current["period_date"] if current else None,
        "as_of_planned_progress": current["planned_progress"] if current else 0,
        "as_of_actual_progress": current["actual_progress"] if current else 0,
        "as_of_deviation_kg": current["deviation_kg"] if current else 0,
        "as_of_deviation_progress": current["deviation_progress"] if current else 0,
        "status": current["status"] if current else "Sem dados",
    }
    return rows, summary


def weekly_rows(entries: Iterable[CurvePeriod]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    buckets: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"planned_kg": ZERO, "actual_kg": ZERO}
    )
    for entry in entries:
        week_start = date.fromordinal(entry.period_date.toordinal() - entry.period_date.weekday())
        buckets[week_start]["planned_kg"] += entry.planned_kg
        buckets[week_start]["actual_kg"] += entry.actual_kg

    totals = sorted(buckets.items())
    planned_total = sum((values["planned_kg"] for _, values in totals), ZERO)
    actual_total = sum((values["actual_kg"] for _, values in totals), ZERO)
    planned_running = ZERO
    actual_running = ZERO
    rows: list[dict[str, Any]] = []
    for sequence, (week_start, values) in enumerate(totals, start=1):
        planned_running += values["planned_kg"]
        actual_running += values["actual_kg"]
        planned_progress = fraction(planned_running, planned_total)
        actual_progress = fraction(actual_running, planned_total)
        rows.append(
            {
                "id": None,
                "sequence": sequence,
                "period_date": week_start.isoformat(),
                "planned_kg": float(values["planned_kg"]),
                "planned_cumulative_kg": float(planned_running),
                "planned_progress": float(planned_progress),
                "actual_kg": float(values["actual_kg"]),
                "actual_cumulative_kg": float(actual_running),
                "actual_progress": float(actual_progress),
                "deviation_kg": float(actual_running - planned_running),
                "deviation_progress": float(actual_progress - planned_progress),
                "status": "No prazo" if actual_progress >= planned_progress else "Atrasado",
            }
        )
    current_rows = [row for row in rows if date.fromisoformat(row["period_date"]) <= date.today()]
    current = current_rows[-1] if current_rows else (rows[0] if rows else None)
    return rows, {
        "planned_kg": float(planned_total),
        "actual_kg": float(actual_total),
        "progress": float(fraction(actual_total, planned_total)),
        "deviation_kg": float(actual_total - planned_total),
        "as_of_date": current["period_date"] if current else None,
        "as_of_planned_progress": current["planned_progress"] if current else 0,
        "as_of_actual_progress": current["actual_progress"] if current else 0,
        "as_of_deviation_kg": current["deviation_kg"] if current else 0,
        "as_of_deviation_progress": current["deviation_progress"] if current else 0,
        "status": current["status"] if current else "Sem dados",
    }
