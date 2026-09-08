"""
Unit & Integration Tests for Smart Todo & Timeline Scheduler
============================================================
Tests:
- Deadline collision detection.
- Task splitting into cognitively bounded blocks.
- Proactive "Finish Before" timeline optimization.
- Non-negotiable sleep protection.
- POST /api/v1/timeline/generate and POST /api/v1/survival-plan/apply.
"""
import unittest
from datetime import date, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Activity, Recommendation
from app.engine.scheduler import (
    detect_deadline_collisions,
    split_task_into_blocks,
    generate_smart_timeline,
)


class SchedulerTestCase(unittest.TestCase):
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

    def test_task_splitting(self):
        # 8h (480 min) task, max_block = 180 min, min_block = 60 min
        task = {
            "id": 101,
            "title": "Machine Learning Term Project",
            "remaining_effort_minutes": 480,
            "splittable": True,
            "minimum_block_minutes": 60,
            "maximum_block_minutes": 180,
        }
        blocks = split_task_into_blocks(task)
        self.assertGreater(len(blocks), 1)
        total_mins = sum(b["duration_minutes"] for b in blocks)
        self.assertEqual(total_mins, 480)
        for b in blocks:
            self.assertGreaterEqual(b["duration_minutes"], 60)
            self.assertLessEqual(b["duration_minutes"], 180)

        # Non-splittable task
        non_split = {
            "id": 102,
            "title": "2-Hour Fixed Exam",
            "remaining_effort_minutes": 120,
            "splittable": False,
        }
        blocks2 = split_task_into_blocks(non_split)
        self.assertEqual(len(blocks2), 1)

    def test_collision_detection(self):
        today = date.today()
        horizon = [
            {"date": (today + timedelta(days=i)).isoformat(), "workload_score": 50.0, "end_battery": 80.0}
            for i in range(7)
        ]
        # Make day 4 a high-load crunch day (90% workload, 40% battery)
        crunch_date = (today + timedelta(days=4)).isoformat()
        horizon[4]["workload_score"] = 90.0
        horizon[4]["end_battery"] = 40.0

        tasks = [{
            "id": 201,
            "title": "Distributed Systems Assignment",
            "deadline": crunch_date,
            "remaining_effort_minutes": 360,
        }]

        collisions = detect_deadline_collisions(horizon, tasks)
        self.assertTrue(collisions["has_collisions"])
        self.assertGreater(len(collisions["tasks_needing_earlier_placement"]), 0)

    def test_finish_before_optimization(self):
        today = date.today()
        deadline = (today + timedelta(days=4)).isoformat()

        tasks = [{
            "id": 301,
            "title": "Final Paper Draft",
            "deadline": deadline,
            "remaining_effort_minutes": 240, # 4 hours
            "splittable": True,
            "category": "Academic",
        }]

        plan = generate_smart_timeline(
            tasks=tasks,
            existing_activities_by_date={},
            horizon_days=7,
            start_date=today,
            target_sleep=8.0,
            minimum_sleep=6.0,
        )
        self.assertEqual(plan["status"], "success")
        self.assertGreater(plan["plan_score"], 0)
        self.assertIn("recommended_actions", plan)
        self.assertGreater(len(plan["recommended_actions"]), 0)
        # Verify protected items includes minimum sleep
        protect_titles = [p["title"] for p in plan["protect"]]
        self.assertIn("Minimum Protected Sleep", protect_titles)

    def test_api_timeline_generation_and_apply(self):
        today = date.today()
        deadline = (today + timedelta(days=3)).isoformat()
        payload = {
            "horizon_days": 7,
            "tasks": [{
                "title": "Algorithm Problem Set",
                "category": "Academic",
                "deadline": deadline,
                "remaining_effort_minutes": 180,
                "splittable": True,
            }]
        }
        res = self.client.post(
            "/api/v1/timeline/generate",
            json=payload,
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("plan", data)
        rec_id = data.get("recommendation_id")
        self.assertIsNotNone(rec_id)

        # Test apply survival plan
        apply_res = self.client.post(
            "/api/v1/survival-plan/apply",
            json={"recommendation_id": rec_id},
            headers={"X-User-Id": str(self.user_id)}
        )
        self.assertEqual(apply_res.status_code, 200)
        apply_data = apply_res.get_json()
        self.assertEqual(apply_data["status"], "success")
        self.assertEqual(apply_data["recommendation"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
