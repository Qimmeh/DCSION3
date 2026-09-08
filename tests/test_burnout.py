"""
Unit & Integration Tests for Burnout Risk Engine
================================================
Tests:
- Capacity stress calculation from capacity load.
- Sustained overload calculation with consecutive days.
- Multi-day trend trajectory detection (rising, falling, stable).
- Risk states (Low, Moderate, High, Very High, Critical).
- Structured diagnosis (primary, secondary, contributing).
- GET /api/v1/burnout-risk endpoint.
"""
import unittest
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models import User
from app.engine.burnout import (
    calculate_capacity_stress,
    calculate_sustained_overload,
    calculate_risk_trend,
    evaluate_risk_state,
    compute_burnout_score,
)


class BurnoutEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            self.user = User.query.filter_by(username="demo_student").first()
            if not self.user:
                self.user = User(username="demo_student", email="demo@university.edu")
                self.user.set_password("demo123")
                db.session.add(self.user)
                db.session.commit()
            self.user_id = self.user.id

    def test_capacity_stress(self):
        # Under 80% is 0 stress
        self.assertEqual(calculate_capacity_stress(75.0), 0.0)
        self.assertEqual(calculate_capacity_stress(80.0), 0.0)
        # 120% -> (120 - 80) / 80 * 100 = 50.0%
        self.assertEqual(calculate_capacity_stress(120.0), 50.0)
        # 160% -> 100%
        self.assertEqual(calculate_capacity_stress(160.0), 100.0)

    def test_sustained_overload(self):
        # 0 consecutive high load days
        res0 = calculate_sustained_overload([60.0, 70.0, 75.0])
        self.assertEqual(res0["consecutive_high_load_days"], 0)
        self.assertEqual(res0["sustained_overload_score"], 0.0)

        # 3 consecutive days
        res3 = calculate_sustained_overload([60.0, 85.0, 95.0, 110.0])
        self.assertEqual(res3["consecutive_high_load_days"], 3)
        self.assertEqual(res3["sustained_overload_score"], 75.0)

    def test_trend_and_state(self):
        trend_up = calculate_risk_trend(current_risk=40.0, forecast_risk=55.0)
        self.assertEqual(trend_up["direction"], "rising")

        trend_down = calculate_risk_trend(current_risk=65.0, forecast_risk=45.0)
        self.assertEqual(trend_down["direction"], "falling")

        self.assertEqual(evaluate_risk_state(15.0)["level"], "Low")
        self.assertEqual(evaluate_risk_state(35.0)["level"], "Moderate")
        self.assertEqual(evaluate_risk_state(55.0)["level"], "High")
        self.assertEqual(evaluate_risk_state(75.0)["level"], "Very High")
        self.assertEqual(evaluate_risk_state(90.0)["level"], "Critical")

    def test_burnout_diagnostics(self):
        res = compute_burnout_score(
            current_capacity_load=130.0, # High stress: 62.5%
            recovery_debt_hours=3.0,
            capacity_loads_history=[85.0, 90.0, 110.0],
            recent_sleep_deficits=[1.5, 2.0],
            future_capacity_loads=[140.0, 120.0]
        )
        self.assertGreater(res["burnout_risk"], 40.0)
        self.assertIn("diagnosis", res)
        self.assertIsNotNone(res["diagnosis"]["primary_problem"])
        self.assertGreater(len(res["diagnosis"]["contributing_factors"]), 0)

    def test_api_burnout_risk(self):
        res = self.client.get("/api/v1/burnout-risk", headers={"X-User-Id": str(self.user_id)})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("report", data)
        self.assertIn("burnout_risk", data["report"])
        self.assertIn("risk_level", data["report"])
        self.assertIn("diagnosis", data["report"])


if __name__ == "__main__":
    unittest.main()
