"""
Backend API & Deterministic Engine Integration Tests
====================================================
Validates all /api/v1 endpoints using Flask's test client.
"""
import unittest
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Activity, WorkloadEvent, WorkloadSnapshot


class BackendTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            # Setup demo user
            self.user = User.query.filter_by(username="demo_student").first()
            if not self.user:
                self.user = User(username="demo_student", email="demo@university.edu")
                self.user.set_password("demo123")
                db.session.add(self.user)
                db.session.commit()
            self.user_id = self.user.id

    def test_01_get_workload_today(self):
        res = self.client.get("/api/v1/workload/today", headers={"X-User-Id": str(self.user_id)})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("workload", data)
        self.assertIn("overall_score", data["workload"])
        self.assertIn("dimension_pressures", data["workload"])

    def test_02_create_activity(self):
        now_str = datetime.utcnow().isoformat()
        payload = {
            "title": "Machine Learning Assignment",
            "category": "Academic",
            "activity_type": "coding_assignment",
            "duration_minutes": 120,
            "intensity": "High",
            "start_time": now_str
        }
        res = self.client.post(
            "/api/v1/activities",
            json=payload,
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("activity", data)
        self.assertIn("workload_score", data)
        self.assertEqual(data["workload_score"]["scores"]["academic"]["raw"], 28.35)

        self.activity_id = data["activity"]["id"]

        # Test extend
        ext_res = self.client.post(
            f"/api/v1/activities/{self.activity_id}/extend",
            json={"minutes": 30},
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(ext_res.status_code, 200)
        ext_data = ext_res.get_json()
        self.assertEqual(ext_data["activity"]["duration_minutes"], 150)

        # Test complete
        comp_res = self.client.post(
            f"/api/v1/activities/{self.activity_id}/complete",
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(comp_res.status_code, 200)
        self.assertEqual(comp_res.get_json()["activity"]["status"], "completed")

    def test_03_capacity_simulation(self):
        payload = {
            "title": "Weekend Part-Time Gig",
            "category": "Work",
            "duration_minutes": 300,
            "intensity": "High"
        }
        res = self.client.post(
            "/api/v1/capacity/simulate",
            json=payload,
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("verdict", data["simulation"])
        self.assertIn("recommendation", data["simulation"])
        self.assertIn("daily", data["simulation"])

    def test_04_domino_rebalance(self):
        res = self.client.post(
            "/api/v1/domino/rebalance",
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("proposals", data)

    def test_05_recovery_protect(self):
        payload = {
            "duration_minutes": 90,
            "recovery_type": "rest",
            "recommended_actions": ["Get food outside", "Take a walk"]
        }
        res = self.client.post(
            "/api/v1/recovery/protect",
            json=payload,
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

        # Test get windows
        list_res = self.client.get("/api/v1/recovery/windows", headers={"X-User-Id": str(self.user_id)})
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(list_res.get_json()["count"], 1)

    def test_06_get_workload_week(self):
        res = self.client.get("/api/v1/workload/week", headers={"X-User-Id": str(self.user_id)})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("weekly_workload", data)


if __name__ == "__main__":
    unittest.main()
