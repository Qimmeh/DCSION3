"""
Google Calendar & Timetable API Integration Tests
=================================================
Validates OAuth endpoints, timetable lifecycle, in-memory caching,
and static asset routing.
"""
import os
import unittest
from app import create_app
from app.extensions import db
from app.models import User
from app.api.calendar_api import calendar_store


class CalendarTestCase(unittest.TestCase):
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

        calendar_store.remove(self.user_id)

    def tearDown(self):
        calendar_store.remove(self.user_id)

    def test_01_oauth_start_unconfigured(self):
        orig_id = os.environ.pop("GOOGLE_CLIENT_ID", None)
        orig_secret = os.environ.pop("GOOGLE_CLIENT_SECRET", None)
        try:
            res = self.client.get(
                "/api/v1/calendar/oauth/start",
                headers={"X-User-Id": str(self.user_id)},
            )
            self.assertEqual(res.status_code, 503)
            data = res.get_json()
            self.assertIn("error", data)
        finally:
            if orig_id:
                os.environ["GOOGLE_CLIENT_ID"] = orig_id
            if orig_secret:
                os.environ["GOOGLE_CLIENT_SECRET"] = orig_secret

    def test_02_oauth_start_configured(self):
        orig_id = os.environ.get("GOOGLE_CLIENT_ID")
        orig_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        os.environ["GOOGLE_CLIENT_ID"] = "dummy-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "dummy-client-secret"
        try:
            res = self.client.get(
                "/api/v1/calendar/oauth/start",
                headers={"X-User-Id": str(self.user_id)},
            )
            self.assertEqual(res.status_code, 302)
            self.assertIn("accounts.google.com", res.headers.get("Location", ""))
        finally:
            if orig_id:
                os.environ["GOOGLE_CLIENT_ID"] = orig_id
            else:
                os.environ.pop("GOOGLE_CLIENT_ID", None)
            if orig_secret:
                os.environ["GOOGLE_CLIENT_SECRET"] = orig_secret
            else:
                os.environ.pop("GOOGLE_CLIENT_SECRET", None)

    def test_03_oauth_callback_invalid_state(self):
        res = self.client.get("/api/v1/calendar/oauth/callback?state=invalid&code=abc")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_04_timetable_not_connected(self):
        orig_id = os.environ.get("GOOGLE_CLIENT_ID")
        orig_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        os.environ["GOOGLE_CLIENT_ID"] = "dummy-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "dummy-client-secret"
        try:
            res = self.client.get(
                "/api/v1/calendar/timetable",
                headers={"X-User-Id": str(self.user_id)},
            )
            self.assertEqual(res.status_code, 401)
            data = res.get_json()
            self.assertIn("error", data)
        finally:
            if orig_id:
                os.environ["GOOGLE_CLIENT_ID"] = orig_id
            else:
                os.environ.pop("GOOGLE_CLIENT_ID", None)
            if orig_secret:
                os.environ["GOOGLE_CLIENT_SECRET"] = orig_secret
            else:
                os.environ.pop("GOOGLE_CLIENT_SECRET", None)

    def test_05_timetable_confirm_and_memory(self):
        fake_events = [
            {
                "id": "evt-1",
                "title": "Software Engineering Lecture",
                "start": "2026-09-11T10:00:00+08:00",
                "end": "2026-09-11T12:00:00+08:00",
                "location": "LT 2",
            }
        ]
        calendar_store.save_pending_timetable(self.user_id, fake_events)

        # Confirm
        res = self.client.post(
            "/api/v1/calendar/timetable/confirm",
            headers={"X-User-Id": str(self.user_id)},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "confirmed")

        # Check memory
        res = self.client.get(
            "/api/v1/calendar/timetable/memory",
            headers={"X-User-Id": str(self.user_id)},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["timetable"][0]["title"], "Software Engineering Lecture")

        # Disconnect
        res = self.client.post(
            "/api/v1/calendar/disconnect",
            headers={"X-User-Id": str(self.user_id)},
        )
        self.assertEqual(res.status_code, 200)

        # Check memory again
        res = self.client.get(
            "/api/v1/calendar/timetable/memory",
            headers={"X-User-Id": str(self.user_id)},
        )
        self.assertEqual(res.get_json()["count"], 0)

    def test_06_static_asset_serving(self):
        # Validate that root static assets are served without 404
        for path in ["/config.js", "/timetable.css", "/timetable.js"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Expected {path} to return 200")


if __name__ == "__main__":
    unittest.main()
