"""
Unit & Integration Tests for Battery & Recovery Engine
======================================================
Tests:
- Sleep recovery curve non-linear interpolation.
- Recovery debt accumulation and decay.
- Activity battery drain calculation with modifiers.
- Capacity load calculation (Workload / Battery * 100).
- /api/v1/battery/today and /api/v1/battery/log-sleep endpoints.
"""
import unittest
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Activity, Profile
from app.engine.battery import (
    sleep_recovery_curve,
    calculate_recovery_debt,
    calculate_starting_battery,
    calculate_activity_battery_drain,
    calculate_capacity_load,
    evaluate_battery_state,
)


class BatteryEngineTestCase(unittest.TestCase):
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

    def test_sleep_recovery_curve(self):
        self.assertAlmostEqual(sleep_recovery_curve(6.0), 65.0, places=1)
        self.assertAlmostEqual(sleep_recovery_curve(7.0), 80.0, places=1)
        self.assertAlmostEqual(sleep_recovery_curve(8.0), 100.0, places=1)
        self.assertAlmostEqual(sleep_recovery_curve(9.0), 105.0, places=1)
        self.assertAlmostEqual(sleep_recovery_curve(10.0), 110.0, places=1)
        # Interpolated 6.5h
        self.assertAlmostEqual(sleep_recovery_curve(6.5), 72.5, places=1)
        # Low sleep (4h)
        self.assertAlmostEqual(sleep_recovery_curve(4.0), 35.0, places=1)

    def test_recovery_debt(self):
        # 6h sleep against 8h target with 0 prior debt
        res = calculate_recovery_debt(previous_debt=0.0, target_sleep=8.0, actual_sleep=6.0)
        self.assertEqual(res["sleep_deficit"], 2.0)
        self.assertEqual(res["updated_debt"], 2.0)

        # Next day: 9h sleep pays down debt
        res2 = calculate_recovery_debt(previous_debt=res["updated_debt"], target_sleep=8.0, actual_sleep=9.0)
        # 2.0 * 0.85 - 1.0 = 1.70 - 1.0 = 0.70
        self.assertEqual(res2["sleep_deficit"], 0.0)
        self.assertAlmostEqual(res2["updated_debt"], 0.70, places=2)

    def test_activity_battery_drain(self):
        # 1 hour medium lecture
        drain_lecture = calculate_activity_battery_drain("academic", duration_minutes=60, intensity="Medium")
        self.assertAlmostEqual(drain_lecture, 5.0, places=1)

        # 2 hour high-intensity assignment with continuity
        drain_assignment = calculate_activity_battery_drain(
            "academic", duration_minutes=120, intensity="High", continuous_minutes=150
        )
        # 5.0 * 2.0 * 1.35 * 1.15 = 15.525
        self.assertGreater(drain_assignment, 15.0)

    def test_capacity_load_and_state(self):
        # Spec example: Workload 82%, Battery 65% gives ~126% capacity load
        cap_load = calculate_capacity_load(workload_score=82.0, battery_score=65.0)
        self.assertAlmostEqual(cap_load, 126.2, places=1)

        self.assertEqual(evaluate_battery_state(85.0), "healthy")
        self.assertEqual(evaluate_battery_state(65.0), "reduced")
        self.assertEqual(evaluate_battery_state(45.0), "low")
        self.assertEqual(evaluate_battery_state(25.0), "very_low")
        self.assertEqual(evaluate_battery_state(10.0), "critical")

    def test_api_battery_endpoints(self):
        # 1. Log sleep
        log_res = self.client.post(
            "/api/v1/battery/log-sleep",
            json={"actual_sleep_hours": 6.5, "target_sleep_hours": 8.0, "notes": "Studying late"},
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(log_res.status_code, 200)
        data = log_res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("record", data)
        self.assertEqual(data["record"]["actual_sleep_hours"], 6.5)

        # 2. Get today's battery
        get_res = self.client.get("/api/v1/battery/today", headers={"X-User-Id": str(self.user_id)})
        self.assertEqual(get_res.status_code, 200)
        bdata = get_res.get_json()
        self.assertEqual(bdata["status"], "success")
        self.assertIn("battery", bdata)
        self.assertIn("capacity_load", bdata["battery"])
        self.assertIn("battery_state", bdata["battery"])


if __name__ == "__main__":
    unittest.main()
