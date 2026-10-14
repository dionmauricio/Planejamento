from datetime import date
from decimal import Decimal
import unittest

from app.domain import as_decimal, curve_rows, weekly_rows
from app.models import CurvePeriod


def period(sequence: int, day: int, planned: str, actual: str) -> CurvePeriod:
    return CurvePeriod(
        id=sequence,
        sheet_key="curva-s",
        sequence=sequence,
        period_date=date(2026, 8, day),
        planned_kg=Decimal(planned),
        actual_kg=Decimal(actual),
    )


class DomainTests(unittest.TestCase):
    def test_curve_progress_and_variance_use_cumulative_weight(self):
        rows, summary = curve_rows(
            [period(1, 1, "100", "120"), period(2, 2, "300", "80")]
        )
        self.assertEqual(rows[0]["planned_cumulative_kg"], 100)
        self.assertEqual(rows[1]["actual_cumulative_kg"], 200)
        self.assertEqual(rows[1]["planned_progress"], 1)
        self.assertEqual(rows[1]["actual_progress"], 0.5)
        self.assertEqual(rows[1]["deviation_kg"], -200)
        self.assertEqual(summary["planned_kg"], 400)
        self.assertEqual(summary["actual_kg"], 200)
        self.assertEqual(summary["status"], "Atrasado")

    def test_weekly_aggregation_groups_by_monday(self):
        rows, summary = weekly_rows(
            [period(1, 3, "100", "40"), period(2, 10, "200", "200")]
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["period_date"], "2026-08-03")
        self.assertEqual(rows[1]["period_date"], "2026-08-10")
        self.assertEqual(summary["planned_kg"], 300)

    def test_weight_validation_rejects_negative_and_infinite_values(self):
        with self.assertRaises(ValueError):
            as_decimal("-0.01", "Peso")
        with self.assertRaises(ValueError):
            as_decimal("Infinity", "Peso")
        self.assertEqual(as_decimal("1.2345"), Decimal("1.235"))


if __name__ == "__main__":
    unittest.main()
