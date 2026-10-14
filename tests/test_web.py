from datetime import date
from decimal import Decimal
import unittest

from app import create_app
from app.models import CurvePeriod


class WebTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            }
        )
        self.client = self.app.test_client()
        factory = self.app.extensions["db_session_factory"]
        with factory() as session:
            session.add_all(
                [
                    CurvePeriod(
                        sheet_key="curva-s",
                        sequence=1,
                        period_date=date(2026, 8, 31),
                        planned_kg=Decimal("1000"),
                        actual_kg=Decimal("400"),
                    ),
                    CurvePeriod(
                        sheet_key="curva-s",
                        sequence=2,
                        period_date=date(2026, 9, 1),
                        planned_kg=Decimal("1000"),
                        actual_kg=Decimal("300"),
                    ),
                ]
            )
            session.commit()

    def tearDown(self):
        self.app.extensions["db_engine"].dispose()

    def test_every_source_worksheet_has_a_frontend_and_api_tab(self):
        sheets = self.client.get("/api/planilhas").get_json()
        self.assertEqual(len(sheets), 9)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'alt="JM Engenharia"', response.data)
        logo = self.client.get("/static/images/jm-logo.png")
        try:
            self.assertEqual(logo.status_code, 200)
            self.assertEqual(logo.mimetype, "image/png")
        finally:
            logo.close()
        for sheet in sheets:
            self.assertIn(sheet["name"].encode(), response.data)

    def test_curve_api_recalculates_indicators_after_edit(self):
        response = self.client.get("/api/planilhas/curva-s")
        data = response.get_json()
        self.assertEqual(data["summary"]["planned_kg"], 2000)
        self.assertEqual(data["summary"]["actual_kg"], 700)
        period_id = data["rows"][0]["id"]

        updated = self.client.put(
            f"/api/planilhas/curva-s/periodos/{period_id}",
            json={"actual_kg": "1200.25"},
        )
        self.assertEqual(updated.status_code, 200)
        refreshed = self.client.get("/api/planilhas/curva-s").get_json()
        self.assertEqual(refreshed["rows"][0]["actual_cumulative_kg"], 1200.25)
        self.assertAlmostEqual(refreshed["summary"]["progress"], 0.750125)

    def test_invalid_production_and_unknown_sheet_are_rejected(self):
        data = self.client.get("/api/planilhas/curva-s").get_json()
        period_id = data["rows"][0]["id"]
        invalid = self.client.put(
            f"/api/planilhas/curva-s/periodos/{period_id}",
            json={"actual_kg": -1},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("error", invalid.get_json())
        self.assertEqual(self.client.get("/api/planilhas/inexistente").status_code, 404)

    def test_task_create_and_update(self):
        created = self.client.post(
            "/api/tarefas",
            json={
                "project_area": "Estação de Emenda",
                "name": "Item de teste",
                "planned_kg": "250",
            },
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.get_json()["id"]
        updated = self.client.patch(
            f"/api/tarefas/{task_id}",
            json={"manufactured_kg": "125", "shipped_kg": "75"},
        )
        self.assertEqual(updated.status_code, 200)
        rows = self.client.get("/api/planilhas/base-tarefas").get_json()["rows"]
        task = next(row for row in rows if row["id"] == task_id)
        self.assertEqual(task["progress"], 0.5)
        self.assertEqual(task["shipped_kg"], 75)


if __name__ == "__main__":
    unittest.main()
