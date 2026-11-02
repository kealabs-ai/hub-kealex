import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("KEALEX_DATABASE_URL", "mysql+pymysql://test:test@localhost/test")
os.environ.setdefault("KEALEX_SECRET_KEY", "integration-test-secret")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.infrastructure.database.models.activity_model import ActivityStatusHistory, Base
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token


class ActivityRouteTests(unittest.TestCase):
    def test_health_endpoint_response_is_preserved(self):
        with patch("app.main.initialize_database"):
            with TestClient(app) as client:
                response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "svc-activities"})

    def test_all_route_prefix_aliases_remain_registered(self):
        routes = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        prefixes = ("/activities", "/api/activities", "/k1/lex/activities", "/v1/lex/activities")
        operations = (
            ("/columns", "GET"), ("/columns", "POST"),
            ("/columns/update", "POST"), ("/columns/delete", "POST"),
            ("", "GET"), ("", "POST"), ("/update", "POST"), ("/delete", "POST"),
        )
        expected = {(prefix + suffix, method) for prefix in prefixes for suffix, method in operations}
        self.assertTrue(expected.issubset(routes), expected - routes)

    def test_activity_status_changes_record_history_and_entry_time(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        def override_get_db():
            db = test_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[verify_token] = lambda: {"sub": "user-1", "tenant_id": "tenant-1"}
        try:
            with patch("app.main.initialize_database"):
                with TestClient(app) as client:
                    created = client.post("/k1/lex/activities", json={"title": "Revisar contrato"})
                    self.assertEqual(created.status_code, 201)
                    activity = created.json()
                    self.assertTrue(activity["statusEnteredAt"].endswith("Z"))

                    moved = client.post("/k1/lex/activities/update", json={
                        "id": activity["id"],
                        "status": "in_progress",
                    })
                    self.assertEqual(moved.status_code, 200)
                    self.assertEqual(moved.json()["status"], "in_progress")
                    self.assertTrue(moved.json()["statusEnteredAt"].endswith("Z"))

                    unchanged = client.post("/k1/lex/activities/update", json={
                        "id": activity["id"],
                        "title": "Revisar contrato atualizado",
                        "status": "in_progress",
                    })
                    self.assertEqual(unchanged.status_code, 200)
                    self.assertEqual(unchanged.json()["statusEnteredAt"], moved.json()["statusEnteredAt"])

                    deleted = client.post("/k1/lex/activities/delete", json={"id": activity["id"]})
                    self.assertEqual(deleted.status_code, 200)

            with test_session() as db:
                history = db.query(ActivityStatusHistory).filter_by(activity_id=activity["id"]).order_by(
                    ActivityStatusHistory.moved_at
                ).all()
                self.assertEqual([(event.from_status, event.to_status) for event in history], [
                    (None, "todo"),
                    ("todo", "in_progress"),
                ])
                self.assertEqual(
                    moved.json()["statusEnteredAt"],
                    history[-1].moved_at.isoformat() + "Z",
                )
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
